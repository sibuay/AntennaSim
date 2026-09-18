#pragma once

#include "antennasim/grid.hpp"

#include <span>
#include <vector>

namespace antennasim {

// Half-open cell ranges [low, high) on each axis, 0 <= low < high <= N.
struct CellBox {
    std::array<std::size_t, 3> low;
    std::array<std::size_t, 3> high;
};

// Box marks every E edge whose two endpoints lie in the closed box; Shell marks
// only the edges lying in one of its six face planes (MAT-01 conventions).
enum class PecShape : unsigned char { Box, Shell };

struct PecPrimitive {
    PecShape shape;
    CellBox cells;
};

// Independent rule for one E edge; exact integer index arithmetic only.
[[nodiscard]] bool pec_marks(const PecPrimitive& primitive, FieldComponent component,
                             std::array<std::size_t, 3> index);

// E-edge perfect-electric-conductor mask under docs/methods/MAT-02-pec-mask-contract.md.
// The outer zero_tangential_e closure (the whole-domain shell) is always present.
// One byte per E sample; H samples are never masked.
class PecMask {
public:
    explicit PecMask(const UniformGrid& grid, std::vector<PecPrimitive> primitives = {});

    [[nodiscard]] const UniformGrid& grid() const noexcept { return grid_; }
    [[nodiscard]] const std::vector<PecPrimitive>& primitives() const noexcept { return primitives_; }
    // True for a masked E sample; false for every H sample. Bounds are checked.
    [[nodiscard]] bool masked(FieldComponent component, std::array<std::size_t, 3> index) const;
    // True for an H sample whose four surrounding tangential E samples are all
    // masked: its curl increment is identically zero. False for E samples.
    [[nodiscard]] bool enclosed(FieldComponent component, std::array<std::size_t, 3> index) const;
    [[nodiscard]] std::span<const unsigned char> values(FieldComponent component) const;
    // Masked samples per E component including the outer closure, and the
    // closure alone.
    [[nodiscard]] const std::array<std::size_t, 3>& masked_counts() const noexcept { return counts_; }
    [[nodiscard]] const std::array<std::size_t, 3>& closure_counts() const noexcept { return closure_; }
    [[nodiscard]] std::size_t mask_bytes() const noexcept { return bytes_; }

private:
    UniformGrid grid_;
    std::vector<PecPrimitive> primitives_;
    std::array<std::vector<unsigned char>, 3> marks_;
    std::array<std::size_t, 3> counts_{};
    std::array<std::size_t, 3> closure_{};
    std::size_t bytes_ = 0;
};

} // namespace antennasim
