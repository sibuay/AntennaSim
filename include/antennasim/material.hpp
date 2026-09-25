#pragma once

#include "antennasim/grid.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace antennasim {

class VacuumTimeStep;

// Per-cell isotropic relative permittivity and constant conductivity under
// docs/methods/MAT-03-material-update-contract.md. Cell order i + Nx (j + Ny k).
// Validated before anything is stored: finite eps_r >= 1, finite sigma >= 0,
// one value per cell. mu = mu0 everywhere; no magnetic or dispersive material.
class MaterialMap {
public:
    MaterialMap(const UniformGrid& grid, std::vector<double> eps_r, std::vector<double> sigma_s_per_m);
    // Validates the two scalars before allocating the per-cell arrays.
    [[nodiscard]] static MaterialMap uniform(const UniformGrid& grid, double eps_r, double sigma_s_per_m);

    [[nodiscard]] const UniformGrid& grid() const noexcept { return grid_; }
    [[nodiscard]] double eps_r(std::array<std::size_t, 3> cell) const;
    [[nodiscard]] double sigma(std::array<std::size_t, 3> cell) const;
    [[nodiscard]] std::span<const double> eps_r_values() const noexcept { return eps_r_; }
    [[nodiscard]] std::span<const double> sigma_values() const noexcept { return sigma_; }
    [[nodiscard]] std::size_t bytes() const noexcept { return bytes_; }

private:
    MaterialMap(const UniformGrid& grid, std::size_t bytes);
    [[nodiscard]] std::size_t cell_offset(std::array<std::size_t, 3> cell) const;
    UniformGrid grid_;
    std::vector<double> eps_r_;
    std::vector<double> sigma_;
    std::size_t bytes_ = 0;
};

// One deduplicated edge material and its time-centred update coefficients.
struct EdgeMaterial {
    double eps_r;           // four-cell arithmetic mean of the relative permittivity
    double sigma_s_per_m;   // four-cell arithmetic mean of the conductivity
    double x;               // sigma_e dt / (2 eps_e)
    double ca;              // (1 - x) / (1 + x)
    double cb;              // (dt / eps_e) / (1 + x), in m/F * s
    std::size_t edges;      // update-range E samples using this entry
};

// MAT-01 edge coefficients stored as a deduplicated table plus one uint32
// index per E sample (D023). Only the FND-03 update ranges are classified;
// tangential outer-wall samples hold index 0 and are never read.
class EdgeCoefficients {
public:
    EdgeCoefficients(const MaterialMap& materials, const VacuumTimeStep& dt);
    // eps_r,e = 1 and sigma_e = 0 through the same formula: Ca = 1, Cb = dt/epsilon0.
    [[nodiscard]] static EdgeCoefficients vacuum(const UniformGrid& grid, const VacuumTimeStep& dt);

    [[nodiscard]] const UniformGrid& grid() const noexcept { return grid_; }
    // Checked; tangential outer-wall E samples and H components are rejected.
    [[nodiscard]] const EdgeMaterial& at(FieldComponent component, std::array<std::size_t, 3> index) const;
    // Unchecked lookup by an already validated layout offset (kernel use).
    [[nodiscard]] const EdgeMaterial& at_offset(FieldComponent component, std::size_t offset) const {
        return table_[index_[static_cast<std::size_t>(component)][offset]];
    }
    [[nodiscard]] std::span<const EdgeMaterial> table() const noexcept { return table_; }
    [[nodiscard]] std::span<const std::uint32_t> indices(FieldComponent component) const;
    [[nodiscard]] std::size_t index_bytes() const noexcept { return index_bytes_; }
    [[nodiscard]] std::size_t table_bytes() const noexcept { return table_.size() * sizeof(EdgeMaterial); }

private:
    EdgeCoefficients(const UniformGrid& grid, const VacuumTimeStep& dt, const MaterialMap* materials);
    UniformGrid grid_;
    std::vector<EdgeMaterial> table_;
    std::array<std::vector<std::uint32_t>, 3> index_;
    std::size_t index_bytes_ = 0;
};

} // namespace antennasim
