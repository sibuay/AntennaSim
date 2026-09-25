#include "material.hpp"
#include "common.hpp"
#include "antennasim/build_info.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <functional>
#include <map>
#include <memory>
#include <thread>

namespace antennasim::benchmark::material {
namespace {
using namespace common;
using Complex = std::complex<double>;
constexpr double wavelength = 0.3;                // m, lambda0
constexpr double loaded_eps_r = 4.0;             // V05/V06-A loaded region
constexpr std::array axes{"x", "y", "z"};

std::size_t cyc(std::size_t a, std::size_t k) { return (a + k) % 3; }
int orientation(std::size_t a, std::size_t b) { return (a + 1) % 3 == b ? 1 : -1; }
double f0() { return c0 / wavelength; }

UniformGrid make_grid(const std::array<std::size_t, 3>& roles, Index role_counts, std::array<double, 3> role_spacing) {
    Index counts{};
    std::array<double, 3> spacing{};
    for (std::size_t r = 0; r < 3; ++r) {
        counts[roles[r]] = role_counts[r];
        spacing[roles[r]] = role_spacing[r];
    }
    AllocationLimits limits;
    limits.max_field_bytes = budget / 2;
    return UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, spacing, limits};
}

// ---- Closed-form discrete predictions (transcribed from the MAT-01 audit) ----
double discrete_k(double d) { const double k = 2 * pi / wavelength; return 2 / d * std::sin(k * d / 2); }

// Root with positive imaginary part of (eps + sigma dt/2) z^2 + (-2 eps + dt^2 K^2/mu0) z + (eps - sigma dt/2) = 0.
Complex lossy_step_root(double dt, double big_k, double eps, double sigma) {
    const double a = eps + sigma * dt / 2;
    const double b = -2 * eps + dt * dt * big_k * big_k / mu0;
    const double c = eps - sigma * dt / 2;
    const double disc = b * b - 4 * a * c;
    if (!(disc < 0)) throw std::runtime_error("Lossy eigenwave is not oscillatory.");
    return Complex{-b, std::sqrt(-disc)} / (2 * a);
}

struct SlabGeometry { double d_a, d_c, dt; std::size_t n_a, i_int; };
constexpr double slab_kc = pi / (2.0 * wavelength);   // TE_1 transverse wavenumber, L_c = 2 lambda0

double beta_continuum(double f, double eps_r) {
    const double k0 = 2 * pi * f / c0;
    const double value = eps_r * k0 * k0 - slab_kc * slab_kc;
    if (!(value > 0)) throw std::runtime_error("Slab frequency below cutoff.");
    return std::sqrt(value);
}
double slab_continuum(double f) {
    const double b1 = beta_continuum(f, 1.0), b2 = beta_continuum(f, loaded_eps_r);
    const double l1 = wavelength / 2, l2 = wavelength - wavelength / 2;
    return b1 * std::cos(b1 * l1) * std::sin(b2 * l2) + b2 * std::sin(b1 * l1) * std::cos(b2 * l2);
}
struct Reduced { double k1, k2, big_omega, big_kc; };
Reduced reduced_wavenumbers(double f, const SlabGeometry& g) {
    Reduced result{};
    result.big_omega = 2 / g.dt * std::sin(pi * f * g.dt);
    result.big_kc = 2 / g.d_c * std::sin(slab_kc * g.d_c / 2);
    for (const double eps_r : {1.0, loaded_eps_r}) {
        const double k2 = eps_r * result.big_omega * result.big_omega / (c0 * c0) - result.big_kc * result.big_kc;
        if (!(k2 > 0)) throw std::runtime_error("Reduced system below cutoff.");
        const double argument = std::sqrt(k2) * g.d_a / 2;
        if (!(argument < 1)) throw std::runtime_error("Axial wavenumber not representable.");
        (eps_r == 1.0 ? result.k1 : result.k2) = 2 / g.d_a * std::asin(argument);
    }
    return result;
}
// Pole-free discrete characteristic function of the averaged-node slab cavity.
double slab_discrete(double f, const SlabGeometry& g) {
    const auto r = reduced_wavenumbers(f, g);
    const double d = g.d_a;
    const auto i_int = static_cast<double>(g.i_int), n_a = static_cast<double>(g.n_a);
    const double eps_avg = (1.0 + loaded_eps_r) / 2 * epsilon0;
    const double s1 = std::sin(r.k1 * i_int * d), s2 = std::sin(r.k2 * (n_a - i_int) * d);
    const double left = std::sin(r.k1 * (i_int - 1) * d), right = std::sin(r.k2 * (n_a - i_int - 1) * d);
    const double c = r.big_kc * r.big_kc - mu0 * eps_avg * r.big_omega * r.big_omega;
    return (s1 * right - 2 * s1 * s2 + s2 * left) / (d * d) - c * s1 * s2;
}
double bisect(const std::function<double(double)>& function, double lo, double hi) {
    double flo = function(lo);
    if (!(flo * function(hi) < 0)) throw std::runtime_error("Root not bracketed.");
    for (int iteration = 0; iteration < 200; ++iteration) {
        const double mid = (lo + hi) / 2, fmid = function(mid);
        if (fmid == 0) return mid;
        if (flo * fmid < 0) hi = mid; else { lo = mid; flo = fmid; }
    }
    return (lo + hi) / 2;
}
std::vector<double> roots(const std::function<double(double)>& function, std::size_t count) {
    const double start = slab_kc * c0 / 2 / pi * 1.001, step = 1e6, limit = 5 * f0();
    std::vector<double> found;
    double lo = start, flo = function(start);
    while (found.size() < count) {
        const double hi = lo + step;
        if (!(hi < limit)) throw std::runtime_error("No slab root found.");
        const double fhi = function(hi);
        if (flo * fhi < 0) found.push_back(bisect(function, lo, hi));
        lo = hi; flo = fhi;
    }
    return found;
}
SlabGeometry slab_geometry(const Case& config) {
    const auto& d = config.grid.spacing_m();
    return {d[config.roles[0]], d[config.roles[2]], config.dt.seconds(), config.grid.cells().values()[config.roles[0]],
            config.i_int};
}
// Exact discrete eigenvector along a at the discrete root, e[0..N_a].
std::vector<double> slab_shape(const Case& config) {
    const auto g = slab_geometry(config);
    const auto r = reduced_wavenumbers(config.f_d, g);
    const double scale = std::sin(r.k1 * static_cast<double>(g.i_int) * g.d_a) /
                         std::sin(r.k2 * static_cast<double>(g.n_a - g.i_int) * g.d_a);
    std::vector<double> shape;
    for (std::size_t i = 0; i <= g.n_a; ++i) {
        shape.push_back(i <= g.i_int ? std::sin(r.k1 * static_cast<double>(i) * g.d_a)
                                     : scale * std::sin(r.k2 * static_cast<double>(g.n_a - i) * g.d_a));
    }
    return shape;
}

// ---- Case construction --------------------------------------------------------
Case wave_case(std::size_t a, std::size_t b, std::size_t p, double sigma, std::string suite) {
    const auto c = 3 - a - b;
    const std::array<std::size_t, 3> roles{a, b, c};
    const double pd = static_cast<double>(p);
    const auto grid = make_grid(roles, {3 * p, 2 * p, 2 * p},
                                {wavelength * 1 / pd, wavelength * 1.5 / pd, wavelength * 2 / pd});
    const auto dt = VacuumTimeStep::from_courant(grid, 0.99);
    const double t = dt.seconds();
    const auto steps = static_cast<std::uint64_t>(std::floor(0.1 * (std::sqrt(loaded_eps_r) * wavelength / c0) / t));
    std::string name = (sigma == 0 ? "dielectric-" : "lossy-") + std::string(axes[a]) + axes[b] + "-p" + std::to_string(p);
    if (sigma != 0) name += sigma == 0.01 ? "-sig0p01" : "-sig0p1";
    Case config{std::move(name), std::move(suite), Kind::Wave, grid, dt, steps, roles, p, 0, loaded_eps_r, sigma, 0, false};
    const double big_k = discrete_k(grid.spacing_m()[a]);
    const double eps = loaded_eps_r * epsilon0;
    if (sigma == 0) {
        config.omega = 2 / t * std::asin(c0 * t * big_k / (2 * std::sqrt(loaded_eps_r)));
        config.z = std::polar(1.0, config.omega * t);
        config.h = std::polar(std::sqrt(loaded_eps_r) / eta0, -config.omega * t / 2);   // (1/eta) z^(-1/2)
    } else {
        config.z = lossy_step_root(t, big_k, eps, sigma);
        const Complex root = std::sqrt(config.z);
        const Complex hhat = Complex{0, t * big_k / mu0} / (root - 1.0 / root);
        config.h = hhat / root;
    }
    return config;
}

Case sheet_case(std::size_t a, std::size_t p, std::string suite) {
    const std::array<std::size_t, 3> roles{a, cyc(a, 1), cyc(a, 2)};
    const double pd = static_cast<double>(p);
    const std::size_t i_src = 15 * p, i_p1 = i_src + 2 * p, i_int = i_p1 + 8 * p, i_p2 = i_int + 2 * p;
    const auto grid = make_grid(roles, {i_p2 + 5 * p, 2, p}, {wavelength / pd, 1.5 * wavelength / pd, 2 * wavelength / pd});
    const auto dt = VacuumTimeStep::from_courant(grid, 0.99);
    const double period = 1 / f0();
    Case config{"interface-" + std::string(axes[a]) + "-p" + std::to_string(p), std::move(suite), Kind::Sheet, grid, dt,
                static_cast<std::uint64_t>(std::ceil(29.0 * period / dt.seconds())), roles, p, 0, loaded_eps_r, 0.0, i_int,
                false};
    config.i_src = i_src; config.i_p1 = i_p1; config.i_p2 = i_p2;
    config.gate = static_cast<std::uint64_t>(std::ceil(15.0 * period / dt.seconds()));
    return config;
}

Case slab_case(std::size_t a, std::size_t mode, std::size_t p, std::string suite) {
    const std::array<std::size_t, 3> roles{a, cyc(a, 1), cyc(a, 2)};
    const double pd = static_cast<double>(p);
    // v05c_geometry: (1, 2, 1) lambda0/p (the MAT-03 erratum of the specification text).
    const auto grid = make_grid(roles, {p, 2, 2 * p}, {wavelength / pd, 2 * wavelength / pd, wavelength / pd});
    const auto dt = VacuumTimeStep::from_courant(grid, 0.99);
    Case config{"slab-" + std::string(axes[a]) + "-m" + std::to_string(mode) + "-p" + std::to_string(p), std::move(suite),
                Kind::Slab, grid, dt, 0, roles, p, mode, loaded_eps_r, 0.0, p / 2, false};
    const auto g = slab_geometry(config);
    config.f_c = roots(slab_continuum, 2)[mode - 1];
    config.f_d = roots([&](double f) { return slab_discrete(f, g); }, mode)[mode - 1];
    config.omega = 2 * pi * config.f_d;
    config.steps = static_cast<std::uint64_t>(std::ceil(2.0 / config.f_c / dt.seconds()));
    return config;
}

Case modular_case(double q, std::string suite) {
    const UniformGrid grid{CellCounts{12, 14, 16}, {0.01, 0.015, 0.02}};
    const auto dt = VacuumTimeStep::from_courant(grid, q);
    return Case{std::string("dissipation-") + (q == 0.5 ? "q50" : "q99"), std::move(suite), Kind::Modular, grid, dt, 2000,
                {0, 1, 2}, 0, 0, 2.25, 0.01, 0, true};
}

std::size_t e_count(const UniformGrid& grid) {
    std::size_t count = 0;
    for (std::size_t id = 0; id < 3; ++id) count += grid.layout(component(id)).element_count;
    return count;
}
std::size_t current_count(const Case& config) {
    return config.kind == Kind::Sheet ? 2 * (config.grid.cells().values()[config.roles[2]] - 1) : 0;
}
// Two field payloads, mask, per-cell map, uint32 index, table allowance (one
// entry for a uniform map, at most five four-cell classes of two materials),
// probes, currents, retained previous E for D, and the fixed overhead.
std::size_t working_bytes(const Case& config) {
    const auto& grid = config.grid;
    const auto cells = grid.cells().values();
    const auto e = e_count(grid);
    return 2 * grid.field_bytes() + e + 16 * cells[0] * cells[1] * cells[2] + 4 * e +
        (config.i_int == 0 ? 1 : 5) * sizeof(EdgeMaterial) + probes(config).size() * sizeof(FieldProbe) +
        current_count(config) * sizeof(CurrentSample) + (config.diagnostics ? 8 * e : 0) + overhead;
}

double face_distance(const UniformGrid& grid, const std::array<double, 3>& r, std::size_t axis) {
    const double cells = r[axis] / grid.spacing_m()[axis];
    return std::min(cells, static_cast<double>(grid.cells().values()[axis]) - cells);
}

void preflight(const Case& config) {
    validate_run_steps(config.dt, config.steps);
    if (working_bytes(config) > budget) throw std::length_error("Material working memory exceeds 2 GiB.");
    if (config.kind == Kind::Wave) {
        const double required = 2 * static_cast<double>(config.steps) + 6;
        if (!(static_cast<double>(config.p) - 0.5 > required)) throw std::invalid_argument("Wave isolation guard failed.");
        for (const auto& probe : probes(config)) {
            const auto r = config.grid.position_m(probe.component, probe.index);
            for (std::size_t axis = 0; axis < 3; ++axis)
                if (!(face_distance(config.grid, r, axis) > required))
                    throw std::invalid_argument("Native probe dependency cone reaches taper.");
        }
    }
}

// ---- Fixtures ------------------------------------------------------------------
// FND-04 compact potentials: the H_c potential yields E_b = A cos(k r_a) in the
// plateau; the E_b potential yields H_c = s abs(h) cos(k r_a + phi), phi = -arg(h).
double wave_potential(const Case& config, std::size_t id, Index index) {
    const auto [a, b, c] = config.roles;
    const auto r = config.grid.position_m(component(id), index);
    double taper = 1;
    for (std::size_t axis = 0; axis < 3; ++axis)
        taper *= std::clamp((face_distance(config.grid, r, axis) - 2) / 2, 0.0, 1.0);
    const double k = 2 * pi / wavelength;
    const double big_k = discrete_k(config.grid.spacing_m()[a]);
    if (id == c + 3) return -static_cast<double>(orientation(a, b)) / big_k * taper * std::sin(k * r[a]);
    if (id == b) return taper * std::abs(config.h) / big_k * std::sin(k * r[a] - std::arg(config.h));
    return 0;
}
// FND-04 v1 V03 modular H potential (E potentials zero), zero within two cells of a face.
double modular_potential(const Case& config, std::size_t id, Index index) {
    const auto r = config.grid.position_m(component(id), index);
    for (std::size_t axis = 0; axis < 3; ++axis)
        if (face_distance(config.grid, r, axis) <= 2) return 0;
    if (id < 3) return 0;
    const auto residue = (17 * index[0] + 31 * index[1] + 43 * index[2] + 13 * (id - 3)) % 101;
    return 0.01 * (static_cast<double>(residue) - 50) / 50;
}

double eps_r_edge(const MaterialMap& map, std::size_t id, Index index) { return edge_average(map, id, index).first; }

// Discrete Gauss law div(eps_r,e E) (edge means from the benchmark library) and div H.
double divergence_error(const Case& config, const FieldStorage& fields, const MaterialMap& map) {
    const auto& grid = config.grid;
    const double dmin = *std::min_element(grid.spacing_m().begin(), grid.spacing_m().end());
    double worst = 0;
    for (bool electric : {true, false}) {
        each(grid.cells().values(), [&](Index index) {
            if (electric && (index[0] == 0 || index[1] == 0 || index[2] == 0)) return;
            double div = 0, scale = 0;
            for (std::size_t axis = 0; axis < 3; ++axis) {
                auto high = index, low = index;
                if (electric) --low[axis]; else ++high[axis];
                const auto f = component(axis + (electric ? 0U : 3U));
                double hi = fields.at(f, high), lo = fields.at(f, low);
                if (electric) { hi *= eps_r_edge(map, axis, high); lo *= eps_r_edge(map, axis, low); }
                hi /= grid.spacing_m()[axis]; lo /= grid.spacing_m()[axis];
                div += hi - lo; scale += std::abs(hi) + std::abs(lo);
            }
            const double error = std::abs(div) / std::max(scale, 1 / (dmin * (electric ? 1 : eta0)));
            if (!std::isfinite(error)) throw std::runtime_error("Nonfinite fixture divergence.");
            worst = std::max(worst, error);
        });
    }
    return worst;
}

bool update_range(const UniformGrid& grid, std::size_t id, Index index) {
    const auto n = grid.cells().values();
    for (std::size_t t = 0; t < 3; ++t)
        if (t != id && (index[t] == 0 || index[t] == n[t])) return false;
    return true;
}

// ---- Diagnostics -----------------------------------------------------------------
struct Diagnostics { double u, q, d; std::array<double, 6> maxima; };

double weight(const UniformGrid& grid, std::size_t id, Index index) {
    double w = 1;
    for (std::size_t axis = 0; axis < 3; ++axis) {
        const bool integer = id < 3 ? axis != id : axis == id - 3;
        if (integer && (index[axis] == 0 || index[axis] == grid.cells().values()[axis])) w *= 0.5;
    }
    return w;
}

// U, Q with eps weighting and D of the step ending at this state, by the
// library's own permutation differences, edge means and compensated sums.
Diagnostics diagnostics(const ReferenceStepper& solver, const MaterialMap& map,
                        std::array<std::vector<double>, 3>& previous, bool first) {
    const auto& fields = solver.fields();
    const auto& grid = fields.grid();
    Sum electric, magnetic, cross, joule;
    Diagnostics result{0, 0, 0, {}};
    all(grid, [&](std::size_t id, Index index) {
        const double value = fields.at(component(id), index);
        result.maxima[id] = std::max(result.maxima[id], std::abs(value));
        const double w = weight(grid, id, index);
        if (id < 3) {
            if (!update_range(grid, id, index)) return;          // constrained walls are exactly zero
            const auto [eps_r, sigma] = edge_average(map, id, index);
            electric.add(w * eps_r * value * value);
            auto& old = previous[id][grid.offset(component(id), index)];
            if (!first) {
                const double mean = (value + old) / 2;
                joule.add(w * sigma * mean * mean);
            }
            old = value;
        } else {
            magnetic.add(w * value * value);
            cross.add(w * value * curl(grid, id, index, [&](std::size_t source, Index at) {
                return fields.at(component(source), at);
            }));
        }
    });
    const auto d = grid.spacing_m();
    const double volume = d[0] * d[1] * d[2];
    const double dt = solver.time_step().seconds();
    result.u = volume / 2 * (epsilon0 * electric.total + mu0 * magnetic.total);
    result.q = result.u - volume * dt / 2 * cross.total;
    result.d = volume * dt * joule.total;
    if (!std::isfinite(result.u) || !std::isfinite(result.q) || !std::isfinite(result.d))
        throw std::runtime_error("Nonfinite energy diagnostic.");
    return result;
}

// ---- Metadata --------------------------------------------------------------------
const char* kind_name(Kind kind) {
    switch (kind) {
    case Kind::Wave: return "wave";
    case Kind::Sheet: return "sheet";
    case Kind::Slab: return "slab";
    case Kind::Modular: return "modular";
    }
    return "unknown";
}
const char* initialization(const Case& config) {
    switch (config.kind) {
    case Kind::Wave:
        return config.sigma == 0 ?
            "FND-04 compact potentials, discrete eigenwave: E_b=A cos(k r_a) at t=0; H_c=s abs(h) cos(k r_a+phi) "
            "at -dt/2 with h=(1/eta) z^(-1/2), phi=-arg(h)=omega_d dt/2" :
            "FND-04 compact potentials, exact lossy eigenwave: E_b=A cos(k r_a) at t=0; H_c=s abs(h) cos(k r_a+phi) "
            "at -dt/2 with h=hhat z^(-1/2), hhat/A=(i dt K/mu0)/(z^(1/2)-z^(-1/2)), phi=-arg(h)";
    case Kind::Sheet: return "zero fields";
    case Kind::Slab:
        return "exact discrete slab eigenvector: E_b=A e[i_a] sin(pi i_c/N_c) at t=0; "
               "H=+(C E_s) sin(omega_d dt/2)/(mu0 Omega) at -dt/2 by permutation curl";
    case Kind::Modular: return "FND-04 v1 normalized modular P curl";
    }
    return "unknown";
}
const char* source_text(const Case& config) {
    return config.kind == Kind::Sheet ?
        "J_b=J0 sin(pi i_c/N_c) g_n on every E_b edge of the plane i_src, J0=1 A/m^2, "
        "g_n=exp(-(((n+1/2) dt-t0)/tau)^2/2) cos(2 pi f0 ((n+1/2) dt-t0)), tau=1/(2 pi 0.15 f0), t0=4 tau, every step" :
        "J=0";
}
const char* material_rule(const Case& config) {
    switch (config.kind) {
    case Kind::Sheet:
    case Kind::Slab: return "eps_r=4, sigma=0 in cells with i_a>=i_int; vacuum elsewhere";
    default: return "uniform eps_r and sigma in every cell";
    }
}

void materials_json(std::ostream& out, const Case& config, const MaterialMap& map) {
    std::map<std::pair<double, double>, std::size_t> distinct;
    const auto eps = map.eps_r_values();
    const auto sigma = map.sigma_values();
    for (std::size_t cell = 0; cell < eps.size(); ++cell) ++distinct[{eps[cell], sigma[cell]}];
    out << "\"materials\":{\"rule\":\"" << material_rule(config) << "\",\"cells\":[";
    bool first = true;
    for (const auto& [value, count] : distinct) {
        out << (first ? "" : ",") << "{\"eps_r\":" << value.first << ",\"sigma_S_per_m\":" << value.second
            << ",\"count\":" << count << '}';
        first = false;
    }
    out << "],\"map_bytes\":" << map.bytes() << '}';
}

void metadata(const Case& config, const std::filesystem::path& path, FixtureChecks checks, double elapsed, bool complete,
              const MaterialMap& map, const EdgeCoefficients* table) {
    auto out = stream(path);
    const char* cpu = std::getenv("PROCESSOR_IDENTIFIER");
    const PecMask pec{config.grid};
    const auto [a, b, c] = config.roles;
    out << "{\n\"schema\":\"closed-v1-raw-1\",\n\"case_status\":\"" << (complete ? "raw_complete" : "incomplete")
        << "\",\n\"fixture_checks_status\":\"" << (complete ? "passed" : "pending") << "\",\n\"case\":\"" << config.name
        << "\",\n\"suite\":\"" << config.suite << "\",\n\"kind\":\"" << kind_name(config.kind)
        << "\",\n\"version\":\"" << version() << "\",\n\"source_snapshot_sha256\":\"" << ANTENNASIM_SOURCE_SNAPSHOT
        << "\",\n\"compiler\":\"" << ANTENNASIM_COMPILER << "\",\n"
        << "\"build_type\":\"" << ANTENNASIM_BUILD_TYPE << "\",\n\"cpu_identifier\":";
    json_string(out, cpu == nullptr ? "unavailable" : cpu);
    out << ",\"hardware_threads\":" << std::thread::hardware_concurrency() << ",\n"
        << "\"backend\":\"scalar CPU\",\"fp_policy\":\"strict, no fast math, no contraction\",\n"
        << "\"output_kind\":\"solver samples; fixture, material, geometry, source and prediction values are deterministic calculations\",\n"
        << "\"boundary\":\"zero_tangential_e; pec_shell of the whole domain; initially zero enclosed H\",\n"
        << "\"pec_primitives\":[],\n\"masked_edges\":"; json_array(out, pec.masked_counts());
    out << ",\"closure_edges\":"; json_array(out, pec.closure_counts());
    out << ",\n\"units\":{\"length\":\"m\",\"time\":\"s\",\"E\":\"V/m\",\"H\":\"A/m\",\"J\":\"A/m^2\",\"energy\":\"J\",\"sigma\":\"S/m\"},\n"
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
        << ",\"steps\":" << config.steps << ",\"roles\":"; json_array(out, config.roles);
    out << ",\"a\":" << a << ",\"b\":" << b << ",\"c\":" << c << ",\"p\":" << config.p << ",\"mode\":" << config.mode
        << ",\"eps_r\":" << config.eps_r << ",\"sigma_S_per_m\":" << config.sigma << ",\"i_int\":" << config.i_int
        << ",\"region\":false,\"diagnostics\":" << (config.diagnostics ? "true" : "false")
        << ",\n\"initialization\":\"" << initialization(config) << "\",\n\"source\":\"" << source_text(config) << '"';
    if (config.kind == Kind::Wave) {
        out << ",\n\"amplitude_V_per_m\":1,\"wavelength_m\":" << wavelength << ",\"omega_d\":" << config.omega
            << ",\"z\":[" << config.z.real() << ',' << config.z.imag() << "],\"h\":[" << config.h.real() << ','
            << config.h.imag() << "],\"eta_ohm\":" << eta0 / std::sqrt(config.eps_r);
    } else if (config.kind == Kind::Sheet) {
        const double tau = 1 / (2 * pi * 0.15 * f0());
        out << ",\n\"i_src\":" << config.i_src << ",\"i_p1\":" << config.i_p1 << ",\"i_p2\":" << config.i_p2
            << ",\"gate\":" << config.gate << ",\"J0_A_per_m2\":1,\"f0_hz\":" << f0() << ",\"tau_s\":" << tau
            << ",\"t0_s\":" << 4 * tau;
    } else if (config.kind == Kind::Slab) {
        out << ",\n\"amplitude_V_per_m\":1,\"f_d_hz\":" << config.f_d << ",\"f_c_hz\":" << config.f_c
            << ",\"omega_d\":" << config.omega;
    }
    out << ",\n\"probe_indices\":[],\n";
    materials_json(out, config, map);
    if (table != nullptr) { out << ",\n"; coefficients_json(out, *table); }
    const auto e = e_count(config.grid);
    out << ",\n\"charge\":\"rho initially zero (discrete div(eps_r,e E)=0); later charge by continuity and conduction\",\n"
        << "\"native_time\":\"E=n*dt; H=(n-0.5)*dt; rows include n=0\",\n"
        << "\"diagnostic_weights\":\"half per transverse E outer wall, half per normal H outer wall; E weighted by eps_r,e; "
           "D_J on row n is the dissipation of the step from n-1 to n\",\n"
        << "\"fixture_max_divergence_error\":" << checks.divergence << ",\"fixture_max_plateau_error\":" << checks.plateau
        << ",\"fixture_max_eigen_error\":" << checks.eigen
        << ",\"field_bytes\":" << config.grid.field_bytes() << ",\"mask_bytes\":" << pec.mask_bytes()
        << ",\"map_bytes\":" << map.bytes() << ",\"coefficient_index_bytes\":" << 4 * e
        << ",\"diagnostic_bytes\":" << (config.diagnostics ? 8 * e : 0)
        << ",\"working_bytes_budgeted\":" << working_bytes(config)
        << ",\"elapsed_seconds\":" << elapsed << "\n}\n";
    out.close();
}
} // namespace

bool is_suite(std::string_view suite) {
    return suite == "dielectric" || suite == "interface" || suite == "slab-cavity" || suite == "lossy" ||
           suite == "dissipation";
}

std::vector<Case> cases(std::string_view suite, std::uint64_t smoke_steps) {
    std::vector<Case> result;
    const std::string label{suite};
    const std::array<std::array<std::size_t, 2>, 6> orderings{{{0, 1}, {0, 2}, {1, 0}, {1, 2}, {2, 0}, {2, 1}}};
    if (suite == "dielectric") {
        for (const auto& [a, b] : orderings)
            for (std::size_t p : {24U, 48U, 96U}) result.push_back(wave_case(a, b, p, 0.0, label));
    } else if (suite == "interface") {
        for (std::size_t p : {16U, 32U})
            for (std::size_t a = 0; a < 3; ++a) result.push_back(sheet_case(a, p, label));
        result.push_back(sheet_case(0, 64, label));
    } else if (suite == "slab-cavity") {
        for (std::size_t a = 0; a < 3; ++a)
            for (std::size_t mode : {1U, 2U})
                for (std::size_t p : {24U, 48U, 96U}) result.push_back(slab_case(a, mode, p, label));
    } else if (suite == "lossy") {
        for (const double sigma : {0.01, 0.1}) {
            for (const auto& [a, b] : orderings)
                for (std::size_t p : {24U, 48U}) result.push_back(wave_case(a, b, p, sigma, label));
            result.push_back(wave_case(0, 1, 96, sigma, label));
        }
    } else if (suite == "dissipation") {
        for (const double q : {0.99, 0.5}) result.push_back(modular_case(q, label));
    } else if (suite == "smoke") {
        result.push_back(wave_case(0, 1, 24, 0.0, "dielectric"));
        result.push_back(sheet_case(0, 16, "interface"));
        result.push_back(slab_case(0, 1, 24, "slab-cavity"));
        result.push_back(wave_case(0, 1, 24, 0.1, "lossy"));
        result.push_back(modular_case(0.99, "dissipation"));
        for (auto& config : result) { config.steps = smoke_steps; config.diagnostics = true; }
    } else throw std::invalid_argument("Unknown material suite.");
    for (const auto& config : result) preflight(config);
    return result;
}

MaterialMap materials(const Case& config) {
    if (config.i_int == 0) return MaterialMap::uniform(config.grid, config.eps_r, config.sigma);
    const auto n = config.grid.cells().values();
    const auto a = config.roles[0];
    std::vector<double> eps, sigma;
    eps.reserve(n[0] * n[1] * n[2]);
    sigma.reserve(n[0] * n[1] * n[2]);
    each(n, [&](Index cell) {
        const bool loaded = cell[a] >= config.i_int;
        eps.push_back(loaded ? config.eps_r : 1.0);
        sigma.push_back(loaded ? config.sigma : 0.0);
    });
    return MaterialMap{config.grid, std::move(eps), std::move(sigma)};
}

std::vector<FieldProbe> probes(const Case& config) {
    std::vector<FieldProbe> result;
    const auto n = config.grid.cells().values();
    const auto [a, b, c] = config.roles;
    switch (config.kind) {
    case Kind::Wave:
        for (std::size_t id = 0; id < 6; ++id) {
            Index index{n[0] / 2, n[1] / 2, n[2] / 2};
            for (std::size_t axial = config.p; axial < 2 * config.p; ++axial) {
                index[a] = axial;
                result.push_back({component(id), index});
            }
        }
        break;
    case Kind::Sheet: {
        Index index{};
        index[a] = config.i_p1;
        index[b] = 0;
        for (std::size_t k = 0; k <= n[c]; ++k) { index[c] = k; result.push_back({component(b), index}); }
        index[c] = n[c] / 2;
        for (const auto& [axial, plane] : {std::pair{config.i_p2, std::size_t{0}}, std::pair{config.i_p1, std::size_t{1}},
                                           std::pair{config.i_p2, std::size_t{1}}}) {
            index[a] = axial; index[b] = plane;
            result.push_back({component(b), index});
        }
        break;
    }
    case Kind::Slab: {
        Index index{};
        index[b] = 0;
        index[c] = n[c] / 2;
        for (std::size_t i = 0; i <= n[a]; ++i) { index[a] = i; result.push_back({component(b), index}); }
        break;
    }
    case Kind::Modular:
        for (std::size_t id = 0; id < 6; ++id) result.push_back({component(id), Index{n[0] / 2, n[1] / 2, n[2] / 2}});
        break;
    }
    return result;
}

std::vector<double> sheet_pulse(const Case& config) {
    const double tau = 1 / (2 * pi * (0.15 * f0()));
    const double t0 = 4 * tau;
    const double dt = config.dt.seconds();
    std::vector<double> samples;
    for (std::uint64_t m = 0; m < config.steps; ++m) {
        const double t = (static_cast<double>(m) + 0.5) * dt - t0;
        samples.push_back(std::exp(-(t / tau) * (t / tau) / 2) * std::cos(2 * pi * f0() * t));
    }
    return samples;
}

FixtureChecks initialize(const Case& config, FieldStorage& fields) {
    if (fields.grid().cells().values() != config.grid.cells().values() ||
        fields.grid().spacing_m() != config.grid.spacing_m()) throw std::invalid_argument("Fixture/grid mismatch.");
    preflight(config);
    const auto& grid = config.grid;
    const auto map = materials(config);
    const auto [a, b, c] = config.roles;
    all(grid, [&](std::size_t id, Index index) { fields.at(component(id), index) = 0; });
    FixtureChecks checks;
    if (config.kind == Kind::Wave || config.kind == Kind::Modular) {
        double maximum = 0;
        const auto potential = [&](std::size_t source, Index at) {
            return config.kind == Kind::Wave ? wave_potential(config, source, at) : modular_potential(config, source, at);
        };
        all(grid, [&](std::size_t id, Index index) {
            if (id < 3 && !update_range(grid, id, index)) return;
            auto& value = fields.at(component(id), index);
            value = curl(grid, id, index, potential);
            maximum = std::max(maximum, std::abs(value));
        });
        if (config.kind == Kind::Modular) {
            if (!(maximum > 0 && std::isfinite(maximum))) throw std::runtime_error("Zero/nonfinite modular shape.");
            all(grid, [&](std::size_t id, Index index) { fields.at(component(id), index) /= maximum; });
        } else {
            // Plateau values against the closed form (E at t=0, H at -dt/2).
            const double k = 2 * pi / wavelength;
            const double eta = eta0 / std::sqrt(config.eps_r);
            for (const auto& probe : probes(config)) {
                const auto id = static_cast<std::size_t>(probe.component);
                const double r = grid.position_m(probe.component, probe.index)[a];
                const double expected = id == b ? std::cos(k * r) :
                    id == c + 3 ? orientation(a, b) * std::abs(config.h) * std::cos(k * r - std::arg(config.h)) : 0.0;
                checks.plateau = std::max(checks.plateau,
                    std::abs(fields.at(probe.component, probe.index) - expected) * (id < 3 ? 1 : eta));
            }
        }
    } else if (config.kind == Kind::Slab) {
        const auto shape = slab_shape(config);
        const double n_c = static_cast<double>(grid.cells().values()[c]);
        each(grid.layout(component(b)).extents, [&](Index index) {
            if (!update_range(grid, b, index)) return;
            fields.at(component(b), index) = shape[index[a]] * std::sin(pi * static_cast<double>(index[c]) / n_c);
        });
        const double dt = config.dt.seconds();
        const double big_omega = 2 / dt * std::sin(config.omega * dt / 2);
        const double factor = std::sin(config.omega * dt / 2) / (mu0 * big_omega);
        const auto electric = [&](std::size_t source, Index at) { return fields.at(component(source), at); };
        for (std::size_t id = 3; id < 6; ++id)
            each(grid.layout(component(id)).extents, [&](Index index) {
                fields.at(component(id), index) = curl(grid, id, index, electric) * factor;
            });
        // Exact eigenvector identity C*C E = mu0 eps_e Omega^2 E on every unconstrained edge.
        const auto g = [&](std::size_t source, Index at) { return curl(grid, source, at, electric); };
        for (std::size_t id = 0; id < 3; ++id)
            each(grid.layout(component(id)).extents, [&](Index index) {
                if (!update_range(grid, id, index)) return;
                const double scale = mu0 * epsilon0 * eps_r_edge(map, id, index) * big_omega * big_omega;
                const double error = std::abs(curl(grid, id, index, g) - scale * fields.at(component(id), index)) / scale;
                if (!std::isfinite(error)) throw std::runtime_error("Nonfinite slab eigen check.");
                checks.eigen = std::max(checks.eigen, error);
            });
    }
    all(grid, [&](std::size_t id, Index index) {
        const double value = fields.at(component(id), index);
        if (!std::isfinite(value)) throw std::runtime_error("Nonfinite fixture.");
        if ((grid.is_tangential_e_wall(component(id), index) || grid.is_normal_h_wall(component(id), index)) && value != 0)
            throw std::runtime_error("Nonzero fixture wall.");
    });
    checks.divergence = divergence_error(config, fields, map);
    if (checks.divergence > 1e-11 || checks.plateau > 1e-11 || checks.eigen > 1e-11)
        throw std::runtime_error("Material fixture identity failed.");
    return checks;
}

void run_case(const Case& config, const std::filesystem::path& path) {
    const auto started = std::chrono::steady_clock::now();
    if (!std::filesystem::create_directory(path)) throw std::runtime_error("Case directory already exists.");
    auto map = std::make_unique<MaterialMap>(materials(config));
    metadata(config, path / "configuration.json", {}, 0, false, *map, nullptr);
    auto initial = std::make_unique<FieldStorage>(config.grid);
    const auto checks = initialize(config, *initial);
    std::vector<CurrentSample> current_samples;
    std::vector<double> pulse;
    if (config.kind == Kind::Sheet) {
        const auto [a, b, c] = config.roles;
        const auto n_c = config.grid.cells().values()[c];
        for (std::size_t plane = 0; plane < 2; ++plane)
            for (std::size_t k = 1; k < n_c; ++k) {
                Index index{};
                index[a] = config.i_src; index[b] = plane; index[c] = k;
                current_samples.push_back({component(b), index,
                    std::sin(pi * static_cast<double>(k) / static_cast<double>(n_c))});
            }
        pulse = sheet_pulse(config);
    }
    const ElectricCurrent current{config.grid, std::move(current_samples)};
    ReferenceStepper solver{*initial, config.dt, PecMask{config.grid}, *map};
    initial.reset();
    std::array<std::vector<double>, 3> previous;
    if (config.diagnostics)
        for (std::size_t id = 0; id < 3; ++id) previous[id].assign(config.grid.layout(component(id)).element_count, 0.0);
    else map.reset();
    auto raw = stream(path / "probes.csv");
    auto energy = stream(path / "diagnostics.csv");
    raw << "state,component,i,j,k,x_m,y_m,z_m,time_s,value\n";
    energy << "state,e_time_s,h_time_s,U_J,Q_J,D_J";
    for (const auto name : names) energy << ",max_" << name;
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
            const auto values = diagnostics(solver, *map, previous, n == 0);
            energy << n << ',' << solver.times().e_s << ',' << solver.times().h_s << ',' << values.u << ',' << values.q
                   << ',' << values.d;
            for (auto maximum : values.maxima) energy << ',' << maximum;
            energy << '\n';
        }
        if (n == config.steps) break;
        if (config.kind == Kind::Sheet) solver.step(current, pulse[n]);
        else solver.step();
    }
    raw.close(); energy.close();
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
    if (!map) map = std::make_unique<MaterialMap>(materials(config));
    metadata(config, path / "metadata.json", checks, elapsed, true, *map, &solver.coefficients());
}
} // namespace antennasim::benchmark::material
