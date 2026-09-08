#pragma once

#include "antennasim/fields.hpp"

#include <cstdint>
#include <stdexcept>

namespace antennasim {

// Pinned FND-03 / 2022 CODATA convention; SI quantities.
inline constexpr double c0 = 299792458.0;
inline constexpr double mu0 = 1.25663706127e-6;
inline constexpr double epsilon0 = 1.0 / (mu0 * c0 * c0);
inline constexpr double eta0 = mu0 * c0;

struct FieldTimes { double e_s; double h_s; };

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

// Source-free vacuum, rho=0, provisional reflecting zero_tangential_e box.
// Explicitly copies initial fields. Local algebra harnesses live in detail/.
class ReferenceStepper {
public:
    ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step);
    ReferenceStepper(const ReferenceStepper&) = delete;
    ReferenceStepper& operator=(const ReferenceStepper&) = delete;
    ReferenceStepper(ReferenceStepper&&) = delete;
    ReferenceStepper& operator=(ReferenceStepper&&) = delete;

    void step();
    // Borrowed view, valid for this owner's lifetime. It changes on step().
    // After any step exception, discard earlier views: fields may be partial.
    [[nodiscard]] const FieldStorage& fields() const;
    [[nodiscard]] FieldTimes times() const;
    [[nodiscard]] std::uint64_t state_index() const noexcept { return state_index_; }
    [[nodiscard]] bool failed() const noexcept { return failed_; }
    [[nodiscard]] const VacuumTimeStep& time_step() const noexcept { return time_step_; }

private:
    void require_valid() const;
    FieldStorage fields_;
    VacuumTimeStep time_step_;
    std::uint64_t state_index_ = 0;
    bool failed_ = false;
};
} // namespace antennasim
