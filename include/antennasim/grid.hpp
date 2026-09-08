#pragma once

#include <array>
#include <concepts>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <type_traits>

namespace antennasim {

template <class T>
concept CellCountInteger = std::integral<T> &&
                          !std::same_as<std::remove_cv_t<T>, bool>;

// Integral API: floating-point/text parsing must not truncate into a cell count.
class CellCounts {
public:
    template <CellCountInteger X, CellCountInteger Y, CellCountInteger Z>
    CellCounts(X x, Y y, Z z)
        : values_{validate(x), validate(y), validate(z)} {}

    [[nodiscard]] const std::array<std::size_t, 3>& values() const noexcept {
        return values_;
    }

private:
    template <CellCountInteger T>
    static std::size_t validate(T value) {
        if (value < 2) {
            throw std::invalid_argument("Each grid axis needs at least two cells.");
        }
        if constexpr (std::numeric_limits<T>::digits >
                      std::numeric_limits<std::size_t>::digits) {
            if (value > static_cast<T>(std::numeric_limits<std::size_t>::max())) {
                throw std::length_error("Cell count exceeds size_t.");
            }
        }
        return static_cast<std::size_t>(value);
    }

    std::array<std::size_t, 3> values_;
};

enum class FieldComponent : unsigned char { Ex, Ey, Ez, Hx, Hy, Hz };

struct ComponentLayout {
    std::array<std::size_t, 3> extents;
    std::size_t element_count;
};

struct AllocationLimits {
    std::size_t max_component_elements = std::numeric_limits<std::size_t>::max();
    std::size_t max_field_bytes = std::numeric_limits<std::size_t>::max();
};

// Validated uniform-grid metadata under docs/methods/FND-03-yee-conventions.md.
// Owns no fields. Passing these checks neither reserves RAM nor validates dt.
class UniformGrid {
public:
    UniformGrid(CellCounts cells, std::array<double, 3> spacing_m,
                AllocationLimits limits = {});

    [[nodiscard]] const CellCounts& cells() const noexcept { return cells_; }
    [[nodiscard]] const std::array<double, 3>& spacing_m() const noexcept {
        return spacing_m_;
    }
    [[nodiscard]] const std::array<double, 3>& lengths_m() const noexcept {
        return lengths_m_;
    }
    [[nodiscard]] const ComponentLayout& layout(FieldComponent component) const;
    // Bounds are checked before offset/coordinate arithmetic (REF-02 contract).
    [[nodiscard]] std::size_t offset(
        FieldComponent component, std::array<std::size_t, 3> index) const;
    [[nodiscard]] std::array<double, 3> position_m(
        FieldComponent component, std::array<std::size_t, 3> index) const;
    [[nodiscard]] bool is_tangential_e_wall(
        FieldComponent component, std::array<std::size_t, 3> index) const;
    [[nodiscard]] bool is_normal_h_wall(
        FieldComponent component, std::array<std::size_t, 3> index) const;
    [[nodiscard]] std::size_t field_elements() const noexcept { return field_elements_; }
    [[nodiscard]] std::size_t field_bytes() const noexcept { return field_bytes_; }
    // Effective limits: callers cannot raise the actual vector<double> limit.
    [[nodiscard]] const AllocationLimits& allocation_limits() const noexcept {
        return limits_;
    }

private:
    CellCounts cells_;
    std::array<double, 3> spacing_m_;
    std::array<double, 3> lengths_m_{};
    std::array<ComponentLayout, 6> layouts_{};
    std::size_t field_elements_ = 0;
    std::size_t field_bytes_ = 0;
    AllocationLimits limits_;
};

} // namespace antennasim
