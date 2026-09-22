#include "closed.hpp"
#include "common.hpp"
#include "antennasim/build_info.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <memory>
#include <thread>

namespace antennasim::benchmark::closed {
namespace {
using namespace common;
constexpr Index base_cells{12, 16, 20};
constexpr std::array<double, 3> base_spacing{0.01, 0.015, 0.02};   // m at s=1
constexpr std::size_t margin = 3;                                   // V04-C cells around the shell
constexpr double amplitude = 1.0;                                   // V/m
constexpr double tau_s = 1.0 / (2 * pi * 1.5e9);                    // pulse time constant
constexpr std::uint64_t spectrum_steps = 32768, enforcement_steps = 4096;
constexpr Index spectrum_source{5, 7, 9}, spectrum_probe{7, 9, 13};
constexpr Index inside_source{8, 10, 12}, outside_source{1, 1, 1};
constexpr std::array axes{"x", "y", "z"};

std::size_t cyc(std::size_t a, std::size_t k) { return (a + k) % 3; }

UniformGrid make_grid(std::size_t s, std::size_t pad) {
    Index counts{};
    std::array<double, 3> spacing{};
    for (std::size_t axis = 0; axis < 3; ++axis) {
        counts[axis] = base_cells[axis] * s + 2 * pad;
        spacing[axis] = base_spacing[axis] / static_cast<double>(s);
    }
    AllocationLimits limits;
    limits.max_field_bytes = budget / 2;
    return UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, spacing, limits};
}

Index cavity_end(const Case& config) {
    Index end{};
    for (std::size_t axis = 0; axis < 3; ++axis) end[axis] = config.origin[axis] + config.cavity[axis];
    return end;
}

Case mode_case(std::size_t a, std::array<std::size_t, 2> mode, std::size_t s, double q, std::size_t pad,
               std::string name, std::string suite) {
    const auto grid = make_grid(s, pad);
    const auto dt = VacuumTimeStep::from_courant(grid, q);
    Index cavity{};
    for (std::size_t axis = 0; axis < 3; ++axis) cavity[axis] = base_cells[axis] * s;
    Case config{std::move(name), std::move(suite), Kind::Mode, grid, dt, 0, a, mode, s,
                Index{pad, pad, pad}, cavity, {}, pad > 0, {}, {}, pad > 0};
    if (pad > 0) config.primitives.push_back({PecShape::Shell, CellBox{config.origin, cavity_end(config)}});
    const auto reference = mode_reference(config);
    // Two continuum periods, as the specification's ceil(2 T_c / dt).
    config.steps = static_cast<std::uint64_t>(std::ceil(2.0 * 2 * pi / reference.omega_c / dt.seconds()));
    return config;
}

Case source_case(std::size_t pad, std::uint64_t steps, Index source, std::vector<Index> ez_probes, std::string name,
                 std::string suite) {
    const auto grid = make_grid(1, pad);
    const auto dt = VacuumTimeStep::from_courant(grid, 0.99);
    Case config{std::move(name), std::move(suite), Kind::Source, grid, dt, steps, 2, {0, 0}, 1,
                Index{pad, pad, pad}, base_cells, {}, pad > 0, std::move(ez_probes), source, true};
    if (pad > 0) config.primitives.push_back({PecShape::Shell, CellBox{config.origin, cavity_end(config)}});
    return config;
}

std::size_t working_bytes(const Case& config) {
    std::size_t mask_bytes = 0;
    for (std::size_t id = 0; id < 3; ++id) mask_bytes += config.grid.layout(component(id)).element_count;
    return 2 * config.grid.field_bytes() + mask_bytes + probes(config).size() * sizeof(FieldProbe) +
        sizeof(CurrentSample) + overhead;
}

void preflight(const Case& config) {
    validate_run_steps(config.dt, config.steps);
    if (working_bytes(config) > budget) throw std::length_error("Closed working memory exceeds 2 GiB.");
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if (config.cavity[axis] % 4 != 0 || config.origin[axis] + config.cavity[axis] > config.grid.cells().values()[axis])
            throw std::invalid_argument("Cavity does not fit the grid with quarter/half native lines.");
    }
    if (config.kind == Kind::Source) {
        const auto ez = component(2);
        (void)config.grid.offset(ez, config.source);
        if (mask(config).masked(ez, config.source)) throw std::invalid_argument("Pulse edge is masked.");
        for (const auto& index : config.ez_probes) (void)config.grid.offset(ez, index);
    }
}

// Exact sample classification against the closed shell box in doubled cell
// units: interior (strictly inside), exterior (strictly outside on some axis),
// otherwise surface (shell edges and face-normal H).
std::size_t region_of(const Case& config, std::size_t id, Index index) {
    const auto& box = config.primitives.front().cells;
    bool inside = true;
    for (std::size_t axis = 0; axis < 3; ++axis) {
        const bool half = id < 3 ? axis == id : axis != id - 3;
        const std::size_t doubled = 2 * index[axis] + (half ? 1 : 0);
        const std::size_t low = 2 * box.low[axis], high = 2 * box.high[axis];
        if (doubled < low || doubled > high) return 2;
        if (!(low < doubled && doubled < high)) inside = false;
    }
    return inside ? 0 : 1;
}

struct Diagnostics {
    double u, q;
    std::array<double, 6> maxima;
    std::array<std::array<double, 6>, 3> regions;
};
Diagnostics diagnostics(const ReferenceStepper& solver, const Case& config) {
    const auto& fields = solver.fields();
    const auto& grid = fields.grid();
    Sum electric, magnetic, cross;
    Diagnostics result{0, 0, {}, {}};
    all(grid, [&](std::size_t id, Index index) {
        const auto f = component(id);
        const double value = fields.at(f, index);
        const double magnitude = std::abs(value);
        result.maxima[id] = std::max(result.maxima[id], magnitude);
        if (config.region) {
            auto& entry = result.regions[region_of(config, id, index)][id];
            entry = std::max(entry, magnitude);
        }
        // Native Yee quadrature: half for each integer coordinate on an outer face.
        double weight = 1;
        for (std::size_t axis = 0; axis < 3; ++axis) {
            const bool integer = id < 3 ? axis != id : axis == id - 3;
            if (integer && (index[axis] == 0 || index[axis] == grid.cells().values()[axis])) weight *= 0.5;
        }
        if (id < 3) electric.add(weight * value * value);
        else {
            magnetic.add(weight * value * value);
            cross.add(weight * value * curl(grid, id, index, [&](std::size_t source, Index at) {
                return fields.at(component(source), at);
            }));
        }
    });
    const auto d = grid.spacing_m();
    const double volume = d[0] * d[1] * d[2];
    result.u = volume / 2 * (epsilon0 * electric.total + mu0 * magnetic.total);
    result.q = result.u - volume * solver.time_step().seconds() / 2 * cross.total;
    if (!std::isfinite(result.u) || !std::isfinite(result.q)) throw std::runtime_error("Nonfinite energy diagnostic.");
    return result;
}

void metadata(const Case& config, const std::filesystem::path& path, FixtureChecks checks, double elapsed, bool complete) {
    auto out = stream(path);
    const char* cpu = std::getenv("PROCESSOR_IDENTIFIER");
    const auto pec = mask(config);
    const auto reference = config.kind == Kind::Mode ? mode_reference(config) : ModeReference{};
    const auto samples = config.kind == Kind::Source ? pulse(config) : std::vector<double>{};
    out << "{\n\"schema\":\"closed-v1-raw-1\",\n\"case_status\":\"" << (complete ? "raw_complete" : "incomplete")
        << "\",\n\"fixture_checks_status\":\"" << (complete ? "passed" : "pending") << "\",\n\"case\":\"" << config.name
        << "\",\n\"suite\":\"" << config.suite << "\",\n\"kind\":\"" << (config.kind == Kind::Mode ? "mode" : "source")
        << "\",\n\"version\":\"" << version() << "\",\n\"source_snapshot_sha256\":\"" << ANTENNASIM_SOURCE_SNAPSHOT
        << "\",\n\"compiler\":\"" << ANTENNASIM_COMPILER << "\",\n"
        << "\"build_type\":\"" << ANTENNASIM_BUILD_TYPE << "\",\n\"cpu_identifier\":";
    json_string(out, cpu == nullptr ? "unavailable" : cpu);
    out << ",\"hardware_threads\":" << std::thread::hardware_concurrency() << ",\n"
        << "\"backend\":\"scalar CPU\",\"fp_policy\":\"strict, no fast math, no contraction\",\n"
        << "\"output_kind\":\"solver samples; fixture, mask, geometry and pulse values are deterministic calculations\",\n"
        << "\"boundary\":\"zero_tangential_e; pec_shell of the whole domain; initially zero enclosed H\",\n"
        << "\"pec_primitives\":[";
    for (std::size_t p = 0; p < config.primitives.size(); ++p) {
        const auto& primitive = config.primitives[p];
        out << (p == 0 ? "" : ",") << "{\"shape\":\"" << (primitive.shape == PecShape::Box ? "pec_box" : "pec_shell")
            << "\",\"low\":"; json_array(out, primitive.cells.low);
        out << ",\"high\":"; json_array(out, primitive.cells.high);
        out << '}';
    }
    out << "],\n\"masked_edges\":"; json_array(out, pec.masked_counts());
    out << ",\"closure_edges\":"; json_array(out, pec.closure_counts());
    out << ",\n\"units\":{\"length\":\"m\",\"time\":\"s\",\"E\":\"V/m\",\"H\":\"A/m\",\"J\":\"A/m^2\",\"energy\":\"J\"},\n"
        << "\"c0\":" << c0 << ",\"mu0\":" << mu0 << ",\"epsilon0\":" << epsilon0 << ",\"eta0\":" << eta0
        << ",\n\"cells\":"; json_array(out, config.grid.cells().values());
    out << ",\n\"spacing_m\":"; json_array(out, config.grid.spacing_m());
    out << ",\n\"lengths_m\":"; json_array(out, config.grid.lengths_m());
    out << ",\n\"extents\":[";
    for (std::size_t id = 0; id < 6; ++id) {
        if (id != 0) out << ',';
        json_array(out, config.grid.layout(component(id)).extents);
    }
    out << "],\n\"dt_s\":" << config.dt.seconds() << ",\"q\":" << config.dt.courant_fraction()
        << ",\"steps\":" << config.steps << ",\"a\":" << config.a << ",\"mode\":"; json_array(out, config.mode);
    out << ",\"s\":" << config.s << ",\n\"origin\":"; json_array(out, config.origin);
    out << ",\"cavity_cells\":"; json_array(out, config.cavity);
    out << ",\"region\":" << (config.region ? "true" : "false") << ",\"diagnostics\":" << (config.diagnostics ? "true" : "false");
    if (config.kind == Kind::Mode) {
        out << ",\n\"amplitude_V_per_m\":" << amplitude << ",\"omega_c\":" << reference.omega_c << ",\"omega_d\":" << reference.omega_d
            // The value at -dt/2, not the amplitude H_s=-C E_s/(mu0 Omega): H^(-1/2)=-H_s sin(omega_d dt/2).
            << ",\n\"initialization\":\"exact discrete standing mode: E_a=A sin(k_b r_b) sin(k_c r_c) at t=0; "
               "H=+(C E_s) sin(omega_d dt/2)/(mu0 Omega) at -dt/2 by permutation curl\",\n\"source\":\"J=0\"";
    } else {
        out << ",\n\"source_index\":"; json_array(out, config.source);
        out << ",\"J0_A_per_m2\":1,\"tau_s\":" << tau_s << ",\"pulse_half_samples\":" << (samples.size() - 1) / 2
            << ",\"pulse_samples\":" << samples.size()
            << ",\n\"initialization\":\"zero fields\",\n\"source\":\"J_z=J0 g_m on one Ez edge at (m+1/2) dt, "
               "g_m=(r/tau) exp(-(r/tau)^2/2), r=(M-m) dt, m=0..2M; zero thereafter\"";
    }
    out << ",\n\"probe_indices\":[";
    for (std::size_t p = 0; p < config.ez_probes.size(); ++p) {
        if (p != 0) out << ',';
        json_array(out, config.ez_probes[p]);
    }
    out << "],\n\"charge\":\"rho initially zero; delta rho=-dt*div J; PEC surface charge implied\",\n"
        << "\"native_time\":\"E=n*dt; H=(n-0.5)*dt; rows include n=0\",\n"
        << "\"diagnostic_weights\":\"half per transverse E outer wall, half per normal H outer wall\",\n"
        << "\"region_sets\":\"interior strictly inside the open shell box; surface on its closed faces; exterior strictly outside\",\n"
        << "\"fixture_max_divergence_error\":" << checks.divergence << ",\"fixture_max_eigen_error\":" << checks.eigen
        << ",\"field_bytes\":" << config.grid.field_bytes() << ",\"mask_bytes\":" << pec.mask_bytes()
        << ",\"working_bytes_budgeted\":" << working_bytes(config)
        << ",\"elapsed_seconds\":" << elapsed << "\n}\n";
    out.close();
}

void run_case(const Case& config, const std::filesystem::path& path) {
    const auto started = std::chrono::steady_clock::now();
    if (!std::filesystem::create_directory(path)) throw std::runtime_error("Case directory already exists.");
    metadata(config, path / "configuration.json", {}, 0, false);
    auto initial = std::make_unique<FieldStorage>(config.grid);
    const auto checks = initialize(config, *initial);
    const auto samples = config.kind == Kind::Source ? pulse(config) : std::vector<double>{};
    std::vector<CurrentSample> current_samples;
    if (config.kind == Kind::Source) current_samples.push_back({component(2), config.source, 1.0});
    ElectricCurrent current{config.grid, std::move(current_samples)};
    ReferenceStepper solver{*initial, config.dt, mask(config)};
    initial.reset();
    auto raw = stream(path / "probes.csv");
    auto energy = stream(path / "diagnostics.csv");
    raw << "state,component,i,j,k,x_m,y_m,z_m,time_s,value\n";
    energy << "state,e_time_s,h_time_s,U_J,Q_J";
    for (const auto name : names) energy << ",max_" << name;
    if (config.region) {
        for (const auto region : {"interior", "surface", "exterior"})
            for (const auto name : names) energy << ',' << region << '_' << name;
    }
    energy << '\n';
    const auto requests = probes(config);
    for (std::uint64_t n = 0; n <= config.steps; ++n) {
        for (const auto& request : requests) {
            const auto sample = sample_probe(solver, request);
            raw << n << ',' << names[static_cast<std::size_t>(request.component)];
            for (auto index : request.index) raw << ',' << index;
            for (auto position : sample.position_m) raw << ',' << position;
            raw << ',' << sample.time_s << ',' << sample.value << '\n';
        }
        if (config.diagnostics) {
            const auto values = diagnostics(solver, config);
            energy << n << ',' << solver.times().e_s << ',' << solver.times().h_s << ',' << values.u << ',' << values.q;
            for (auto maximum : values.maxima) energy << ',' << maximum;
            if (config.region)
                for (const auto& region : values.regions)
                    for (auto maximum : region) energy << ',' << maximum;
            energy << '\n';
        }
        if (n == config.steps) break;
        if (config.kind == Kind::Source && n < samples.size()) solver.step(current, samples[n]);
        else solver.step();
    }
    raw.close(); energy.close();
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    metadata(config, path / "metadata.json", checks, elapsed, true);
}
} // namespace

ModeReference mode_reference(const Case& config) {
    const auto b = cyc(config.a, 1), c = cyc(config.a, 2);
    const auto& d = config.grid.spacing_m();
    const double dt = config.dt.seconds();
    const double length_b = static_cast<double>(config.cavity[b]) * d[b];
    const double length_c = static_cast<double>(config.cavity[c]) * d[c];
    ModeReference reference{};
    reference.k_b = static_cast<double>(config.mode[0]) * pi / length_b;
    reference.k_c = static_cast<double>(config.mode[1]) * pi / length_c;
    reference.big_k_b = 2 / d[b] * std::sin(reference.k_b * d[b] / 2);
    reference.big_k_c = 2 / d[c] * std::sin(reference.k_c * d[c] / 2);
    reference.omega_c = c0 * std::hypot(reference.k_b, reference.k_c);
    const double argument = c0 * dt * std::hypot(reference.big_k_b, reference.big_k_c) / 2;
    if (!(argument > 0 && argument < 1)) throw std::invalid_argument("Discrete dispersion argument outside (0,1).");
    reference.omega_d = 2 / dt * std::asin(argument);
    reference.big_omega = 2 / dt * std::sin(reference.omega_d * dt / 2);
    return reference;
}

PecMask mask(const Case& config) { return PecMask{config.grid, config.primitives}; }

Case pec_mode_case(std::size_t a, PecShape shape) {
    auto config = mode_case(a, {1, 1}, 1, 0.99, margin, std::string("pec-c1-") + axes[a], "pec");
    config.primitives.front().shape = shape;
    return config;
}

std::vector<Case> cases(std::string_view suite, std::uint64_t smoke_steps) {
    std::vector<Case> result;
    const auto cavity = [](std::size_t a, std::array<std::size_t, 2> mode, std::size_t s, double q) {
        std::string name = std::string("cavity-") + axes[a] + "-m" + std::to_string(mode[0]) + std::to_string(mode[1]) +
            "-s" + std::to_string(s) + (q == 0.5 ? "-q50" : "");
        return mode_case(a, mode, s, q, 0, std::move(name), "cavity");
    };
    const auto spectrum = [] {
        return source_case(0, spectrum_steps, spectrum_source, {spectrum_probe}, "spectrum-s1", "cavity-spectrum");
    };
    const auto c2 = [] {
        Index probe{}, source = inside_source;
        for (std::size_t axis = 0; axis < 3; ++axis) probe[axis] = spectrum_probe[axis] + margin;
        return source_case(margin, enforcement_steps, source, {probe, source}, "pec-c2-inside", "pec");
    };
    const auto c3 = [] {
        return source_case(margin, enforcement_steps, outside_source, {outside_source, Index{9, 11, 13}}, "pec-c3-outside", "pec");
    };
    if (suite == "cavity") {
        for (std::size_t a = 0; a < 3; ++a)
            for (const std::array<std::size_t, 2> mode : {std::array<std::size_t, 2>{1, 1}, {2, 1}, {1, 2}})
                for (std::size_t s : {1U, 2U, 4U}) result.push_back(cavity(a, mode, s, 0.99));
        for (std::size_t a = 0; a < 3; ++a) result.push_back(cavity(a, {1, 1}, 1, 0.5));
    } else if (suite == "cavity-spectrum") {
        result.push_back(spectrum());
    } else if (suite == "pec") {
        for (std::size_t a = 0; a < 3; ++a) result.push_back(pec_mode_case(a, PecShape::Shell));
        result.push_back(c2());
        result.push_back(c3());
    } else if (suite == "smoke") {
        result.push_back(cavity(0, {1, 1}, 1, 0.99));
        result.push_back(spectrum());
        result.push_back(pec_mode_case(0, PecShape::Shell));
        result.push_back(c3());
        for (auto& config : result) config.steps = smoke_steps;
    } else throw std::invalid_argument("Unknown closed suite.");
    for (const auto& config : result) preflight(config);
    return result;
}

std::vector<FieldProbe> probes(const Case& config) {
    std::vector<FieldProbe> result;
    if (config.kind == Kind::Source) {
        for (const auto& index : config.ez_probes) result.push_back({component(2), index});
        return result;
    }
    const auto a = config.a, b = cyc(a, 1), c = cyc(a, 2);
    Index index{};
    // E_a and H_c lines along b at i_a = N_a/2, i_c = N_c/4; H_b line along c at i_b = N_b/4.
    index[a] = config.origin[a] + config.cavity[a] / 2;
    index[c] = config.origin[c] + config.cavity[c] / 4;
    for (std::size_t j = 0; j <= config.cavity[b]; ++j) {
        index[b] = config.origin[b] + j;
        result.push_back({component(a), index});
    }
    for (std::size_t j = 0; j < config.cavity[b]; ++j) {
        index[b] = config.origin[b] + j;
        result.push_back({component(c + 3), index});
    }
    index[b] = config.origin[b] + config.cavity[b] / 4;
    for (std::size_t k = 0; k < config.cavity[c]; ++k) {
        index[c] = config.origin[c] + k;
        result.push_back({component(b + 3), index});
    }
    return result;
}

std::vector<double> pulse(const Case& config) {
    const double dt = config.dt.seconds();
    const auto half = static_cast<std::size_t>(std::ceil(6 * tau_s / dt));
    std::vector<double> samples;
    for (std::size_t m = 0; m <= 2 * half; ++m) {
        // Exact integer multiples of dt: mirrored samples cancel bitwise.
        const double r = static_cast<double>(static_cast<long long>(half) - static_cast<long long>(m)) * dt;
        samples.push_back((r / tau_s) * std::exp(-(r / tau_s) * (r / tau_s) / 2));
    }
    return samples;
}

FixtureChecks initialize(const Case& config, FieldStorage& fields) {
    if (fields.grid().cells().values() != config.grid.cells().values() ||
        fields.grid().spacing_m() != config.grid.spacing_m()) throw std::invalid_argument("Fixture/grid mismatch.");
    preflight(config);
    const auto pec = mask(config);
    const auto& grid = config.grid;
    all(grid, [&](std::size_t id, Index index) { fields.at(component(id), index) = 0; });
    FixtureChecks checks;
    if (config.kind == Kind::Mode) {
        const auto reference = mode_reference(config);
        const auto a = config.a, b = cyc(a, 1), c = cyc(a, 2);
        const auto& d = grid.spacing_m();
        const auto end = cavity_end(config);
        each(grid.layout(component(a)).extents, [&](Index index) {
            const bool inside = config.origin[a] <= index[a] && index[a] < end[a] &&
                config.origin[b] < index[b] && index[b] < end[b] && config.origin[c] < index[c] && index[c] < end[c];
            if (!inside) return;
            // Integer offsets first so that a shifted cavity reproduces the same arguments bitwise.
            const double r_b = static_cast<double>(index[b] - config.origin[b]) * d[b];
            const double r_c = static_cast<double>(index[c] - config.origin[c]) * d[c];
            fields.at(component(a), index) = amplitude * std::sin(reference.k_b * r_b) * std::sin(reference.k_c * r_c);
        });
        const auto electric = [&](std::size_t source, Index at) { return fields.at(component(source), at); };
        const double factor = std::sin(reference.omega_d * config.dt.seconds() / 2) / (mu0 * reference.big_omega);
        for (std::size_t id = 3; id < 6; ++id)
            each(grid.layout(component(id)).extents, [&](Index index) {
                fields.at(component(id), index) = curl(grid, id, index, electric) * factor;
            });
        // Exact eigenvector identity C*C E = |K|^2 E on every unmasked edge (independent curls).
        const double k2 = reference.big_k_b * reference.big_k_b + reference.big_k_c * reference.big_k_c;
        const auto g = [&](std::size_t source, Index at) { return curl(grid, source, at, electric); };
        for (std::size_t id = 0; id < 3; ++id)
            each(grid.layout(component(id)).extents, [&](Index index) {
                if (pec.masked(component(id), index)) return;
                const double value = curl(grid, id, index, g);
                const double error = std::abs(value - k2 * fields.at(component(id), index)) / k2;
                if (!std::isfinite(error)) throw std::runtime_error("Nonfinite fixture eigen check.");
                checks.eigen = std::max(checks.eigen, error);
            });
    }
    all(grid, [&](std::size_t id, Index index) {
        const auto f = component(id);
        const double value = fields.at(f, index);
        if (!std::isfinite(value)) throw std::runtime_error("Nonfinite fixture.");
        if ((pec.masked(f, index) || pec.enclosed(f, index)) && value != 0)
            throw std::runtime_error("Fixture is nonzero on a masked edge or enclosed H sample.");
    });
    const double dmin = *std::min_element(grid.spacing_m().begin(), grid.spacing_m().end());
    for (bool electric : {true, false}) {
        each(grid.cells().values(), [&](Index index) {
            if (electric && (index[0] == 0 || index[1] == 0 || index[2] == 0)) return;
            double div = 0, scale = 0;
            for (std::size_t axis = 0; axis < 3; ++axis) {
                auto high = index, low = index;
                if (electric) --low[axis]; else ++high[axis];
                const auto f = component(axis + (electric ? 0U : 3U));
                if (electric && (pec.masked(f, high) || pec.masked(f, low))) return;   // implied surface charge
                const double hi = fields.at(f, high) / grid.spacing_m()[axis];
                const double lo = fields.at(f, low) / grid.spacing_m()[axis];
                div += hi - lo; scale += std::abs(hi) + std::abs(lo);
            }
            const double error = std::abs(div) / std::max(scale, 1 / (dmin * (electric ? 1 : eta0)));
            if (!std::isfinite(error)) throw std::runtime_error("Nonfinite fixture divergence.");
            checks.divergence = std::max(checks.divergence, error);
        });
    }
    if (checks.divergence > 1e-11 || checks.eigen > 1e-11) throw std::runtime_error("Closed fixture identity failed.");
    return checks;
}

void run_suite(std::string_view suite, const std::filesystem::path& output, std::uint64_t smoke_steps) {
    const auto configs = cases(suite, smoke_steps);
    if (output.empty()) throw std::invalid_argument("Output path is empty.");
    if (!output.parent_path().empty()) std::filesystem::create_directories(output.parent_path());
    if (!std::filesystem::create_directory(output)) throw std::invalid_argument("Output directory already exists.");
    for (const auto& config : configs) {
        try { run_case(config, output / config.name); }
        catch (const std::exception& error) { throw std::runtime_error(config.name + ": " + error.what()); }
    }
    auto complete = stream(output / "COMPLETE.json.tmp");
    complete << "{\"schema\":\"closed-v1-raw-1\",\"suite\":\"" << suite
        << "\",\"cases\":" << configs.size() << ",\"physical_acceptance\":\"not evaluated\"}\n";
    complete.close();
    std::filesystem::rename(output / "COMPLETE.json.tmp", output / "COMPLETE.json");
}
} // namespace antennasim::benchmark::closed
