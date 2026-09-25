#include "antennasim/material.hpp"
#include "antennasim/vacuum.hpp"
#include "antennasim/detail/checked_size.hpp"

#include <bit>
#include <cmath>
#include <limits>
#include <map>
#include <string>
#include <utility>

namespace antennasim {
namespace {
using Index = std::array<std::size_t, 3>;
constexpr std::array names{"Ex", "Ey", "Ez"};

std::size_t cell_count(const UniformGrid& grid) {
    const auto& n = grid.cells().values();
    return detail::checked_multiply(detail::checked_multiply(n[0], n[1]), n[2]);
}

std::string cell_text(std::size_t offset, const UniformGrid& grid) {
    const auto& n = grid.cells().values();
    return "cell [" + std::to_string(offset % n[0]) + "," + std::to_string(offset / n[0] % n[1]) + "," +
        std::to_string(offset / (n[0] * n[1])) + "]";
}

void validate_values(double eps_r, double sigma, const std::string& where) {
    if (!std::isfinite(eps_r) || !(eps_r >= 1)) {
        throw std::invalid_argument("Relative permittivity must be finite and >= 1 at " + where + ".");
    }
    if (!std::isfinite(sigma) || !(sigma >= 0)) {
        throw std::invalid_argument("Conductivity must be finite and >= 0 at " + where + ".");
    }
}

// MAT-01 time-centred coefficients; relative mean first, epsilon0 afterwards.
EdgeMaterial edge_material(double eps_r, double sigma, double dt) {
    const double eps = eps_r * epsilon0;
    const double x = (sigma * dt) / (2 * eps);
    const double ca = (1 - x) / (1 + x);
    const double cb = (dt / eps) / (1 + x);
    return {eps_r, sigma, x, ca, cb, 0};
}

template <class Function>
void update_range(const UniformGrid& grid, std::size_t a, Function function) {
    // FND-03 half-open E update ranges: [0,N_a) along a, [1,N_t) transverse.
    const auto& n = grid.cells().values();
    Index begin{1, 1, 1};
    begin[a] = 0;
    for (std::size_t k = begin[2]; k < n[2]; ++k)
        for (std::size_t j = begin[1]; j < n[1]; ++j)
            for (std::size_t i = begin[0]; i < n[0]; ++i) function(Index{i, j, k});
}
} // namespace

MaterialMap::MaterialMap(const UniformGrid& grid, std::size_t bytes) : grid_(grid), bytes_(bytes) {}

MaterialMap::MaterialMap(const UniformGrid& grid, std::vector<double> eps_r, std::vector<double> sigma_s_per_m)
    : grid_(grid) {
    const auto count = cell_count(grid_);
    if (eps_r.size() != count || sigma_s_per_m.size() != count) {
        throw std::invalid_argument("Material arrays need exactly one value per cell.");
    }
    for (std::size_t cell = 0; cell < count; ++cell) {
        validate_values(eps_r[cell], sigma_s_per_m[cell], cell_text(cell, grid_));
    }
    bytes_ = detail::checked_multiply(count, 2 * sizeof(double));
    eps_r_ = std::move(eps_r);
    sigma_ = std::move(sigma_s_per_m);
}

MaterialMap MaterialMap::uniform(const UniformGrid& grid, double eps_r, double sigma_s_per_m) {
    validate_values(eps_r, sigma_s_per_m, "the uniform material");
    const auto count = cell_count(grid);
    MaterialMap map{grid, detail::checked_multiply(count, 2 * sizeof(double))};
    map.eps_r_.assign(count, eps_r);
    map.sigma_.assign(count, sigma_s_per_m);
    return map;
}

std::size_t MaterialMap::cell_offset(Index cell) const {
    const auto& n = grid_.cells().values();
    for (std::size_t axis = 0; axis < 3; ++axis) {
        if (cell[axis] >= n[axis]) { throw std::out_of_range("Material cell index is outside the grid."); }
    }
    return cell[0] + n[0] * (cell[1] + n[1] * cell[2]);
}

double MaterialMap::eps_r(Index cell) const { return eps_r_[cell_offset(cell)]; }
double MaterialMap::sigma(Index cell) const { return sigma_[cell_offset(cell)]; }

EdgeCoefficients::EdgeCoefficients(const MaterialMap& materials, const VacuumTimeStep& dt)
    : EdgeCoefficients(materials.grid(), dt, &materials) {}

EdgeCoefficients EdgeCoefficients::vacuum(const UniformGrid& grid, const VacuumTimeStep& dt) {
    return EdgeCoefficients{grid, dt, nullptr};
}

EdgeCoefficients::EdgeCoefficients(const UniformGrid& grid, const VacuumTimeStep& dt, const MaterialMap* materials)
    : grid_(grid) {
    if (grid_.spacing_m() != dt.spacing_m()) {
        throw std::invalid_argument("Material/time-step spacing mismatch.");
    }
    const auto& n = grid_.cells().values();
    for (std::size_t a = 0; a < 3; ++a) {
        const auto count = grid_.layout(static_cast<FieldComponent>(a)).element_count;
        index_bytes_ = detail::checked_add(index_bytes_, detail::checked_multiply(count, sizeof(std::uint32_t)));
    }
    std::map<std::pair<std::uint64_t, std::uint64_t>, std::uint32_t> seen;
    for (std::size_t a = 0; a < 3; ++a) {
        const auto component = static_cast<FieldComponent>(a);
        auto& index = index_[a];
        index.assign(grid_.layout(component).element_count, 0);
        const auto b = (a + 1) % 3, c = (a + 2) % 3;
        update_range(grid_, a, [&](Index edge) {
            double eps_r = 1, sigma = 0;
            if (materials != nullptr) {
                // The four cells sharing the edge, in the transverse plane at cell edge[a].
                Index cell = edge;
                eps_r = 0; sigma = 0;
                for (const auto [db, dc] : {std::pair{1, 1}, std::pair{0, 1}, std::pair{1, 0}, std::pair{0, 0}}) {
                    cell[b] = edge[b] - static_cast<std::size_t>(db);
                    cell[c] = edge[c] - static_cast<std::size_t>(dc);
                    const auto offset = cell[0] + n[0] * (cell[1] + n[1] * cell[2]);
                    eps_r += materials->eps_r_values()[offset];
                    sigma += materials->sigma_values()[offset];
                }
                eps_r /= 4;
                sigma /= 4;
            }
            const std::pair key{std::bit_cast<std::uint64_t>(eps_r), std::bit_cast<std::uint64_t>(sigma)};
            auto found = seen.find(key);
            if (found == seen.end()) {
                if (table_.size() >= std::numeric_limits<std::uint32_t>::max()) {
                    throw std::length_error("Edge coefficient table exceeds the uint32 index range.");
                }
                auto entry = edge_material(eps_r, sigma, dt.seconds());
                if (!std::isfinite(entry.x) || !std::isfinite(entry.ca) || !std::isfinite(entry.cb) || !(entry.cb > 0)) {
                    throw std::overflow_error(std::string("Edge coefficients are not finite with Cb > 0 at ") +
                        names[a] + "[" + std::to_string(edge[0]) + "," + std::to_string(edge[1]) + "," +
                        std::to_string(edge[2]) + "].");
                }
                found = seen.emplace(key, static_cast<std::uint32_t>(table_.size())).first;
                table_.push_back(entry);
            }
            index[grid_.offset(component, edge)] = found->second;
            ++table_[found->second].edges;
        });
    }
}

const EdgeMaterial& EdgeCoefficients::at(FieldComponent component, Index index) const {
    const auto offset = grid_.offset(component, index);
    if (static_cast<std::size_t>(component) >= 3 || grid_.is_tangential_e_wall(component, index)) {
        throw std::out_of_range("Edge coefficients are defined only on unconstrained E samples.");
    }
    return at_offset(component, offset);
}

std::span<const std::uint32_t> EdgeCoefficients::indices(FieldComponent component) const {
    const auto id = static_cast<std::size_t>(component);
    if (id >= 3) { throw std::invalid_argument("Only E components carry edge coefficients."); }
    return index_[id];
}

} // namespace antennasim
