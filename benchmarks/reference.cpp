#include "reference.hpp"
#include "common.hpp"
#include "antennasim/build_info.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <memory>
#include <thread>

namespace antennasim::benchmark {
namespace {
using namespace common;
constexpr double wavelength = 0.3;
int orientation(std::size_t a, std::size_t b) { return (a + 1) % 3 == b ? 1 : -1; }
double face_distance(const UniformGrid& grid, const std::array<double, 3>& r, std::size_t axis) {
    const double cells = r[axis] / grid.spacing_m()[axis];
    return std::min(cells, static_cast<double>(grid.cells().values()[axis]) - cells);
}
double potential(const Case& config, std::size_t id, Index index) {
    const auto r = config.grid.position_m(component(id), index);
    double mask = 1;
    for (std::size_t axis = 0; axis < 3; ++axis) {
        const double distance = face_distance(config.grid, r, axis);
        if (!config.propagation && distance <= 2) return 0;
        mask *= std::clamp((distance - 2) / 2, 0.0, 1.0);
    }
    if (!config.propagation) {
        if (id < 3) return 0;
        const auto residue = (17*index[0]+31*index[1]+43*index[2]+13*(id-3)) % 101;
        return 0.01 * (static_cast<double>(residue)-50) / 50;
    }
    const auto c = 3 - config.a - config.b;
    const double k = 2*pi/wavelength;
    const double d = config.grid.spacing_m()[config.a];
    const double K = 2/d*std::sin(k*d/2);
    const double omega = 2/config.dt.seconds()*std::asin(c0*config.dt.seconds()*K/2);
    const double shift = config.enlarged ? 2*wavelength : 0;
    if (id == c+3) {
        return -static_cast<double>(orientation(config.a, config.b))/K * mask *
            std::sin(k*(r[config.a]-shift));
    }
    if (id == config.b) {
        return mask/(eta0*K)*std::sin(k*(r[config.a]-shift)+omega*config.dt.seconds()/2);
    }
    return 0;
}

std::size_t working_bytes(const Case& config) {
    // Fixed built-in grid sizes; count both initial and owned field payloads,
    // the stepper's closure mask (one byte per E sample) and its vacuum
    // coefficient index (four bytes per E sample) with a one-entry table (D023).
    const auto& grid = config.grid;
    std::size_t e_count = 0;
    for (std::size_t id = 0; id < 3; ++id) e_count += grid.layout(component(id)).element_count;
    const std::size_t source_count = config.driven ? e_count : 0;
    return 2*grid.field_bytes() + e_count + 4*e_count + sizeof(EdgeMaterial) + source_count*sizeof(CurrentSample) +
        6*config.p*sizeof(FieldProbe) + overhead;
}
void preflight(const Case& config) {
    validate_run_steps(config.dt, config.steps);
    if (working_bytes(config) > budget) throw std::length_error("Reference working memory exceeds 2 GiB.");
    if (config.propagation) {
        const double required = 2*static_cast<double>(config.steps)+6;
        if (!(static_cast<double>(config.p)-0.5 > required))
            throw std::invalid_argument("Propagation dependency isolation guard failed.");
        for (const auto& probe : probes(config)) {
            const auto r = config.grid.position_m(probe.component, probe.index);
            for (std::size_t axis = 0; axis < 3; ++axis)
                if (!(face_distance(config.grid, r, axis) > required))
                    throw std::invalid_argument("Native probe dependency cone reaches taper.");
        }
    }
}
Case propagation_case(std::size_t a, std::size_t b, std::size_t p, std::string_view variant) {
    const auto c = 3-a-b;
    const bool enlarged = variant == "enlarged", cubic = variant == "cubic";
    Index counts{};
    std::array<double, 3> spacing{};
    counts[a] = (enlarged ? 7 : 3)*p;
    counts[b] = enlarged ? 14*p/3 : (cubic ? 3 : 2)*p;
    counts[c] = (enlarged || cubic ? 4 : 2)*p;
    spacing[a] = wavelength/static_cast<double>(p);
    spacing[b] = (cubic ? 1 : 1.5)*spacing[a];
    spacing[c] = (cubic ? 1 : 2)*spacing[a];
    AllocationLimits limits;
    limits.max_field_bytes = budget/2;
    const UniformGrid grid{CellCounts{counts[0],counts[1],counts[2]}, spacing, limits};
    const auto dt = VacuumTimeStep::from_courant(grid, variant == "half-q" ? 0.5 : 0.99);
    const auto steps = static_cast<std::uint64_t>(std::floor(0.1*wavelength/c0/dt.seconds()));
    const std::string axes = "xyz";
    return {"prop-"+axes.substr(a,1)+axes.substr(b,1)+"-p"+std::to_string(p)+"-"+std::string(variant),
            grid, dt, steps, a, b, p, true, enlarged, false};
}
Case stability_case(double q, bool driven) {
    const UniformGrid grid{CellCounts{12,14,16}, {0.01,0.015,0.02}};
    const auto dt = VacuumTimeStep::from_courant(grid,q);
    return {std::string("stable-")+(q == .5 ? "q50-" : "q99-")+(driven ? "driven" : "initial"),
            grid,dt,driven ? 20008U : 20000U,0,1,24,false,false,driven};
}
struct Diagnostics { double u, q; std::array<double, 6> maxima; };
Diagnostics diagnostics(const ReferenceStepper& solver) {
    const auto& fields = solver.fields();
    const auto& grid = fields.grid();
    Sum electric, magnetic, cross;
    std::array<double, 6> maxima{};
    all(grid, [&](std::size_t id, Index index) {
        const auto f = component(id);
        const double value = fields.at(f,index);
        maxima[id] = std::max(maxima[id],std::abs(value));
        // Native Yee quadrature: half for each integer coordinate on a face.
        double weight = 1;
        for (std::size_t axis = 0; axis < 3; ++axis) {
            const bool integer = id < 3 ? axis != id : axis == id-3;
            if (integer && (index[axis] == 0 || index[axis] == grid.cells().values()[axis])) weight *= 0.5;
        }
        if (id < 3) electric.add(weight*value*value);
        else {
            magnetic.add(weight*value*value);
            cross.add(weight*value*curl(grid,id,index,[&](std::size_t source, Index at) {
                return fields.at(component(source),at);
            }));
        }
    });
    const auto d = grid.spacing_m();
    const double volume = d[0]*d[1]*d[2];
    const double u = volume/2*(epsilon0*electric.total+mu0*magnetic.total);
    const double q = u-volume*solver.time_step().seconds()/2*cross.total;
    if (!std::isfinite(u) || !std::isfinite(q)) throw std::runtime_error("Nonfinite energy diagnostic.");
    return {u,q,maxima};
}
void metadata(const Case& config, const std::filesystem::path& path, FixtureChecks checks, double elapsed, bool complete) {
    auto out = stream(path);
    const char* cpu = std::getenv("PROCESSOR_IDENTIFIER");
    out << "{\n\"schema\":\"reference-v1-raw-1\",\n\"case_status\":\"" << (complete ? "raw_complete" : "incomplete")
        << "\",\n\"fixture_checks_status\":\"" << (complete ? "passed" : "pending") << "\",\n\"case\":\"" << config.name
        << "\",\n\"version\":\"" << version() << "\",\n\"source_snapshot_sha256\":\"" << ANTENNASIM_SOURCE_SNAPSHOT
        << "\",\n\"compiler\":\"" << ANTENNASIM_COMPILER << "\",\n"
        << "\"build_type\":\"" << ANTENNASIM_BUILD_TYPE << "\",\n\"cpu_identifier\":";
    json_string(out,cpu == nullptr ? "unavailable" : cpu);
    out << ",\"hardware_threads\":" << std::thread::hardware_concurrency() << ",\n"
        << "\"backend\":\"scalar CPU\",\"fp_policy\":\"strict, no fast math, no contraction\",\n"
        << "\"output_kind\":\"solver samples; fixture and geometry values are deterministic calculations\",\n"
        << "\"boundary\":\"zero_tangential_e; initially zero normal H\",\n"
        << "\"units\":{\"length\":\"m\",\"time\":\"s\",\"E\":\"V/m\",\"H\":\"A/m\",\"J\":\"A/m^2\",\"energy\":\"J\"},\n"
        << "\"c0\":" << c0 << ",\"mu0\":" << mu0 << ",\"epsilon0\":" << epsilon0 << ",\"eta0\":" << eta0
        << ",\n\"cells\":"; json_array(out,config.grid.cells().values());
    out << ",\n\"spacing_m\":"; json_array(out,config.grid.spacing_m());
    out << ",\n\"lengths_m\":"; json_array(out,config.grid.lengths_m());
    out << ",\n\"extents\":[";
    for (std::size_t id = 0; id < 6; ++id) {
        if (id != 0) out << ',';
        json_array(out,config.grid.layout(component(id)).extents);
    }
    out << "],\n\"dt_s\":" << config.dt.seconds() << ",\"q\":" << config.dt.courant_fraction()
        << ",\"steps\":" << config.steps << ",\"a\":" << config.a << ",\"b\":" << config.b << ",\"p\":" << config.p
        << ",\"propagation\":" << (config.propagation ? "true" : "false")
        << ",\"enlarged\":" << (config.enlarged ? "true" : "false")
        << ",\"driven\":" << (config.driven ? "true" : "false")
        << ",\n\"initialization\":\"" << (config.propagation ? "FND-04 v1 compact P/Q curls" :
            config.driven ? "zero fields" : "FND-04 v1 normalized modular P curl") << "\",\n"
        << "\"source\":\"" << (config.driven ? "0.01*epsilon0/dt*F*sin(pi*(n+0.5)/8), n=0..7; zero thereafter" : "J=0")
        << "\",\n\"charge\":\"rho initially zero; delta rho=-dt*div J\",\n"
        << "\"native_time\":\"E=n*dt; H=(n-0.5)*dt; rows include n=0\",\n"
        << "\"diagnostic_weights\":\"half per transverse E wall, half per normal H wall\",\n"
        << "\"diagnostic_reference_state\":" << (config.driven ? 8 : 0)
        << ",\"fixture_max_divergence_error\":" << checks.divergence << ",\"fixture_max_plateau_error\":" << checks.plateau
        << ",\"field_bytes\":" << config.grid.field_bytes() << ",\"working_bytes_budgeted\":" << working_bytes(config)
        << ",\"elapsed_seconds\":" << elapsed << "\n}\n";
    out.close();
}
void run_case(const Case& config, const std::filesystem::path& path) {
    const auto started = std::chrono::steady_clock::now();
    if (!std::filesystem::create_directory(path)) throw std::runtime_error("Case directory already exists.");
    // Retain exact input/provenance if allocation, fixture checks or stepping fail.
    // Fixture metrics are placeholders until fixture_checks_status is passed.
    metadata(config,path / "configuration.json",{},0,false);
    auto initial = std::make_unique<FieldStorage>(config.grid);
    const auto checks = initialize(config,*initial);
    std::vector<CurrentSample> samples;
    if (config.driven) {
        std::size_t reserve = 0;
        for (std::size_t id = 0; id < 3; ++id) reserve += config.grid.layout(component(id)).element_count;
        samples.reserve(reserve);
        all(config.grid,[&](std::size_t id, Index index) {
            auto& value = initial->at(component(id),index);
            if (id < 3 && value != 0) samples.push_back({component(id),index,value});
            value = 0;
        });
    }
    ElectricCurrent current{config.grid,std::move(samples)};
    ReferenceStepper solver{*initial,config.dt};
    initial.reset();
    auto raw = stream(path / "probes.csv");
    auto energy = stream(path / "diagnostics.csv");
    raw << "state,component,i,j,k,x_m,y_m,z_m,time_s,value\n";
    energy << "state,e_time_s,h_time_s,U_J,Q_J,max_Ex,max_Ey,max_Ez,max_Hx,max_Hy,max_Hz\n";
    const auto requests = probes(config);
    for (std::uint64_t n = 0; n <= config.steps; ++n) {
        for (const auto& request : requests) {
            const auto sample = sample_probe(solver,request);
            raw << n << ',' << names[static_cast<std::size_t>(request.component)];
            for (auto index : request.index) raw << ',' << index;
            for (auto position : sample.position_m) raw << ',' << position;
            raw << ',' << sample.time_s << ',' << sample.value << '\n';
        }
        // Propagation requires native line output; full-volume energies are for V03.
        if (!config.propagation) {
            const auto values = diagnostics(solver);
            energy << n << ',' << solver.times().e_s << ',' << solver.times().h_s << ',' << values.u << ',' << values.q;
            for (auto maximum : values.maxima) energy << ',' << maximum;
            energy << '\n';
        }
        if (n == config.steps) break;
        if (config.driven && n < 8) {
            const double amplitude = 0.01*epsilon0/config.dt.seconds()*std::sin(pi*(static_cast<double>(n)+.5)/8);
            solver.step(current,amplitude);
        } else solver.step();
    }
    raw.close(); energy.close();
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    metadata(config,path / "metadata.json",checks,elapsed,true);
}
} // namespace

std::vector<Case> cases(std::string_view suite, std::uint64_t smoke_steps) {
    std::vector<Case> result;
    if (suite == "propagation") {
        for (std::size_t a = 0; a < 3; ++a) for (std::size_t b = 0; b < 3; ++b) {
            if (a == b) continue;
            for (std::size_t p : {24U,48U,96U}) result.push_back(propagation_case(a,b,p,"primary"));
            for (const auto variant : {"enlarged","half-q","cubic"}) result.push_back(propagation_case(a,b,24,variant));
        }
    } else if (suite == "stability") {
        for (double q : {.5,.99}) for (bool driven : {false,true}) result.push_back(stability_case(q,driven));
    } else if (suite == "smoke") {
        result.push_back(propagation_case(0,1,24,"primary"));
        result.push_back(stability_case(.99,false));
        result.push_back(stability_case(.99,true));
        for (auto& config : result) config.steps = smoke_steps;
    } else throw std::invalid_argument("Unknown reference suite.");
    for (const auto& config : result) preflight(config);
    return result;
}

std::vector<FieldProbe> probes(const Case& config) {
    std::vector<FieldProbe> result;
    const auto counts = config.grid.cells().values();
    for (std::size_t id = 0; id < 6; ++id) {
        Index index{counts[0]/2,counts[1]/2,counts[2]/2};
        if (!config.propagation) { result.push_back({component(id),index}); continue; }
        for (std::size_t axial = config.p; axial < 2*config.p; ++axial) {
            index[config.a] = axial + (config.enlarged ? 2*config.p : 0);
            // Enlarged transverse centers equal the original centers + 2 lambda.
            result.push_back({component(id),index});
        }
    }
    return result;
}

FixtureChecks initialize(const Case& config, FieldStorage& fields) {
    if (fields.grid().cells().values() != config.grid.cells().values() ||
        fields.grid().spacing_m() != config.grid.spacing_m()) throw std::invalid_argument("Fixture/grid mismatch.");
    preflight(config);
    double maximum = 0;
    all(config.grid,[&](std::size_t id, Index index) {
        auto& value = fields.at(component(id),index);
        value = 0;
        if (!config.grid.is_tangential_e_wall(component(id),index)) {
            value = curl(config.grid,id,index,[&](std::size_t source, Index at) { return potential(config,source,at); });
        }
        maximum = std::max(maximum,std::abs(value));
    });
    if (!config.propagation) {
        if (!(maximum > 0 && std::isfinite(maximum))) throw std::runtime_error("Zero/nonfinite stability shape.");
        all(config.grid,[&](std::size_t id, Index index) { fields.at(component(id),index) /= maximum; });
    }
    FixtureChecks checks;
    all(config.grid,[&](std::size_t id, Index index) {
        const auto f = component(id);
        const double value = fields.at(f,index);
        if (!std::isfinite(value)) throw std::runtime_error("Nonfinite fixture.");
        if ((config.grid.is_tangential_e_wall(f,index) || config.grid.is_normal_h_wall(f,index)) && value != 0)
            throw std::runtime_error("Nonzero fixture wall.");
    });
    const double dmin = *std::min_element(config.grid.spacing_m().begin(),config.grid.spacing_m().end());
    for (bool electric : {true,false}) {
        each(config.grid.cells().values(),[&](Index index) {
            if (electric && (index[0] == 0 || index[1] == 0 || index[2] == 0)) return;
            double div = 0, scale = 0;
            for (std::size_t axis = 0; axis < 3; ++axis) {
                auto high = index, low = index;
                if (electric) --low[axis]; else ++high[axis];
                const auto f = component(axis+(electric ? 0U : 3U));
                const double hi = fields.at(f,high)/config.grid.spacing_m()[axis];
                const double lo = fields.at(f,low)/config.grid.spacing_m()[axis];
                div += hi-lo; scale += std::abs(hi)+std::abs(lo);
            }
            const double error = std::abs(div)/std::max(scale,1/(dmin*(electric ? 1 : eta0)));
            if (!std::isfinite(error)) throw std::runtime_error("Nonfinite fixture divergence.");
            checks.divergence = std::max(checks.divergence,error);
        });
    }
    if (config.propagation) {
        const auto c = 3-config.a-config.b;
        const double k = 2*pi/wavelength, d = config.grid.spacing_m()[config.a];
        const double omega = 2/config.dt.seconds()*std::asin(c0*config.dt.seconds()/d*std::sin(k*d/2));
        for (const auto& probe : probes(config)) {
            const auto id = static_cast<std::size_t>(probe.component);
            const auto r = config.grid.position_m(probe.component,probe.index);
            const double time = id < 3 ? 0 : -config.dt.seconds()/2;
            const double shift = config.enlarged ? 2*wavelength : 0;
            const double wave = std::cos(k*(r[config.a]-shift)-omega*time);
            const double expected = id == config.b ? wave : id == c+3 ? orientation(config.a,config.b)*wave/eta0 : 0;
            checks.plateau = std::max(checks.plateau,std::abs(fields.at(probe.component,probe.index)-expected)*(id < 3 ? 1 : eta0));
        }
    }
    if (checks.divergence > 1e-11 || checks.plateau > 1e-11) throw std::runtime_error("S08 fixture identity failed.");
    return checks;
}

void run_suite(std::string_view suite, const std::filesystem::path& output, std::uint64_t smoke_steps) {
    const auto configs = cases(suite,smoke_steps);
    if (output.empty()) throw std::invalid_argument("Output path is empty.");
    // create_directory is an exclusive claim; never reuse even an empty directory.
    if (!output.parent_path().empty()) std::filesystem::create_directories(output.parent_path());
    if (!std::filesystem::create_directory(output)) throw std::invalid_argument("Output directory already exists.");
    for (const auto& config : configs) {
        try { run_case(config,output / config.name); }
        catch (const std::exception& error) { throw std::runtime_error(config.name+": "+error.what()); }
    }
    auto complete = stream(output / "COMPLETE.json.tmp");
    complete << "{\"schema\":\"reference-v1-raw-1\",\"suite\":\"" << suite
        << "\",\"cases\":" << configs.size() << ",\"physical_acceptance\":\"not evaluated\"}\n";
    complete.close();
    std::filesystem::rename(output / "COMPLETE.json.tmp",output / "COMPLETE.json");
}
} // namespace antennasim::benchmark
