// S10-S13 structural checks of the per-cell material map, the MAT-01 edge
// coefficients and the lossy update (MAT-01 specification, MAT-03 contract).
// Independent enumerations and formulas; the production averaging, curl and
// coefficient code are never used as their own oracle. Select a group with
// --check s10|s11|s12|s13.
#include "antennasim/material.hpp"
#include "antennasim/vacuum.hpp"
#include "antennasim/detail/vacuum_kernel.hpp"
#include "material_steps_golden.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <string_view>

namespace {
using namespace antennasim;
using enum FieldComponent;
using Index = std::array<std::size_t, 3>;
constexpr std::array components{Ex, Ey, Ez, Hx, Hy, Hz};
std::size_t checks = 0;
double worst_coefficient = 0, worst_single = 0, worst_golden = 0, worst_identity = 0;

void check(bool condition, std::string_view context) {
    ++checks;
    if (!condition) throw std::runtime_error(std::string(context));
}
template <class Error, class Function>
void rejects(Function function, std::string_view context) {
    bool rejected = false;
    try { function(); } catch (const Error&) { rejected = true; }
    check(rejected, context);
}
template <class Function>
void enumerate(Index shape, Function function) {
    for (std::size_t k = 0; k < shape[2]; ++k)
        for (std::size_t j = 0; j < shape[1]; ++j)
            for (std::size_t i = 0; i < shape[0]; ++i) function(Index{i, j, k});
}
template <class Function>
void all(const UniformGrid& grid, Function function) {
    for (std::size_t id = 0; id < 6; ++id)
        enumerate(grid.layout(components[id]).extents, [&](Index index) { function(id, index); });
}

UniformGrid grid_of(Index cells, std::array<double, 3> spacing = {2, 3, 5}) {
    return UniformGrid{CellCounts{cells[0], cells[1], cells[2]}, spacing};
}
// Tangential outer-wall E (transverse integer index on a face) or normal outer-wall H.
bool constrained(const UniformGrid& grid, std::size_t id, Index index) {
    const auto n = grid.cells().values();
    for (std::size_t t = 0; t < 3; ++t) {
        const bool integer = id < 3 ? t != id : t == id - 3;
        if (integer && (index[t] == 0 || index[t] == n[t])) return true;
    }
    return false;
}

// S10 modular map: v = max(0, ((17i+31j+43k) mod 101) - 50), eps_r = 1 + v/60, sigma = v/50.
double modular_value(Index cell) {
    const auto v = static_cast<long long>((17 * cell[0] + 31 * cell[1] + 43 * cell[2]) % 101) - 50;
    return static_cast<double>(std::max(0LL, v));
}
MaterialMap modular_map(const UniformGrid& grid) {
    std::vector<double> eps, sigma;
    enumerate(grid.cells().values(), [&](Index cell) {
        eps.push_back(1.0 + modular_value(cell) / 60.0);
        sigma.push_back(modular_value(cell) / 50.0);
    });
    return MaterialMap{grid, eps, sigma};
}
// Maps whose sigma does not follow eps_r (added in the 2026-09-25 review: in the
// modular map equal eps_r,e implies equal sigma_e, so a table key that ignored
// sigma passed every check). Constant eps_r with varying sigma, and eps_r and
// sigma from unrelated modular values.
MaterialMap independent_map(const UniformGrid& grid, bool constant_eps) {
    std::vector<double> eps, sigma;
    enumerate(grid.cells().values(), [&](Index cell) {
        eps.push_back(constant_eps ? 4.0 : 1.0 + modular_value(cell) / 60.0);
        sigma.push_back(static_cast<double>((7 * cell[0] + 11 * cell[1] + 13 * cell[2]) % 5) / 10.0);
    });
    return MaterialMap{grid, eps, sigma};
}

// Independent edge averages: every cell deposits its values on its twelve
// edges (cell -> edge enumeration); an edge with four deposits is interior.
struct Deposits { std::array<double, 4> eps{}, sigma{}; std::size_t count = 0; };
std::map<std::pair<std::size_t, Index>, Deposits> edge_deposits(const UniformGrid& grid, const MaterialMap& map) {
    std::map<std::pair<std::size_t, Index>, Deposits> result;
    enumerate(grid.cells().values(), [&](Index cell) {
        for (std::size_t a = 0; a < 3; ++a) {
            const auto b = (a + 1) % 3, c = (a + 2) % 3;
            for (std::size_t db = 0; db < 2; ++db)
                for (std::size_t dc = 0; dc < 2; ++dc) {
                    Index edge = cell;
                    edge[b] += db;
                    edge[c] += dc;
                    auto& entry = result[{a, edge}];
                    entry.eps[entry.count] = map.eps_r(cell);
                    entry.sigma[entry.count] = map.sigma(cell);
                    ++entry.count;
                }
        }
    });
    return result;
}
struct Expected { double eps_r, sigma, x, ca, cb; };
Expected formula(double eps_r, double sigma, double dt) {
    const double eps = epsilon0 * eps_r;
    const double x = sigma * dt / eps / 2;
    return {eps_r, sigma, x, (1 - x) / (1 + x), dt / eps / (1 + x)};
}
bool relative(double actual, double expected, double limit, double floor = 0) {
    const double scale = std::max(std::abs(expected), floor);
    if (scale == 0) return actual == 0;
    const double error = std::abs(actual - expected) / scale;
    worst_coefficient = std::max(worst_coefficient, error);
    return error <= limit;
}

void coefficients_against_enumeration(const UniformGrid& grid, const MaterialMap& map, const VacuumTimeStep& dt) {
    const EdgeCoefficients coefficients{map, dt};
    const auto deposits = edge_deposits(grid, map);
    std::vector<std::size_t> used(coefficients.table().size(), 0);
    std::size_t interior = 0;
    for (std::size_t a = 0; a < 3; ++a) {
        enumerate(grid.layout(components[a]).extents, [&](Index index) {
            const auto found = deposits.find({a, index});
            const std::size_t count = found == deposits.end() ? 0 : found->second.count;
            check(constrained(grid, a, index) == (count != 4), "interior edges are exactly those shared by four cells");
            if (count != 4) {
                rejects<std::out_of_range>([&] { (void)coefficients.at(components[a], index); }, "wall edge coefficients undefined");
                return;
            }
            ++interior;
            double eps = 0, sigma = 0;
            for (std::size_t n = 0; n < 4; ++n) { eps += found->second.eps[n]; sigma += found->second.sigma[n]; }
            const auto expected = formula(eps / 4, sigma / 4, dt.seconds());
            const auto& actual = coefficients.at(components[a], index);
            check(relative(actual.eps_r, expected.eps_r, 1e-15) && relative(actual.sigma_s_per_m, expected.sigma, 1e-15) &&
                  relative(actual.x, expected.x, 1e-15) && relative(actual.ca, expected.ca, 1e-15, 1.0) &&
                  relative(actual.cb, expected.cb, 1e-15), "edge coefficients equal the independent average and formula");
            const auto offset = grid.offset(components[a], index);
            ++used[coefficients.indices(components[a])[offset]];
        });
    }
    std::size_t total = 0;
    for (std::size_t e = 0; e < used.size(); ++e) {
        check(used[e] == coefficients.table()[e].edges && used[e] > 0, "entry edge counts equal the enumeration");
        total += used[e];
        for (std::size_t f = 0; f < e; ++f) {
            const auto& p = coefficients.table()[e];
            const auto& q = coefficients.table()[f];
            check(!(p.eps_r == q.eps_r && p.sigma_s_per_m == q.sigma_s_per_m), "table entries are distinct");
        }
    }
    check(total == interior, "every update-range edge is classified once");
    check(coefficients.index_bytes() == 4 * (grid.layout(Ex).element_count + grid.layout(Ey).element_count +
                                              grid.layout(Ez).element_count), "index bytes are four per E sample");
}

bool same_entry(const EdgeMaterial& a, const EdgeMaterial& b) {
    return a.eps_r == b.eps_r && a.sigma_s_per_m == b.sigma_s_per_m && a.x == b.x && a.ca == b.ca && a.cb == b.cb &&
           a.edges == b.edges;
}

void fill_modular(FieldStorage& fields, int offset = 0) {
    const auto& grid = fields.grid();
    all(grid, [&](std::size_t id, Index index) {
        fields.at(components[id], index) = constrained(grid, id, index) ? 0.0 :
            static_cast<double>(static_cast<long long>((17 * index[0] + 31 * index[1] + 43 * index[2] + 13 * id +
                static_cast<std::size_t>(offset)) % 101) - 50);
    });
}
bool bitwise_equal(const FieldStorage& a, const FieldStorage& b) {
    bool equal = true;
    all(a.grid(), [&](std::size_t id, Index index) {
        // Bit patterns, so that +0 and -0 differ.
        equal = equal && std::bit_cast<std::uint64_t>(a.at(components[id], index)) ==
                             std::bit_cast<std::uint64_t>(b.at(components[id], index));
    });
    return equal;
}

// Divergence-free test fixture (uniform material): E = C*(P_H), H = C(P_E) of
// modular potentials, evaluated by explicit component equations.
void curl_fixture(FieldStorage& fields) {
    const auto& grid = fields.grid();
    FieldStorage potential{grid};
    const auto n = grid.cells().values();
    all(grid, [&](std::size_t id, Index index) {
        bool inside = true;
        for (std::size_t t = 0; t < 3; ++t) inside = inside && index[t] >= 1 && index[t] + 1 <= n[t];
        potential.at(components[id], index) = inside ?
            static_cast<double>(static_cast<long long>((17 * index[0] + 31 * index[1] + 43 * index[2] + 13 * id) % 101) - 50) / 100 : 0.0;
    });
    const auto [dx, dy, dz] = grid.spacing_m();
    all(grid, [&](std::size_t id, Index index) {
        auto& target = fields.at(components[id], index);
        target = 0;
        if (constrained(grid, id, index)) return;
        const auto [i, j, k] = index;
        const auto& p = potential;
        switch (id) {
        case 0: target = (p.at(Hz, {i,j,k}) - p.at(Hz, {i,j-1,k})) / dy - (p.at(Hy, {i,j,k}) - p.at(Hy, {i,j,k-1})) / dz; break;
        case 1: target = (p.at(Hx, {i,j,k}) - p.at(Hx, {i,j,k-1})) / dz - (p.at(Hz, {i,j,k}) - p.at(Hz, {i-1,j,k})) / dx; break;
        case 2: target = (p.at(Hy, {i,j,k}) - p.at(Hy, {i-1,j,k})) / dx - (p.at(Hx, {i,j,k}) - p.at(Hx, {i,j-1,k})) / dy; break;
        case 3: target = (p.at(Ez, {i,j+1,k}) - p.at(Ez, {i,j,k})) / dy - (p.at(Ey, {i,j,k+1}) - p.at(Ey, {i,j,k})) / dz; break;
        case 4: target = (p.at(Ex, {i,j,k+1}) - p.at(Ex, {i,j,k})) / dz - (p.at(Ez, {i+1,j,k}) - p.at(Ez, {i,j,k})) / dx; break;
        default: target = (p.at(Ey, {i+1,j,k}) - p.at(Ey, {i,j,k})) / dx - (p.at(Ex, {i,j+1,k}) - p.at(Ex, {i,j,k})) / dy; break;
        }
    });
}
// Backward-difference curl of H at an interior E sample (explicit equations).
double curl_h(const FieldStorage& f, std::size_t id, Index index) {
    const auto [i, j, k] = index;
    const auto [dx, dy, dz] = f.grid().spacing_m();
    if (id == 0) return (f.at(Hz, {i,j,k}) - f.at(Hz, {i,j-1,k})) / dy - (f.at(Hy, {i,j,k}) - f.at(Hy, {i,j,k-1})) / dz;
    if (id == 1) return (f.at(Hx, {i,j,k}) - f.at(Hx, {i,j,k-1})) / dz - (f.at(Hz, {i,j,k}) - f.at(Hz, {i-1,j,k})) / dx;
    return (f.at(Hy, {i,j,k}) - f.at(Hy, {i-1,j,k})) / dx - (f.at(Hx, {i,j,k}) - f.at(Hx, {i,j-1,k})) / dy;
}
// Forward-difference curl of E at an H sample (explicit equations).
double curl_e(const FieldStorage& f, std::size_t id, Index index) {
    const auto [i, j, k] = index;
    const auto [dx, dy, dz] = f.grid().spacing_m();
    if (id == 3) return (f.at(Ez, {i,j+1,k}) - f.at(Ez, {i,j,k})) / dy - (f.at(Ey, {i,j,k+1}) - f.at(Ey, {i,j,k})) / dz;
    if (id == 4) return (f.at(Ex, {i,j,k+1}) - f.at(Ex, {i,j,k})) / dz - (f.at(Ez, {i+1,j,k}) - f.at(Ez, {i,j,k})) / dx;
    return (f.at(Ey, {i+1,j,k}) - f.at(Ey, {i,j,k})) / dx - (f.at(Ex, {i,j+1,k}) - f.at(Ex, {i,j,k})) / dy;
}

void s10() {
    for (const Index cells : {Index{2, 3, 4}, Index{5, 4, 3}}) {
        const auto grid = grid_of(cells);
        const auto dt = VacuumTimeStep::from_courant(grid);
        coefficients_against_enumeration(grid, modular_map(grid), dt);
        coefficients_against_enumeration(grid, independent_map(grid, true), dt);
        coefficients_against_enumeration(grid, independent_map(grid, false), dt);
        // Vacuum: Ca = 1, x = 0 and Cb = dt/epsilon0 bitwise, identical to the default table.
        const EdgeCoefficients vacuum_map{MaterialMap::uniform(grid, 1, 0), dt};
        const auto vacuum = EdgeCoefficients::vacuum(grid, dt);
        check(vacuum_map.table().size() == 1 && vacuum.table().size() == 1, "vacuum has one table entry");
        const auto& entry = vacuum_map.table().front();
        check(entry.ca == 1.0 && entry.x == 0.0 && entry.cb == dt.e_scale() && entry.cb == dt.seconds() / epsilon0 &&
              entry.eps_r == 1.0 && entry.sigma_s_per_m == 0.0, "vacuum map gives Ca=1 and Cb=dt/epsilon0 bitwise");
        check(same_entry(entry, vacuum.table().front()), "vacuum map table equals the default table");
        for (std::size_t a = 0; a < 3; ++a) {
            const auto x = vacuum_map.indices(components[a]);
            const auto y = vacuum.indices(components[a]);
            check(std::equal(x.begin(), x.end(), y.begin(), y.end()), "vacuum index arrays equal");
        }
        // Rejections before anything is stored.
        const auto count = cells[0] * cells[1] * cells[2];
        const auto bad = [&](std::size_t cell, double eps, double sigma) {
            std::vector<double> e(count, 2.0), s(count, 0.5);
            e[cell] = eps; s[cell] = sigma;
            rejects<std::invalid_argument>([&] { (void)MaterialMap{grid, e, s}; }, "invalid cell material rejected");
        };
        const double nan = std::numeric_limits<double>::quiet_NaN(), inf = std::numeric_limits<double>::infinity();
        for (std::size_t cell : {std::size_t{0}, count - 1}) {
            bad(cell, 0.999999999, 0); bad(cell, 0, 0); bad(cell, -1, 0); bad(cell, 1, -1e-300); bad(cell, 1, -1);
            bad(cell, nan, 0); bad(cell, inf, 0); bad(cell, -inf, 0); bad(cell, 1, nan); bad(cell, 1, inf);
        }
        rejects<std::invalid_argument>([&] { (void)MaterialMap(grid, std::vector<double>(count - 1, 1), std::vector<double>(count, 0)); }, "short eps array");
        rejects<std::invalid_argument>([&] { (void)MaterialMap(grid, std::vector<double>(count, 1), std::vector<double>(count + 1, 0)); }, "long sigma array");
        rejects<std::invalid_argument>([&] { (void)MaterialMap::uniform(grid, 0.5, 0); }, "uniform eps_r<1");
        rejects<std::invalid_argument>([&] { (void)MaterialMap::uniform(grid, 1, -0.5); }, "uniform sigma<0");
        rejects<std::invalid_argument>([&] { (void)MaterialMap::uniform(grid, nan, 0); }, "uniform nonfinite eps");
        const auto other = grid_of(Index{cells[0] + 1, cells[1], cells[2]});
        FieldStorage zero{grid};
        rejects<std::invalid_argument>([&] { ReferenceStepper s{zero, dt, MaterialMap::uniform(other, 2, 0)}; }, "material cells mismatch");
        const auto stretched = grid_of(cells, {2, 3, 6});
        rejects<std::invalid_argument>([&] { (void)EdgeCoefficients(MaterialMap::uniform(stretched, 2, 0), dt); }, "material spacing mismatch");
        rejects<std::out_of_range>([&] { (void)MaterialMap::uniform(grid, 1, 0).eps_r({cells[0], 0, 0}); }, "cell bounds");
        rejects<std::invalid_argument>([&] { (void)vacuum.indices(Hx); }, "H carries no coefficients");
    }
    // Material kernel with vacuum coefficients is bitwise the P1 kernels (closure and interior shell).
    const auto grid = grid_of({6, 5, 4});
    const auto dt = VacuumTimeStep::from_courant(grid);
    const auto vacuum = EdgeCoefficients::vacuum(grid, dt);
    for (bool shell : {false, true}) {
        std::vector<PecPrimitive> primitives;
        if (shell) primitives.push_back({PecShape::Shell, CellBox{{1, 1, 1}, {4, 4, 3}}});
        const PecMask mask{grid, primitives};
        FieldStorage a{grid}, b{grid};
        fill_modular(a); fill_modular(b);
        all(grid, [&](std::size_t id, Index index) {
            if (mask.masked(components[id], index)) { a.at(components[id], index) = 0; b.at(components[id], index) = 0; }
        });
        for (std::uint64_t n = 0; n < 2; ++n) {
            detail::advance_h(a, dt, n); detail::advance_h(b, dt, n);
            if (shell) detail::advance_e(a, dt, n, mask); else detail::advance_e(a, dt, n);
            detail::advance_e(b, dt, n, mask, vacuum);
            check(bitwise_equal(a, b), "material kernel with vacuum coefficients equals the P1 kernel bitwise");
        }
    }
    // Stepper: default, vacuum map, and masked forms bitwise identical over driven steps.
    // Every constructor shares the material kernel, so these three agree by
    // construction; the independent reference is a transcription of the P1
    // (REF-04/MAT-02) step: the P1 kernels, then E <- E - e_scale*(amplitude*J)
    // (added in the 2026-09-25 review; a reassociated source term passed before).
    FieldStorage initial{grid};
    curl_fixture(initial);
    const ElectricCurrent current{grid, {{Ez, {2, 2, 1}, 0.7}, {Ex, {3, 1, 2}, -1.3}}};
    ReferenceStepper p1{initial, dt};
    ReferenceStepper mapped{initial, dt, MaterialMap::uniform(grid, 1, 0)};
    ReferenceStepper masked{initial, dt, PecMask{grid}, MaterialMap::uniform(grid, 1, 0)};
    FieldStorage transcribed{grid};
    curl_fixture(transcribed);
    const PecMask closure{grid};
    for (int n = 0; n < 3; ++n) {
        const double amplitude = 0.3 + 0.7 * n;   // not dyadic: a reassociated product rounds differently
        p1.step(current, amplitude); mapped.step(current, amplitude); masked.step(current, amplitude);
        detail::advance_h(transcribed, dt, static_cast<std::uint64_t>(n));
        detail::advance_e(transcribed, dt, static_cast<std::uint64_t>(n), closure);
        for (const auto& sample : current.samples()) {
            auto& value = transcribed.at(sample.component, sample.index);
            value = value - dt.e_scale() * (amplitude * sample.amperes_per_m2);
        }
        check(bitwise_equal(p1.fields(), mapped.fields()) && bitwise_equal(p1.fields(), masked.fields()),
              "vacuum map stepper equals the default stepper bitwise");
        check(bitwise_equal(p1.fields(), transcribed), "driven stepper equals the transcribed P1 step bitwise");
    }
    // Initial screening uses the discrete Gauss law with the edge permittivity.
    const auto map = modular_map(grid);
    rejects<std::invalid_argument>([&] { ReferenceStepper s{initial, dt, map}; }, "div E = 0 but div(eps E) != 0 rejected");
    FieldStorage displaced{grid};
    curl_fixture(displaced);
    const EdgeCoefficients table{map, dt};
    all(grid, [&](std::size_t id, Index index) {
        if (id < 3 && !constrained(grid, id, index)) displaced.at(components[id], index) /= table.at(components[id], index).eps_r;
    });
    ReferenceStepper accepted{displaced, dt, map};
    check(accepted.coefficients().table().size() == table.table().size(), "div(eps E) = 0 accepted");
    std::cout << "PASS S10: modular and sigma-independent maps on (2,3,4) and (5,4,3) against cell->edge enumeration "
              << "(worst relative " << worst_coefficient << "); vacuum Ca=1, Cb=dt/epsilon0 bitwise; rejections; vacuum "
              << "kernel bitwise; driven stepper bitwise equal to the transcribed P1 step\n";
}

void s11() {
    // Single edge: prescribed eps_e, sigma_e (uniform cells), curl from the resulting H, and J.
    const auto grid = grid_of({4, 4, 4}, {0.01, 0.015, 0.02});
    const auto dt = VacuumTimeStep::from_courant(grid);
    FieldStorage initial{grid};
    curl_fixture(initial);
    const Index target{1, 2, 2};
    const double j0 = 3.5, amplitude = -0.625, eps_r = 2.5;
    for (const double x : {0.0, 0.01, 0.045, 0.5}) {
        const double eps = eps_r * epsilon0;
        const double sigma = 2 * x * eps / dt.seconds();
        ReferenceStepper stepper{initial, dt, MaterialMap::uniform(grid, eps_r, sigma)};
        const ElectricCurrent current{grid, {{Ey, target, j0}}};
        stepper.step(current, amplitude);
        const double curl = curl_h(stepper.fields(), 1, target);
        const double ca = (1 - x) / (1 + x), cb = dt.seconds() / eps / (1 + x);
        const double e0 = initial.at(Ey, target);
        const double expected = ca * e0 + cb * (curl - amplitude * j0);
        const double scale = std::abs(ca * e0) + std::abs(cb * curl) + std::abs(cb * amplitude * j0);
        const double error = std::abs(stepper.fields().at(Ey, target) - expected) / scale;
        worst_single = std::max(worst_single, error);
        check(error <= 1e-13, "single-edge lossy update equals the independent formula");
        check(std::abs(stepper.coefficients().at(Ey, target).x - x) <= 1e-15 * std::max(x, 1.0), "prescribed x_e");
    }
    // Two full lossy steps on (5,4,3) against the exact-rational transcription.
    const auto golden_grid = grid_of({5, 4, 3});
    const auto golden_dt = VacuumTimeStep::from_seconds(golden_grid, std::ldexp(1.0, -30));
    FieldStorage start{golden_grid};
    for (const auto& sample : material_golden::samples) start.at(components[sample.component], sample.index) = sample.stages[0];
    ReferenceStepper stepper{start, golden_dt, modular_map(golden_grid)};
    for (std::size_t stage = 1; stage <= 2; ++stage) {
        stepper.step();
        std::array<double, 6> scale{};
        for (const auto& sample : material_golden::samples)
            scale[sample.component] = std::max(scale[sample.component], std::abs(sample.stages[stage]));
        for (const auto& sample : material_golden::samples) {
            const double error = std::abs(stepper.fields().at(components[sample.component], sample.index) -
                                          sample.stages[stage]) / scale[sample.component];
            worst_golden = std::max(worst_golden, error);
            check(error <= 1e-13, "two lossy steps equal the exact-rational transcription");
        }
    }
    std::cout << "PASS S11: single-edge update for x in {0,0.01,0.045,0.5} (worst " << worst_single
              << "); two lossy steps on (5,4,3) against 513 exact-rational samples (worst normalized " << worst_golden << ")\n";
}

void s12() {
    for (const Index cells : {Index{12, 14, 16}, Index{5, 4, 3}}) {
        const auto grid = grid_of(cells, {0.01, 0.015, 0.02});
        const auto vacuum = VacuumTimeStep::from_courant(grid);
        FieldStorage initial{grid};
        curl_fixture(initial);
        for (const auto& [eps_r, sigma] : {std::pair{1.0, 0.0}, std::pair{4.0, 0.1}, std::pair{2.25, 5.0}}) {
            ReferenceStepper stepper{initial, vacuum, MaterialMap::uniform(grid, eps_r, sigma)};
            check(stepper.time_step().seconds() == vacuum.seconds() && stepper.time_step().limit_seconds() ==
                  vacuum.limit_seconds() && stepper.time_step().e_scale() == vacuum.e_scale(), "material dt is the vacuum dt");
            for (int n = 0; n < 3; ++n) stepper.step();
            check(stepper.state_index() == 3 && stepper.times().e_s == 3 * vacuum.seconds(), "material stepping keeps native times");
        }
        check(VacuumTimeStep::from_courant(grid, 0.99).seconds() == vacuum.seconds(), "CFL selection is material independent");
    }
    // eps_r < 1 is rejected before allocation: on a grid whose arrays cannot be
    // allocated, validation must raise invalid_argument rather than an allocation error.
    const UniformGrid huge{CellCounts{1 << 20, 1 << 20, 1 << 10}, {1, 1, 1}};
    rejects<std::invalid_argument>([&] { (void)MaterialMap::uniform(huge, 0.5, 0); }, "eps_r<1 rejected before allocation");
    rejects<std::invalid_argument>([&] { (void)MaterialMap::uniform(huge, 1, -1); }, "sigma<0 rejected before allocation");
    // Coefficient overflow and nonfinite x rejected before stepping or copying fields.
    const auto grid = grid_of({5, 4, 3});
    const auto dt = VacuumTimeStep::from_courant(grid);
    FieldStorage zero{grid};
    rejects<std::overflow_error>([&] { ReferenceStepper s{zero, dt, MaterialMap::uniform(grid, 1e308, 0)}; }, "eps sum overflow gives Cb=0");
    rejects<std::overflow_error>([&] { ReferenceStepper s{zero, dt, MaterialMap::uniform(grid, 1, 1.7e308)}; }, "nonfinite x rejected");
    rejects<std::overflow_error>([&] { (void)EdgeCoefficients(MaterialMap::uniform(grid, 1e308, 0), dt); }, "coefficient overflow in the table");
    std::cout << "PASS S12: material dt equals the vacuum CFL value; eps_r<1/sigma<0 rejected before allocation; "
                 "coefficient overflow and nonfinite x rejected\n";
}

// Q_n = dV/2 (epsilon0 sum eps_r E^2 + mu0 sum H^2) - dV dt/2 sum H (C E); returns (Q, sum of absolute terms).
std::pair<double, double> invariant(const FieldStorage& f, const std::map<std::pair<std::size_t, Index>, Deposits>& deposits,
                                    double dt) {
    const auto& grid = f.grid();
    const auto [dx, dy, dz] = grid.spacing_m();
    const double volume = dx * dy * dz;
    long double total = 0, absolute = 0;
    all(grid, [&](std::size_t id, Index index) {
        const double value = f.at(components[id], index);
        if (value == 0) return;
        check(!constrained(grid, id, index), "constrained samples stay zero");
        long double term;
        if (id < 3) {
            const auto& d = deposits.at({id, index});
            const double eps_r = (d.eps[0] + d.eps[1] + d.eps[2] + d.eps[3]) / 4;
            term = static_cast<long double>(volume) / 2 * epsilon0 * eps_r * value * value;
        } else {
            term = static_cast<long double>(volume) / 2 * mu0 * value * value;
            const long double cross = -static_cast<long double>(volume) * dt / 2 * value * curl_e(f, id, index);
            total += cross; absolute += std::abs(cross);
        }
        total += term; absolute += std::abs(term);
    });
    return {static_cast<double>(total), static_cast<double>(absolute)};
}

void s13() {
    for (const Index cells : {Index{2, 3, 4}, Index{5, 4, 3}}) {
        const auto grid = grid_of(cells);
        const auto dt = VacuumTimeStep::from_courant(grid);
        const auto map = modular_map(grid);
        const EdgeCoefficients coefficients{map, dt};
        const auto deposits = edge_deposits(grid, map);
        const PecMask mask{grid};
        FieldStorage f{grid};
        fill_modular(f);
        FieldStorage before{grid};
        all(grid, [&](std::size_t id, Index index) { before.at(components[id], index) = f.at(components[id], index); });
        const auto [q_old, abs_old] = invariant(f, deposits, dt.seconds());
        detail::advance_h(f, dt, 0);
        detail::advance_e(f, dt, 0, mask, coefficients);
        const auto [q_new, abs_new] = invariant(f, deposits, dt.seconds());
        const auto [dx, dy, dz] = grid.spacing_m();
        long double dissipation = 0;
        for (std::size_t id = 0; id < 3; ++id)
            enumerate(grid.layout(components[id]).extents, [&](Index index) {
                if (constrained(grid, id, index)) return;
                const auto& d = deposits.at({id, index});
                const double sigma = (d.sigma[0] + d.sigma[1] + d.sigma[2] + d.sigma[3]) / 4;
                const double mean = (f.at(components[id], index) + before.at(components[id], index)) / 2;
                dissipation += static_cast<long double>(dx * dy * dz) * dt.seconds() * sigma * mean * mean;
            });
        check(dissipation >= 0, "dissipation is nonnegative");
        const double residual = std::abs(q_new - q_old + static_cast<double>(dissipation));
        const double scale = abs_old + abs_new + static_cast<double>(dissipation);
        worst_identity = std::max(worst_identity, residual / scale);
        check(residual <= 1e-12 * scale, "Q_(n+1) - Q_n + D_n = 0 on modular fields with the S10 map");
        check(static_cast<double>(dissipation) > 1e-6 * scale, "the S10 map dissipates a nontrivial amount");
    }
    std::cout << "PASS S13: one-step dissipation identity on (2,3,4) and (5,4,3); worst residual/sum of absolute terms "
              << worst_identity << '\n';
}
} // namespace

int main(int argc, char* argv[]) {
    try {
        if (argc != 3 || std::string_view{argv[1]} != "--check") throw std::invalid_argument("Usage: --check s10|s11|s12|s13");
        const std::string_view group{argv[2]};
        if (group == "s10") s10();
        else if (group == "s11") s11();
        else if (group == "s12") s12();
        else if (group == "s13") s13();
        else throw std::invalid_argument("Unknown check group.");
        std::cout << "PASS " << group << ": " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
