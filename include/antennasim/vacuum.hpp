#pragma once

#include "antennasim/fields.hpp"
#include "antennasim/material.hpp"
#include "antennasim/pec.hpp"

#include <cstdint>
#include <stdexcept>
#include <vector>

namespace antennasim {

// Pinned FND-03 / 2022 CODATA convention; SI quantities.
inline constexpr double c0 = 299792458.0;
inline constexpr double mu0 = 1.25663706127e-6;
inline constexpr double epsilon0 = 1.0 / (mu0 * c0 * c0);
inline constexpr double eta0 = mu0 * c0;

struct FieldTimes { double e_s; double h_s; };

struct CurrentSample {
    FieldComponent component;
    std::array<std::size_t, 3> index;
    double amperes_per_m2;
};

// Fixed impressed E-edge current shape; values apply at the update half time.
class ElectricCurrent {
public:
    ElectricCurrent(const UniformGrid& grid, std::vector<CurrentSample> samples);
    [[nodiscard]] const UniformGrid& grid() const noexcept { return grid_; }
    [[nodiscard]] std::span<const CurrentSample> samples() const noexcept { return samples_; }
private:
    UniformGrid grid_;
    std::vector<CurrentSample> samples_;
};

class VacuumTimeStep {
public:
    [[nodiscard]] static VacuumTimeStep from_courant(const UniformGrid& grid, double q = 0.99);
    [[nodiscard]] static VacuumTimeStep from_seconds(const UniformGrid& grid, double dt_s);
    [[nodiscard]] double seconds() const noexcept { return dt_s_; }
    [[nodiscard]] double limit_seconds() const noexcept { return limit_s_; }
    [[nodiscard]] double courant_fraction() const noexcept { return dt_s_ / limit_s_; }
    [[nodiscard]] double e_scale() const noexcept { return e_scale_; }
    [[nodiscard]] double h_scale() const noexcept { return h_scale_; }
    [[nodiscard]] const std::array<double, 3>& spacing_m() const noexcept { return spacing_m_; }
    [[nodiscard]] FieldTimes times_at(std::uint64_t n) const;

private:
    VacuumTimeStep(const UniformGrid& grid, double dt_s, double limit_s);
    std::array<double, 3> spacing_m_;
    double dt_s_;
    double limit_s_;
    double e_scale_;
    double h_scale_;
};

class FieldUpdateError : public std::runtime_error {
public:
    FieldUpdateError(std::uint64_t step, FieldComponent component, std::array<std::size_t, 3> index);
    [[nodiscard]] std::uint64_t step() const noexcept { return step_; }
    [[nodiscard]] FieldComponent component() const noexcept { return component_; }
    [[nodiscard]] const std::array<std::size_t, 3>& index() const noexcept { return index_; }
private:
    std::uint64_t step_;
    FieldComponent component_;
    std::array<std::size_t, 3> index_;
};

// Per-cell isotropic eps_r/sigma (vacuum by default) with rho=0 initially
// (eps-weighted edge divergence) inside an E-edge PEC mask whose outer closure
// is the zero_tangential_e box; forms without a mask have no interior
// conductor. Every constructor runs the MAT-03 material kernel. Explicitly
// copies initial fields. Local algebra harnesses live in detail/.
class ReferenceStepper {
public:
    ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step);
    ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step, PecMask mask);
    ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step, const MaterialMap& materials);
    ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step, PecMask mask,
                     const MaterialMap& materials);
    ReferenceStepper(const ReferenceStepper&) = delete;
    ReferenceStepper& operator=(const ReferenceStepper&) = delete;
    ReferenceStepper(ReferenceStepper&&) = delete;
    ReferenceStepper& operator=(ReferenceStepper&&) = delete;

    void step();
    void step(const ElectricCurrent& current, double amplitude = 1.0);
    // Borrowed view, valid for this owner's lifetime. It changes on step().
    // After any step exception, discard earlier views: fields may be partial.
    [[nodiscard]] const FieldStorage& fields() const;
    [[nodiscard]] FieldTimes times() const;
    [[nodiscard]] std::uint64_t state_index() const noexcept { return state_index_; }
    [[nodiscard]] bool failed() const noexcept { return failed_; }
    [[nodiscard]] const VacuumTimeStep& time_step() const noexcept { return time_step_; }
    [[nodiscard]] const PecMask& mask() const noexcept { return mask_; }
    [[nodiscard]] const EdgeCoefficients& coefficients() const noexcept { return coefficients_; }

private:
    ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step, PecMask mask,
                     EdgeCoefficients coefficients);
    void advance(const ElectricCurrent* current, double amplitude);
    void require_valid() const;
    PecMask mask_;
    // Built and validated before the owned field copy is allocated.
    EdgeCoefficients coefficients_;
    FieldStorage fields_;
    VacuumTimeStep time_step_;
    std::uint64_t state_index_ = 0;
    bool failed_ = false;
};
} // namespace antennasim
