#include "antennasim/grid.hpp"
#include "antennasim/detail/checked_size.hpp"

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace {

using antennasim::AllocationLimits;
using antennasim::CellCounts;
using antennasim::FieldComponent;
using antennasim::UniformGrid;
using Shape = std::array<std::size_t, 3>;

static_assert(!std::is_constructible_v<CellCounts, double, int, int>);
static_assert(!std::is_constructible_v<CellCounts, int, double, int>);
static_assert(!std::is_constructible_v<CellCounts, int, int, double>);
static_assert(!std::is_constructible_v<CellCounts, bool, int, int>);
static_assert(!std::is_constructible_v<CellCounts, int, bool, int>);
static_assert(!std::is_constructible_v<CellCounts, int, int, bool>);
static_assert(std::is_constructible_v<CellCounts, int, unsigned, std::size_t>);

std::size_t checks = 0;
std::size_t failures = 0;

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

void small_grid_fixtures() {
    // Literal tables independently enumerated from FND-03/S01, not generated
    // with production layout functions or a copy of the production loop.
    struct Fixture {
        Shape cells;
        std::array<Shape, 6> extents;
        std::array<std::size_t, 6> elements;
        std::array<double, 3> lengths;
        std::size_t bytes;
    };
    const std::array<Fixture, 3> fixtures{{
        {{2, 2, 2}, {{{2, 3, 3}, {3, 2, 3}, {3, 3, 2},
                     {3, 2, 2}, {2, 3, 2}, {2, 2, 3}}},
         {18, 18, 18, 12, 12, 12}, {4, 6, 10}, 720},
        {{2, 3, 4}, {{{2, 4, 5}, {3, 3, 5}, {3, 4, 4},
                     {3, 3, 4}, {2, 4, 4}, {2, 3, 5}}},
         {40, 45, 48, 36, 32, 30}, {4, 9, 20}, 1848},
        {{5, 4, 3}, {{{5, 5, 4}, {6, 4, 4}, {6, 5, 3},
                     {6, 4, 3}, {5, 5, 3}, {5, 4, 4}}},
         {100, 96, 90, 72, 75, 80}, {10, 12, 15}, 4104}
    }};
    constexpr std::array components{FieldComponent::Ex, FieldComponent::Ey,
        FieldComponent::Ez, FieldComponent::Hx, FieldComponent::Hy, FieldComponent::Hz};
    for (const auto& fixture : fixtures) {
        const auto [nx, ny, nz] = fixture.cells;
        const UniformGrid grid{CellCounts{nx, ny, nz}, {2, 3, 5}};
        check(grid.cells().values() == fixture.cells, "preserved cell counts");
        check(grid.spacing_m() == std::array<double, 3>{2, 3, 5}, "SI spacings");
        check(grid.lengths_m() == fixture.lengths, "exact unequal-spacing lengths");
        check(grid.field_bytes() == fixture.bytes, "independent aggregate bytes");
        check(grid.field_elements() == fixture.bytes / 8, "independent aggregate elements");
        for (std::size_t i = 0; i < components.size(); ++i) {
            check(grid.layout(components[i]).extents == fixture.extents[i],
                  "independent component extents");
            check(grid.layout(components[i]).element_count == fixture.elements[i],
                  "independent component element count");
        }
    }
    const UniformGrid grid{CellCounts{2, 2U, std::size_t{2}}, {1, 1, 1}};
    rejects<std::invalid_argument>([&] { (void)grid.layout(static_cast<FieldComponent>(6)); },
                                   "invalid component after Hz");
    rejects<std::invalid_argument>([&] { (void)grid.layout(static_cast<FieldComponent>(255)); },
                                   "invalid component underlying maximum");
}

template <class Count>
void wider_count_input() {
    if constexpr (std::numeric_limits<Count>::digits >
                  std::numeric_limits<std::size_t>::digits) {
        rejects<std::length_error>([] {
            (void)CellCounts{std::numeric_limits<Count>::max(), 2, 2};
        }, "integral input wider than size_t");
    }
}

void count_and_spacing_inputs() {
    for (std::size_t axis = 0; axis < 3; ++axis) {
        const std::string context = "axis " + std::to_string(axis);
        for (const auto bad : {-1LL, 0LL, 1LL, std::numeric_limits<long long>::min()}) {
            std::array<long long, 3> counts{2, 3, 4};
            counts[axis] = bad;
            rejects<std::invalid_argument>([&] {
                (void)CellCounts{counts[0], counts[1], counts[2]};
            }, "reject signed count before conversion: " + context);
        }
        for (const auto bad : {std::size_t{0}, std::size_t{1}}) {
            Shape counts{2, 3, 4};
            counts[axis] = bad;
            rejects<std::invalid_argument>([&] {
                (void)CellCounts{counts[0], counts[1], counts[2]};
            }, "reject too-small unsigned count: " + context);
        }
        for (const double bad : {0.0, -0.0, -1.0,
                 std::numeric_limits<double>::quiet_NaN(),
                 std::numeric_limits<double>::infinity(),
                 -std::numeric_limits<double>::infinity()}) {
            std::array<double, 3> spacing{2, 3, 5};
            spacing[axis] = bad;
            rejects<std::invalid_argument>([&] {
                (void)UniformGrid{CellCounts{2, 3, 4}, spacing};
            }, "reject invalid spacing: " + context);
        }
    }
    wider_count_input<std::uintmax_t>();
}

void arithmetic_and_limits() {
    using antennasim::detail::checked_add;
    using antennasim::detail::checked_multiply;
    constexpr auto maximum = std::numeric_limits<std::size_t>::max();
    check(checked_add(maximum, 0) == maximum, "safe max+0");
    check(checked_add(maximum - 1, 1) == maximum, "exact addition boundary");
    check(checked_multiply(maximum, 1) == maximum, "safe max*1");
    check(checked_multiply(0, maximum) == 0 && checked_multiply(maximum, 0) == 0,
          "zero products in both orders");
    check(checked_multiply(maximum / 2, 2) == maximum - 1, "last safe even product");
    rejects<std::length_error>([&] { (void)checked_add(maximum, 1); }, "addition overflow");
    rejects<std::length_error>([&] { (void)checked_multiply(maximum / 2 + 1, 2); },
                               "multiplication overflow");
    for (std::size_t axis = 0; axis < 3; ++axis) {
        Shape counts{2, 2, 2};
        counts[axis] = maximum;
        rejects<std::length_error>([&] {
            (void)UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, {1, 1, 1}};
        }, "N+1 overflow on axis " + std::to_string(axis));
        counts[axis] = maximum / 3;
        rejects<std::length_error>([&] {
            (void)UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, {1, 1, 1}};
        }, "component extent product overflow on axis " + std::to_string(axis));

        // Independent expansion: for (x,2,2), all six arrays sum to 37*x+16.
        // Rotation does not change this total. Each component product fits.
        counts[axis] = maximum / 37 + 1;
        rejects<std::length_error>([&] {
            (void)UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, {1, 1, 1}};
        }, "aggregate element overflow on axis " + std::to_string(axis));
        counts[axis] = maximum / (37 * 8) + 1;
        rejects<std::length_error>([&] {
            (void)UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, {1, 1, 1}};
        }, "aggregate byte overflow on axis " + std::to_string(axis));
    }

    const UniformGrid exact{CellCounts{2, 3, 4}, {2, 3, 5}, {48, 1848}};
    check(exact.field_bytes() == 1848, "exact component/byte budget accepted");
    check(exact.allocation_limits().max_component_elements == 48 &&
          exact.allocation_limits().max_field_bytes == 1848, "effective lowered limits");
    for (const auto limits : {AllocationLimits{47, maximum}, AllocationLimits{maximum, 1847},
                              AllocationLimits{0, maximum}, AllocationLimits{maximum, 0}}) {
        rejects<std::length_error>([&] {
            (void)UniformGrid{CellCounts{2, 3, 4}, {2, 3, 5}, limits};
        }, "insufficient component or aggregate cap");
    }
    const UniformGrid native_limit{CellCounts{2, 2, 2}, {1, 1, 1}, {maximum, maximum}};
    check(native_limit.allocation_limits().max_component_elements ==
          std::vector<double>{}.max_size(), "cannot raise real container limit");
}

void representability() {
    constexpr double minimum = std::numeric_limits<double>::denorm_min();
    constexpr double maximum = std::numeric_limits<double>::max();
    for (std::size_t axis = 0; axis < 3; ++axis) {
        std::array<double, 3> spacing{1, 1, 1};
        for (const double bad : {minimum, maximum}) {
            spacing[axis] = bad;
            rejects<std::overflow_error>([&] {
                (void)UniformGrid{CellCounts{2, 2, 2}, spacing};
            }, "underflowed half coordinate or overflowing length on axis " + std::to_string(axis));
        }
        // Geometry alone admits these extremes; future dt validation can reject them.
        spacing[axis] = 2 * minimum;
        const UniformGrid subnormal{CellCounts{2, 2, 2}, spacing};
        check(subnormal.lengths_m()[axis] == 4 * minimum, "resolvable subnormal geometry");
        spacing[axis] = maximum / 2;
        const UniformGrid largest{CellCounts{2, 2, 2}, spacing};
        check(largest.lengths_m()[axis] == maximum, "largest finite endpoint accepted");

        if constexpr (std::numeric_limits<std::size_t>::digits > 52) {
            // These construct metadata only; never request enormous field arrays.
            constexpr auto exact_index = std::uint64_t{1} << 52;
            std::array<std::uint64_t, 3> counts{2, 2, 2};
            counts[axis] = exact_index;
            spacing = {1, 1, 1};
            const UniformGrid exact{CellCounts{counts[0], counts[1], counts[2]}, spacing};
            check(exact.lengths_m()[axis] == 0x1p52, "last exact half-index extent");
            counts[axis] = exact_index + 1;
            rejects<std::overflow_error>([&] {
                (void)UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, spacing};
            }, "cell count exceeds binary64 half-index range");
            counts[axis] = exact_index;
            spacing[axis] = 1.5;
            rejects<std::overflow_error>([&] {
                (void)UniformGrid{CellCounts{counts[0], counts[1], counts[2]}, spacing};
            }, "scaled half locations cannot be resolved throughout domain");
        }
    }
}

} // namespace

int main() {
    try {
        small_grid_fixtures();
        count_and_spacing_inputs();
        arithmetic_and_limits();
        representability();
    } catch (const std::exception& error) {
        std::cerr << "Unexpected exception: " << error.what() << '\n';
        return 1;
    }
    std::cout << checks << " grid checks, " << failures << " failures.\n"
              << "LIMIT: metadata/structural checks only; no field storage or solver.\n";
    return failures == 0 ? 0 : 1;
}
