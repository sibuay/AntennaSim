// S09 structural checks of the E-edge PEC mask (MAT-01 specification, MAT-02
// contract). Independent endpoint enumeration; no production rule is reused
// as its own oracle.
#include "antennasim/vacuum.hpp"
#include "antennasim/detail/vacuum_kernel.hpp"
#include "closed.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <string_view>

namespace {
using namespace antennasim;
using enum FieldComponent;
using Index = std::array<std::size_t, 3>;
constexpr std::array components{Ex, Ey, Ez, Hx, Hy, Hz};
std::size_t checks = 0;

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

// Independent formulation: an E_a edge joins the nodes index and index+e_a. A
// box marks it when both nodes lie in the closed node box; a shell additionally
// requires a shared coordinate on one of the box's face planes.
bool in_closed_box(Index node, const CellBox& box) {
    for (std::size_t t = 0; t < 3; ++t)
        if (node[t] < box.low[t] || node[t] > box.high[t]) return false;
    return true;
}
bool marks_by_endpoints(const PecPrimitive& primitive, std::size_t a, Index index) {
    Index first = index, second = index;
    ++second[a];
    if (!in_closed_box(first, primitive.cells) || !in_closed_box(second, primitive.cells)) return false;
    if (primitive.shape == PecShape::Box) return true;
    for (std::size_t t = 0; t < 3; ++t)
        if (first[t] == second[t] && (first[t] == primitive.cells.low[t] || first[t] == primitive.cells.high[t])) return true;
    return false;
}
// Tangential outer-face E_a samples: all samples minus those with every
// transverse index strictly inside (1..N-1).
std::size_t wall_count(const UniformGrid& grid, std::size_t a) {
    const auto n = grid.cells().values();
    std::size_t interior = n[a];
    for (std::size_t t = 0; t < 3; ++t) if (t != a) interior *= n[t] - 1;
    return grid.layout(components[a]).element_count - interior;
}

void mask_against_enumeration(const UniformGrid& grid, const std::vector<PecPrimitive>& primitives,
                              std::array<std::size_t, 3>* interior_counts = nullptr) {
    const PecMask mask{grid, primitives};
    std::array<std::size_t, 3> counted{}, closure{};
    all(grid, [&](std::size_t id, Index index) {
        if (id >= 3) {
            check(!mask.masked(components[id], index), "H samples are never masked");
            return;
        }
        bool expected = grid.is_tangential_e_wall(components[id], index);
        for (const auto& primitive : primitives) expected = expected || marks_by_endpoints(primitive, id, index);
        check(mask.masked(components[id], index) == expected, "mask equals the independent endpoint enumeration");
        check((mask.values(components[id])[grid.offset(components[id], index)] != 0) == expected, "contiguous mask view");
        counted[id] += expected;
        closure[id] += grid.is_tangential_e_wall(components[id], index);
    });
    check(mask.masked_counts() == counted && mask.closure_counts() == closure, "reported masked/closure counts");
    for (std::size_t a = 0; a < 3; ++a) check(closure[a] == wall_count(grid, a), "closure count formula");
    check(mask.primitives().size() == primitives.size(), "primitives retained");
    if (interior_counts != nullptr)
        for (std::size_t a = 0; a < 3; ++a) (*interior_counts)[a] = counted[a] - closure[a];
}

void enumeration() {
    for (const Index counts : {Index{5, 4, 3}, Index{2, 3, 4}}) {
        const UniformGrid grid{CellCounts{counts[0], counts[1], counts[2]}, {2, 3, 5}};
        const PecMask closure{grid};
        std::size_t bytes = 0;
        all(grid, [&](std::size_t id, Index index) {
            const auto f = components[id];
            if (id < 3) {
                check(closure.masked(f, index) == grid.is_tangential_e_wall(f, index), "default mask is the outer closure");
                check(!closure.enclosed(f, index), "E samples are never enclosed");
            } else {
                check(!closure.masked(f, index), "default mask leaves H free");
                check(closure.enclosed(f, index) == grid.is_normal_h_wall(f, index), "enclosed H equals the normal H walls");
            }
        });
        for (std::size_t id = 0; id < 3; ++id) bytes += grid.layout(components[id]).element_count;
        check(closure.mask_bytes() == bytes && closure.primitives().empty() &&
              closure.masked_counts() == closure.closure_counts(), "closure-only counts and byte cost");
        rejects<std::invalid_argument>([&] { (void)closure.values(Hx); }, "H mask view rejected");
        rejects<std::out_of_range>([&] { (void)closure.masked(Ex, {counts[0], 0, 0}); }, "mask bounds");
        const bool small = counts[0] == 2;
        const std::vector<std::vector<PecPrimitive>> sets = small ? std::vector<std::vector<PecPrimitive>>{
            {{PecShape::Box, {{1, 1, 1}, {2, 3, 2}}}},
            {{PecShape::Shell, {{1, 1, 1}, {2, 3, 2}}}},
            {{PecShape::Shell, {{0, 0, 1}, {2, 2, 3}}}},
            {{PecShape::Box, {{0, 1, 1}, {2, 3, 3}}}, {PecShape::Shell, {{1, 0, 2}, {2, 2, 4}}}}} :
            std::vector<std::vector<PecPrimitive>>{
            {{PecShape::Box, {{1, 1, 1}, {3, 3, 2}}}},
            {{PecShape::Shell, {{1, 1, 1}, {3, 3, 2}}}},
            {{PecShape::Box, {{0, 1, 0}, {2, 3, 2}}}},
            {{PecShape::Box, {{1, 1, 1}, {3, 3, 2}}}, {PecShape::Shell, {{2, 0, 1}, {5, 2, 3}}}}};
        for (const auto& set : sets) mask_against_enumeration(grid, set);
    }
    // V04-C shell and the solid box of the same ranges on the (18,22,26) grid.
    const UniformGrid grid{CellCounts{18, 22, 26}, {0.01, 0.015, 0.02}};
    std::array<std::size_t, 3> shell_counts{}, box_counts{};
    mask_against_enumeration(grid, {{PecShape::Shell, {{3, 3, 3}, {15, 19, 23}}}}, &shell_counts);
    mask_against_enumeration(grid, {{PecShape::Box, {{3, 3, 3}, {15, 19, 23}}}}, &box_counts);
    check(shell_counts == std::array<std::size_t, 3>{864, 1024, 1120}, "V04-C shell marks 864/1024/1120 edges");
    check(box_counts[0] + box_counts[1] + box_counts[2] == 13072, "V04-C solid box marks 13072 edges");
    std::cout << "V04-C shell edges " << shell_counts[0] + shell_counts[1] + shell_counts[2] << '\n';
}

void stepping() {
    const UniformGrid grid{CellCounts{6, 5, 4}, {2, 3, 5}};
    const auto dt = VacuumTimeStep::from_courant(grid);
    const CellBox box{{1, 1, 1}, {4, 4, 3}};
    const FieldStorage zero{grid};
    const Index outside{5, 4, 2}, inside{2, 2, 1};   // Ez edges
    for (const auto shape : {PecShape::Shell, PecShape::Box}) {
        const PecMask mask{grid, {{shape, box}}};
        std::vector<CurrentSample> samples{{Ez, outside, 1.0}};
        if (shape == PecShape::Shell) samples.push_back({Ez, inside, -1.0});
        check(!mask.masked(Ez, outside) && mask.masked(Ez, inside) == (shape == PecShape::Box), "chosen source edges");
        const ElectricCurrent current{grid, samples};
        ReferenceStepper solver{zero, dt, mask};
        for (int n = 0; n < 2; ++n) solver.step(current);
        std::size_t masked_zero = 0, enclosed_zero = 0, e_inside = 0, e_outside = 0, h_moving = 0;
        all(grid, [&](std::size_t id, Index index) {
            const auto f = components[id];
            const double value = solver.fields().at(f, index);
            if (mask.masked(f, index)) { check(value == 0, "masked E stays exactly zero"); ++masked_zero; return; }
            if (mask.enclosed(f, index)) { check(value == 0, "enclosed H stays exactly zero"); ++enclosed_zero; return; }
            if (value == 0) return;
            if (id >= 3) { ++h_moving; return; }
            bool interior = true;
            for (std::size_t t = 0; t < 3; ++t) {
                const double coordinate = static_cast<double>(index[t]) + (t == id ? 0.5 : 0.0);
                interior = interior && coordinate > static_cast<double>(box.low[t]) && coordinate < static_cast<double>(box.high[t]);
            }
            if (interior) ++e_inside; else ++e_outside;
        });
        check(masked_zero > 0 && enclosed_zero > 0 && e_outside > 0 && h_moving > 0, "unmasked samples evolve");
        check((e_inside > 0) == (shape == PecShape::Shell), "shell interior evolves; box interior is silent");
        check(solver.mask().masked_counts() == mask.masked_counts(), "stepper reports its mask");
    }
    // The closure-only mask performs the vacuum arithmetic bitwise.
    ReferenceStepper vacuum{zero, dt}, explicit_closure{zero, dt, PecMask{grid}};
    const ElectricCurrent current{grid, {{Ex, {2, 2, 2}, 0.7}, {Ey, {3, 1, 2}, -0.3}}};
    for (int n = 0; n < 3; ++n) { vacuum.step(current); explicit_closure.step(current); }
    all(grid, [&](std::size_t id, Index index) {
        check(vacuum.fields().at(components[id], index) == explicit_closure.fields().at(components[id], index),
              "default and explicit closure steppers agree bitwise");
    });
    FieldStorage plain{grid}, masked{grid};
    all(grid, [&](std::size_t id, Index index) {
        const double value = grid.is_tangential_e_wall(components[id], index) ? 0.0 :
            (static_cast<double>((17 * index[0] + 31 * index[1] + 43 * index[2] + 13 * id) % 101) - 50) / 50;
        plain.at(components[id], index) = value;
        masked.at(components[id], index) = value;
    });
    detail::advance_e(plain, dt, 0);
    detail::advance_e(masked, dt, 0, PecMask{grid});
    all(grid, [&](std::size_t id, Index index) {
        check(plain.at(components[id], index) == masked.at(components[id], index), "kernel with closure mask is bitwise identical");
    });
    const UniformGrid other{CellCounts{6, 5, 4}, {2, 3, 4}};
    rejects<std::invalid_argument>([&] { detail::advance_e(plain, dt, 0, PecMask{other}); }, "kernel mask mismatch");
}

void rejections() {
    const UniformGrid grid{CellCounts{5, 4, 3}, {2, 3, 5}};
    const auto dt = VacuumTimeStep::from_courant(grid);
    for (const CellBox bad : {CellBox{{3, 1, 1}, {1, 3, 2}}, CellBox{{1, 1, 1}, {6, 3, 2}}, CellBox{{1, 1, 1}, {3, 1, 2}},
                             CellBox{{1, 1, 3}, {3, 3, 3}}, CellBox{{0, 0, 0}, {5, 5, 3}}})
        rejects<std::invalid_argument>([&] { PecMask invalid{grid, {{PecShape::Box, bad}}}; }, "inverted/out-of-range primitive");
    rejects<std::invalid_argument>([&] { PecMask invalid{grid, {{static_cast<PecShape>(7), CellBox{{1, 1, 1}, {3, 3, 2}}}}}; }, "unknown shape");
    const FieldStorage zero{grid};
    const UniformGrid different{CellCounts{6, 4, 3}, {2, 3, 5}};
    rejects<std::invalid_argument>([&] { ReferenceStepper mismatch{zero, dt, PecMask{different}}; }, "mask/grid mismatch");
    const CellBox box{{1, 1, 1}, {3, 3, 2}};
    for (const auto shape : {PecShape::Shell, PecShape::Box}) {
        const PecMask mask{grid, {{shape, box}}};
        std::size_t tested = 0;
        all(grid, [&](std::size_t id, Index index) {
            const auto f = components[id];
            if (!(mask.masked(f, index) || mask.enclosed(f, index)) || grid.is_tangential_e_wall(f, index) ||
                grid.is_normal_h_wall(f, index)) return;
            FieldStorage fields{grid};
            fields.at(f, index) = 1;
            rejects<std::invalid_argument>([&] { ReferenceStepper invalid{fields, dt, mask}; }, "nonzero initial masked/enclosed sample");
            check(fields.at(f, index) == 1, "invalid initial data not silently clamped");
            ++tested;
        });
        check(tested > 0, "interior masked and enclosed samples exist");
        ReferenceStepper solver{zero, dt, mask};
        const ElectricCurrent on_face{grid, {{Ez, {1, 1, 1}, 1.0}}};
        check(mask.masked(Ez, {1, 1, 1}), "chosen edge lies on the primitive face");
        rejects<std::invalid_argument>([&] { solver.step(on_face); }, "source on a masked edge");
        check(solver.failed() && solver.state_index() == 0, "rejected source is terminal without advancing");
        // Divergence screening ignores nodes with a masked neighbour (implied surface charge)
        // but still rejects charged interior nodes.
        FieldStorage charged{grid};
        charged.at(Ex, {3, 2, 1}) = 1;   // node (3,2,1) and (4,2,1) are away from the primitive
        rejects<std::invalid_argument>([&] { ReferenceStepper invalid{charged, dt, mask}; }, "initial rho=0 screening retained");
    }
    // The V04-C fixtures: the shell accepts the mode and the pulse, the solid box rejects both.
    for (std::size_t a = 0; a < 3; ++a) {
        const auto shell = benchmark::closed::pec_mode_case(a, PecShape::Shell);
        FieldStorage fields{shell.grid};
        const auto result = benchmark::closed::initialize(shell, fields);
        ReferenceStepper solver{fields, shell.dt, benchmark::closed::mask(shell)};
        const auto counts = solver.mask().masked_counts();
        const auto closure = solver.mask().closure_counts();
        check(counts[0] - closure[0] + counts[1] - closure[1] + counts[2] - closure[2] == 3008, "V04-C shell in the run mask");
        check(result.eigen <= 1e-11 && result.divergence <= 1e-11, "V04-C mode fixture identities");
        const auto solid = benchmark::closed::pec_mode_case(a, PecShape::Box);
        FieldStorage boxed{solid.grid};
        rejects<std::runtime_error>([&] { (void)benchmark::closed::initialize(solid, boxed); }, "V04-C mode inside a solid box rejected");
    }
    auto pec = benchmark::closed::cases("pec");
    check(pec.size() == 5, "five V04-C cases");
    for (auto& config : pec) {
        if (config.kind != benchmark::closed::Kind::Source) continue;
        config.primitives.front().shape = PecShape::Box;
        FieldStorage fields{config.grid};
        if (config.name == "pec-c2-inside")
            rejects<std::invalid_argument>([&] { (void)benchmark::closed::initialize(config, fields); }, "C2 source inside a solid box rejected");
        else check(benchmark::closed::initialize(config, fields).divergence == 0, "C3 exterior source accepted with a solid box");
    }
}

void fixtures() {
    const auto cavity = benchmark::closed::cases("cavity");
    const auto spectrum = benchmark::closed::cases("cavity-spectrum");
    check(cavity.size() == 30 && spectrum.size() == 1, "fixed closed suite enumeration");
    double worst_eigen = 0, worst_divergence = 0;
    for (const auto& config : cavity) {
        if (config.s != 1) continue;   // s=1 fixtures execute here; larger ones in the manual suite
        FieldStorage fields{config.grid};
        const auto result = benchmark::closed::initialize(config, fields);
        worst_eigen = std::max(worst_eigen, result.eigen);
        worst_divergence = std::max(worst_divergence, result.divergence);
        ReferenceStepper solver{fields, config.dt, benchmark::closed::mask(config)};
        check(solver.state_index() == 0, "production screening accepts the exact mode");
        check(benchmark::closed::probes(config).size() == 2 * config.cavity[(config.a + 1) % 3] + 1 + config.cavity[(config.a + 2) % 3],
              "three native lines");
    }
    const auto samples = benchmark::closed::pulse(spectrum.front());
    check(samples.size() == 53 && samples[26] == 0, "53 half-time pulse samples centred on zero");
    for (std::size_t m = 0; m < 26; ++m)
        check(samples[m] == -samples[52 - m] && samples[m] > 0, "mirrored pulse samples cancel bitwise (early samples positive)");
    rejects<std::invalid_argument>([] { (void)benchmark::closed::cases("unknown"); }, "unknown closed suite");
    std::cout << "closed s=1 fixture identities: eigen=" << worst_eigen << " divergence=" << worst_divergence << '\n';
}
} // namespace

int main() {
    try { enumeration(); stepping(); rejections(); fixtures(); std::cout << "PASS " << checks << " PEC mask checks\n"; return 0; }
    catch (const std::exception& error) { std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n'; return 1; }
}
