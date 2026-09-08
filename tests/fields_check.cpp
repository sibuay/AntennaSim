#include "antennasim/fields.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <type_traits>
#include <utility>

namespace {
using antennasim::CellCounts;
using antennasim::FieldComponent;
using antennasim::FieldStorage;
using antennasim::UniformGrid;
using Index = std::array<std::size_t, 3>;
using Position = std::array<double, 3>;
using enum FieldComponent;

static_assert(std::is_same_v<decltype(std::declval<FieldStorage&>().at(Ex, {})), double&>);
static_assert(std::is_same_v<decltype(std::declval<const FieldStorage&>().at(Ex, {})),
                             const double&>);
static_assert(std::is_same_v<decltype(std::declval<FieldStorage&>().values(Ex)),
                             std::span<const double>>);
static_assert(!std::is_copy_constructible_v<FieldStorage>);
static_assert(!std::is_move_constructible_v<FieldStorage>);
static_assert(!std::is_copy_assignable_v<FieldStorage>);
static_assert(!std::is_move_assignable_v<FieldStorage>);

std::size_t checks = 0;
std::size_t failures = 0;
std::size_t stencil_reads = 0;
constexpr std::array components{Ex, Ey, Ez, Hx, Hy, Hz};

void check(bool condition, std::string_view context) {
    ++checks;
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << context << '\n';
    }
}

template <class Error, class Function>
void rejects(Function function, std::string_view context) {
    try {
        function();
        check(false, context);
    } catch (const Error&) {
        check(true, context);
    } catch (const std::exception& error) {
        check(false, context);
        std::cerr << "  Wrong error category: " << error.what() << '\n';
    }
}

struct Fixture {
    Index cells;
    std::array<Index, 6> shapes;
    std::array<std::size_t, 6> sizes;
    std::array<std::size_t, 3> e_walls;
    std::array<std::size_t, 3> h_walls;
    std::size_t reads;
};

// Literal, independently enumerated S01 shapes and wall-union totals.
constexpr std::array<Fixture, 3> fixtures{{
    {{2, 2, 2}, {{{2, 3, 3}, {3, 2, 3}, {3, 3, 2},
                  {3, 2, 2}, {2, 3, 2}, {2, 2, 3}}},
     {18, 18, 18, 12, 12, 12}, {16, 16, 16}, {8, 8, 8}, 168},
    {{2, 3, 4}, {{{2, 4, 5}, {3, 3, 5}, {3, 4, 4},
                  {3, 3, 4}, {2, 4, 4}, {2, 3, 5}}},
     {40, 45, 48, 36, 32, 30}, {28, 36, 40}, {24, 16, 12}, 508},
    {{5, 4, 3}, {{{5, 5, 4}, {6, 4, 4}, {6, 5, 3},
                  {6, 4, 3}, {5, 5, 3}, {5, 4, 4}}},
     {100, 96, 90, 72, 75, 80}, {70, 64, 54}, {24, 30, 40}, 1300}
}};

// Actual coordinate sequences, rather than the implementation's scaling formula.
constexpr std::array<Position, 6> nodes{{
    {0, 0, 0}, {2, 3, 5}, {4, 6, 10}, {6, 9, 15}, {8, 12, 20}, {10, 15, 25}}};
constexpr std::array<Position, 5> halves{{
    {1, 1.5, 2.5}, {3, 4.5, 7.5}, {5, 7.5, 12.5},
    {7, 10.5, 17.5}, {9, 13.5, 22.5}}};
constexpr std::array<std::array<bool, 3>, 6> half_axes{{
    {true, false, false}, {false, true, false}, {false, false, true},
    {false, true, true}, {true, false, true}, {true, true, false}}};

Position expected_position(std::size_t component, Index index) {
    Position result{};
    for (std::size_t a = 0; a < 3; ++a) {
        result[a] = half_axes[component][a] ? halves[index[a]][a] : nodes[index[a]][a];
    }
    return result;
}

template <class Function>
void enumerate(Index shape, Function function) {
    std::size_t ordinal = 0;
    for (std::size_t k = 0; k < shape[2]; ++k) {
        for (std::size_t j = 0; j < shape[1]; ++j) {
            for (std::size_t i = 0; i < shape[0]; ++i) {
                function(Index{i, j, k}, ordinal++);
            }
        }
    }
}

double marker(std::size_t component, std::size_t ordinal) {
    return static_cast<double>(1000 * (component + 1) + ordinal);
}

void access_failures(FieldStorage& fields, const Fixture& fixture) {
    const auto& grid = fields.grid();
    const auto& constant = std::as_const(fields);
    for (std::size_t id = 0; id < 6; ++id) {
        const auto component = components[id];
        for (std::size_t axis = 0; axis < 3; ++axis) {
            for (auto bad : {fixture.shapes[id][axis], std::numeric_limits<std::size_t>::max()}) {
                Index index{};
                index[axis] = bad;
                rejects<std::out_of_range>([&] { (void)grid.offset(component, index); }, "offset bounds");
                rejects<std::out_of_range>([&] { (void)grid.position_m(component, index); }, "position bounds");
                rejects<std::out_of_range>([&] { (void)grid.is_tangential_e_wall(component, index); }, "E wall bounds");
                rejects<std::out_of_range>([&] { (void)grid.is_normal_h_wall(component, index); }, "H wall bounds");
                rejects<std::out_of_range>([&] { fields.at(component, index) = -1; }, "mutable bounds");
                rejects<std::out_of_range>([&] { (void)constant.at(component, index); }, "const bounds");
            }
        }
    }
    for (const auto bad : {static_cast<FieldComponent>(6), static_cast<FieldComponent>(255)}) {
        rejects<std::invalid_argument>([&] { (void)grid.offset(bad, {}); }, "offset selector");
        rejects<std::invalid_argument>([&] { (void)grid.position_m(bad, {}); }, "position selector");
        rejects<std::invalid_argument>([&] { (void)grid.is_tangential_e_wall(bad, {}); }, "E wall selector");
        rejects<std::invalid_argument>([&] { (void)grid.is_normal_h_wall(bad, {}); }, "H wall selector");
        rejects<std::invalid_argument>([&] { fields.at(bad, {}) = -1; }, "mutable selector");
        rejects<std::invalid_argument>([&] { (void)constant.at(bad, {}); }, "const selector");
        rejects<std::invalid_argument>([&] { (void)fields.values(bad); }, "view selector");
    }
}

// Two derivative pairs for each target, transcribed from FND-03. This is an
// access harness only: it deliberately does not implement field increments.
struct Read { FieldComponent source; std::array<int, 3> shift; };
constexpr std::array<std::array<Read, 4>, 6> reads{{
    {{{Hz, {0, 0, 0}}, {Hz, {0, -1, 0}}, {Hy, {0, 0, 0}}, {Hy, {0, 0, -1}}}},
    {{{Hx, {0, 0, 0}}, {Hx, {0, 0, -1}}, {Hz, {0, 0, 0}}, {Hz, {-1, 0, 0}}}},
    {{{Hy, {0, 0, 0}}, {Hy, {-1, 0, 0}}, {Hx, {0, 0, 0}}, {Hx, {0, -1, 0}}}},
    {{{Ey, {0, 0, 1}}, {Ey, {0, 0, 0}}, {Ez, {0, 1, 0}}, {Ez, {0, 0, 0}}}},
    {{{Ez, {1, 0, 0}}, {Ez, {0, 0, 0}}, {Ex, {0, 0, 1}}, {Ex, {0, 0, 0}}}},
    {{{Ex, {0, 1, 0}}, {Ex, {0, 0, 0}}, {Ey, {1, 0, 0}}, {Ey, {0, 0, 0}}}}
}};
constexpr std::array<std::array<std::size_t, 2>, 6> derivative_axes{{
    {1, 2}, {2, 0}, {0, 1}, {2, 1}, {0, 2}, {1, 0}}};

void stencil_access(const FieldStorage& fields, const Fixture& fixture) {
    const auto& grid = fields.grid();
    const auto previous_reads = stencil_reads;
    const auto [nx, ny, nz] = fixture.cells;
    const std::array<Index, 6> begin{{{0, 1, 1}, {1, 0, 1}, {1, 1, 0},
                                    {0, 0, 0}, {0, 0, 0}, {0, 0, 0}}};
    const std::array<Index, 6> end{{{nx, ny, nz}, {nx, ny, nz}, {nx, ny, nz},
                                  {nx + 1, ny, nz}, {nx, ny + 1, nz}, {nx, ny, nz + 1}}};
    for (std::size_t id = 0; id < 6; ++id) {
        enumerate(fixture.shapes[id], [&](Index index, std::size_t) {
            bool included = true;
            for (std::size_t a = 0; a < 3; ++a) {
                included = included && index[a] >= begin[id][a] && index[a] < end[id][a];
            }
            check(included == !grid.is_tangential_e_wall(components[id], index), "range omits exactly E walls");
            if (!included) { return; }
            std::array<Position, 4> positions{};
            for (std::size_t r = 0; r < 4; ++r) {
                Index neighbour{};
                for (std::size_t a = 0; a < 3; ++a) {
                    const int shifted = static_cast<int>(index[a]) + reads[id][r].shift[a];
                    check(shifted >= 0, "no negative stencil coordinate before unsigned conversion");
                    if (shifted < 0) { return; }
                    neighbour[a] = static_cast<std::size_t>(shifted);
                }
                const auto source = reads[id][r].source;
                const auto value = fields.at(source, neighbour);
                check(value >= 1000 && value < 7000, "stencil reads initialized component storage");
                positions[r] = grid.position_m(source, neighbour);
                ++stencil_reads;
            }
            const auto target = expected_position(id, index);
            for (std::size_t pair = 0; pair < 2; ++pair) {
                for (std::size_t a = 0; a < 3; ++a) {
                    const auto high = positions[2 * pair][a];
                    const auto low = positions[2 * pair + 1][a];
                    check((high + low) / 2 == target[a], "exact derivative midpoint at native target");
                    const auto separation = a == derivative_axes[id][pair] ? nodes[1][a] : 0.0;
                    check(high - low == separation, "exact derivative separation and axis");
                }
            }
        });
    }
    check(stencil_reads - previous_reads == fixture.reads, "independent stencil-read total");
}

void storage_fixture(const Fixture& fixture) {
    const auto [nx, ny, nz] = fixture.cells;
    FieldStorage fields{UniformGrid{CellCounts{nx, ny, nz}, {2, 3, 5}}};
    const auto& grid = fields.grid();
    const auto& constant = std::as_const(fields);
    for (std::size_t id = 0; id < 6; ++id) {
        const auto component = components[id];
        const auto view = fields.values(component);
        check(grid.layout(component).extents == fixture.shapes[id], "literal component extents");
        check(view.size() == fixture.sizes[id], "literal allocated size");
        std::size_t e_count = 0;
        std::size_t h_count = 0;
        enumerate(fixture.shapes[id], [&](Index index, std::size_t ordinal) {
            check(fields.at(component, index) == 0 && !std::signbit(fields.at(component, index)), "initial positive zero");
            check(grid.offset(component, index) == ordinal, "unique contiguous offset by enumeration");
            check(&fields.at(component, index) == view.data() + ordinal, "x-contiguous address");
            check(&constant.at(component, index) == view.data() + ordinal, "const address matches");
            const auto position = expected_position(id, index);
            check(grid.position_m(component, index) == position, "exact literal native coordinates");
            bool e_wall = false;
            bool h_wall = false;
            for (std::size_t a = 0; a < 3; ++a) {
                const bool on_face = position[a] == 0 || position[a] == nodes[fixture.cells[a]][a];
                e_wall = e_wall || (id < 3 && a != id && on_face);
                h_wall = h_wall || (id >= 3 && a == id - 3 && on_face);
            }
            check(grid.is_tangential_e_wall(component, index) == e_wall, "E union versus physical faces");
            check(grid.is_normal_h_wall(component, index) == h_wall, "normal H versus physical faces");
            e_count += e_wall ? 1U : 0U;
            h_count += h_wall ? 1U : 0U;
            fields.at(component, index) = marker(id, ordinal);
        });
        check(e_count == (id < 3 ? fixture.e_walls[id] : 0), "literal E wall union total");
        check(h_count == (id >= 3 ? fixture.h_walls[id - 3] : 0), "literal normal H wall total");
    }
    access_failures(fields, fixture);
    stencil_access(constant, fixture);
    // Check after all six arrays have been filled and all read/failure paths run.
    for (std::size_t id = 0; id < 6; ++id) {
        enumerate(fixture.shapes[id], [&](Index index, std::size_t ordinal) {
            (void)grid.is_tangential_e_wall(components[id], index);
            (void)grid.is_normal_h_wall(components[id], index);
            check(constant.at(components[id], index) == marker(id, ordinal), "markers preserved with no aliasing or zeroing");
            check(constant.values(components[id])[ordinal] == marker(id, ordinal), "view readback by ordinal");
        });
    }
    FieldStorage separate{grid};
    separate.at(Ex, {}) = -7;
    check(fields.at(Ex, {}) == 1000, "separate owners do not alias");
    check(separate.at(Ey, {}) == 0, "separate owner starts from zero");
}

void limits_and_coordinates() {
    FieldStorage exact{UniformGrid{CellCounts{2, 3, 4}, {2, 3, 5}, {48, 1848}}};
    std::size_t size = 0;
    for (auto component : components) { size += exact.values(component).size(); }
    check(size * sizeof(double) == 1848, "actual field payload at exact allocation cap");
    for (std::size_t axis = 0; axis < 3; ++axis) {
        Position spacing{1, 1, 1};
        for (const double d : {2 * std::numeric_limits<double>::denorm_min(),
                               std::numeric_limits<double>::max() / 2}) {
            spacing[axis] = d;
            const UniformGrid grid{CellCounts{2, 2, 2}, spacing};
            for (std::size_t id = 0; id < 6; ++id) {
                const auto component = components[id];
                enumerate(grid.layout(component).extents, [&](Index index, std::size_t) {
                    const auto position = grid.position_m(component, index);
                    check(std::isfinite(position[axis]) && position[axis] >= 0 &&
                          position[axis] <= grid.lengths_m()[axis], "extreme coordinate finite and within domain");
                    if (index[axis] > 0) {
                        auto previous = index;
                        --previous[axis];
                        check(position[axis] > grid.position_m(component, previous)[axis], "extreme coordinates strictly ordered");
                    }
                });
                if (half_axes[id][axis]) {
                    check(grid.position_m(component, {})[axis] == d / 2, "extreme first half coordinate");
                } else {
                    Index endpoint{};
                    endpoint[axis] = 2;
                    check(grid.position_m(component, endpoint)[axis] == grid.lengths_m()[axis], "extreme node endpoint");
                }
            }
        }
    }
}
} // namespace

int main() {
    try {
        for (const auto& fixture : fixtures) { storage_fixture(fixture); }
        limits_and_coordinates();
    } catch (const std::exception& error) {
        std::cerr << "Unexpected exception: " << error.what() << '\n';
        return 1;
    }
    std::cout << checks << " field-storage checks, " << failures << " failures; "
              << stencil_reads << " stencil reads.\n"
              << "LIMIT: storage/access geometry only; no field evolution or validated physics.\n";
    return failures == 0 ? 0 : 1;
}
