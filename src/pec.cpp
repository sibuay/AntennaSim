#include "antennasim/pec.hpp"
#include "antennasim/detail/checked_size.hpp"

#include <string>

namespace antennasim {
namespace {
using Index = std::array<std::size_t, 3>;

void validate(const CellBox& box, const UniformGrid& grid) {
    const auto& counts = grid.cells().values();
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if (!(box.low[axis] < box.high[axis]) || box.high[axis] > counts[axis]) {
            throw std::invalid_argument("PEC primitive axis " + std::to_string(axis) +
                " must satisfy 0 <= low < high <= cell count.");
        }
    }
}

template <class Function>
void each(Index end, Function function) {
    for (std::size_t k = 0; k < end[2]; ++k)
        for (std::size_t j = 0; j < end[1]; ++j)
            for (std::size_t i = 0; i < end[0]; ++i) function(Index{i, j, k});
}
} // namespace

bool pec_marks(const PecPrimitive& primitive, FieldComponent component, Index index) {
    const auto a = static_cast<std::size_t>(component);
    if (a >= 3) { return false; }
    const auto& low = primitive.cells.low;
    const auto& high = primitive.cells.high;
    // The edge spans index[a] to index[a]+1 along a at nodes index[b], index[c].
    if (!(low[a] <= index[a] && index[a] < high[a])) { return false; }
    bool on_face = false;
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if (axis == a) { continue; }
        if (!(low[axis] <= index[axis] && index[axis] <= high[axis])) { return false; }
        if (index[axis] == low[axis] || index[axis] == high[axis]) { on_face = true; }
    }
    return primitive.shape == PecShape::Box || on_face;
}

PecMask::PecMask(const UniformGrid& grid, std::vector<PecPrimitive> primitives)
    : grid_(grid), primitives_(std::move(primitives)) {
    for (const auto& primitive : primitives_) {
        if (primitive.shape != PecShape::Box && primitive.shape != PecShape::Shell) {
            throw std::invalid_argument("Unknown PEC primitive shape.");
        }
        validate(primitive.cells, grid_);
    }
    const PecPrimitive closure{PecShape::Shell, CellBox{{0, 0, 0}, grid_.cells().values()}};
    for (std::size_t id = 0; id < 3; ++id) {
        const auto component = static_cast<FieldComponent>(id);
        const auto& layout = grid_.layout(component);
        marks_[id].assign(layout.element_count, 0);
        bytes_ = detail::checked_add(bytes_, layout.element_count);
        each(layout.extents, [&](Index index) {
            bool mark = pec_marks(closure, component, index);
            if (mark) { ++closure_[id]; }
            for (const auto& primitive : primitives_) { mark = mark || pec_marks(primitive, component, index); }
            if (mark) {
                marks_[id][grid_.offset(component, index)] = 1;
                ++counts_[id];
            }
        });
    }
}

bool PecMask::masked(FieldComponent component, Index index) const {
    const auto offset = grid_.offset(component, index);
    const auto id = static_cast<std::size_t>(component);
    return id < 3 && marks_[id][offset] != 0;
}

bool PecMask::enclosed(FieldComponent component, Index index) const {
    (void)grid_.offset(component, index);
    const auto id = static_cast<std::size_t>(component);
    if (id < 3) { return false; }
    const auto a = id - 3, b = (a + 1) % 3, c = (a + 2) % 3;
    // FND-03 forward stencil of H_a: E_b at index and +1 along c; E_c at index and +1 along b.
    auto up_c = index; ++up_c[c];
    auto up_b = index; ++up_b[b];
    const auto eb = static_cast<FieldComponent>(b), ec = static_cast<FieldComponent>(c);
    return masked(eb, index) && masked(eb, up_c) && masked(ec, index) && masked(ec, up_b);
}

std::span<const unsigned char> PecMask::values(FieldComponent component) const {
    const auto id = static_cast<std::size_t>(component);
    if (id >= 3) { throw std::invalid_argument("Only E components carry a PEC mask."); }
    return marks_[id];
}

} // namespace antennasim
