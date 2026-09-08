#pragma once

#include "antennasim/grid.hpp"

#include <span>
#include <vector>

namespace antennasim {

// Fixed owner of six zero-initialized binary64 Yee arrays. No clock or solver.
// See docs/methods/REF-02-field-storage-contract.md for invariants and scope.
class FieldStorage {
public:
    explicit FieldStorage(UniformGrid grid);
    FieldStorage(const FieldStorage&) = delete;
    FieldStorage& operator=(const FieldStorage&) = delete;
    FieldStorage(FieldStorage&&) = delete;
    FieldStorage& operator=(FieldStorage&&) = delete;

    [[nodiscard]] const UniformGrid& grid() const noexcept { return grid_; }
    [[nodiscard]] double& at(FieldComponent component, std::array<std::size_t, 3> index);
    [[nodiscard]] const double& at(
        FieldComponent component, std::array<std::size_t, 3> index) const;
    // Borrowed read-only contiguous view, valid until this owner is destroyed.
    [[nodiscard]] std::span<const double> values(FieldComponent component) const;

private:
    UniformGrid grid_;
    std::array<std::vector<double>, 6> fields_;
};

} // namespace antennasim
