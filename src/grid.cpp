#include "antennasim/grid.hpp"
#include "antennasim/detail/checked_size.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace antennasim {
namespace {

static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559 &&
              std::numeric_limits<double>::digits == 53 &&
              std::numeric_limits<double>::max_exponent == 1024);

double domain_length(std::size_t count, double spacing, std::size_t axis) {
    const std::string context = "Grid axis " + std::to_string(axis) + ": ";
    if (!std::isfinite(spacing) || spacing <= 0.0) {
        throw std::invalid_argument(context + "spacing must be finite and positive.");
    }
    // All integer and half indices through N must be exact before scaling.
    constexpr std::uint64_t max_half_index = std::uint64_t{1} << 52;
    if (count > max_half_index) {
        throw std::overflow_error(context + "cell count cannot resolve half indices.");
    }
    const double length = static_cast<double>(count) * spacing;
    if (!std::isfinite(length) || length <= 0.0) {
        throw std::overflow_error(context + "domain length is not representable.");
    }
    const double half_spacing = 0.5 * spacing;
    const double largest_gap = length - std::nextafter(length, 0.0);
    // A conservative whole-domain guard, not just an endpoint spot check.
    // Every native location lies in [0,L], whose largest downward ULP is here.
    if (half_spacing <= 0.0 || half_spacing < largest_gap) {
        throw std::overflow_error(context + "half-cell coordinates are not resolvable.");
    }
    return length;
}

} // namespace

UniformGrid::UniformGrid(CellCounts cells, std::array<double, 3> spacing_m,
                         AllocationLimits limits)
    : cells_(cells), spacing_m_(spacing_m), limits_(limits) {
    const auto [nx, ny, nz] = cells_.values();
    const auto nx1 = detail::checked_add(nx, 1);
    const auto ny1 = detail::checked_add(ny, 1);
    const auto nz1 = detail::checked_add(nz, 1);
    // FND-03's edge E and face H shapes; no common padded stride or ghosts.
    layouts_ = {{{{nx, ny1, nz1}, 0}, {{nx1, ny, nz1}, 0},
                 {{nx1, ny1, nz}, 0}, {{nx1, ny, nz}, 0},
                 {{nx, ny1, nz}, 0}, {{nx, ny, nz1}, 0}}};
    for (auto& component : layouts_) {
        const auto [sx, sy, sz] = component.extents;
        component.element_count = detail::checked_multiply(
            detail::checked_multiply(sx, sy), sz);
        field_elements_ = detail::checked_add(field_elements_, component.element_count);
    }
    field_bytes_ = detail::checked_multiply(field_elements_, sizeof(double));

    limits_.max_component_elements = std::min(
        limits_.max_component_elements, std::vector<double>{}.max_size());
    for (const auto& component : layouts_) {
        if (component.element_count > limits_.max_component_elements) {
            throw std::length_error("A field component exceeds its allocation limit.");
        }
    }
    if (field_bytes_ > limits_.max_field_bytes) {
        throw std::length_error("The six fields exceed the aggregate byte limit.");
    }
    for (std::size_t axis = 0; axis < 3; ++axis) {
        lengths_m_[axis] = domain_length(cells_.values()[axis], spacing_m_[axis], axis);
    }
}

const ComponentLayout& UniformGrid::layout(FieldComponent component) const {
    const auto index = static_cast<std::size_t>(component);
    if (index >= layouts_.size()) {
        throw std::invalid_argument("Unknown Yee field component.");
    }
    return layouts_[index];
}

std::size_t UniformGrid::offset(
    FieldComponent component, std::array<std::size_t, 3> index) const {
    const auto& shape = layout(component).extents;
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if (index[axis] >= shape[axis]) {
            throw std::out_of_range("Field index exceeds its component extent.");
        }
    }
    // Bounds plus validated extent products prove every intermediate fits.
    return index[0] + shape[0] * (index[1] + shape[1] * index[2]);
}

std::array<double, 3> UniformGrid::position_m(
    FieldComponent component, std::array<std::size_t, 3> index) const {
    (void)offset(component, index);
    constexpr std::array<std::array<double, 3>, 6> half_offsets{{
        {0.5, 0, 0}, {0, 0.5, 0}, {0, 0, 0.5},
        {0, 0.5, 0.5}, {0.5, 0, 0.5}, {0.5, 0.5, 0}}};
    const auto& shift = half_offsets[static_cast<std::size_t>(component)];
    std::array<double, 3> position{};
    for (std::size_t axis = 0; axis < 3; ++axis) {
        position[axis] = (static_cast<double>(index[axis]) + shift[axis]) * spacing_m_[axis];
    }
    return position;
}

bool UniformGrid::is_tangential_e_wall(
    FieldComponent component, std::array<std::size_t, 3> index) const {
    (void)offset(component, index);
    const auto component_axis = static_cast<std::size_t>(component);
    if (component_axis >= 3) {
        return false;
    }
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if (axis != component_axis &&
            (index[axis] == 0 || index[axis] == cells_.values()[axis])) {
            return true;
        }
    }
    return false;
}

bool UniformGrid::is_normal_h_wall(
    FieldComponent component, std::array<std::size_t, 3> index) const {
    (void)offset(component, index);
    const auto component_id = static_cast<std::size_t>(component);
    if (component_id < 3) {
        return false;
    }
    const auto axis = component_id - 3;
    return index[axis] == 0 || index[axis] == cells_.values()[axis];
}

} // namespace antennasim
