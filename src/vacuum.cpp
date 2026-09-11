#include "antennasim/vacuum.hpp"
#include "antennasim/detail/vacuum_kernel.hpp"

#include <algorithm>
#include <cmath>
#include <string>

namespace antennasim {
namespace {
using Index = std::array<std::size_t, 3>;
using enum FieldComponent;
constexpr std::array components{Ex, Ey, Ez, Hx, Hy, Hz};
constexpr std::array names{"Ex", "Ey", "Ez", "Hx", "Hy", "Hz"};

template <class Function>
void each(Index begin, Index end, Function function) {
    for (std::size_t k = begin[2]; k < end[2]; ++k) {
        for (std::size_t j = begin[1]; j < end[1]; ++j) {
            for (std::size_t i = begin[0]; i < end[0]; ++i) {
                function(Index{i, j, k});
            }
        }
    }
}

void positive_finite(double value, const char* name) {
    if (!std::isfinite(value) || value <= 0) {
        throw std::overflow_error(std::string(name) + " is not positive and finite.");
    }
}

double cfl_limit(const UniformGrid& grid) {
    const auto& spacing = grid.spacing_m();
    const auto d = *std::min_element(spacing.begin(), spacing.end());
    double sum = 0;
    for (const double da : spacing) {
        const auto ratio = d / da;
        sum += ratio * ratio;
    }
    const auto limit = (d / c0) / std::sqrt(sum);
    positive_finite(limit, "CFL limit");
    return limit;
}

std::string location(std::uint64_t n, FieldComponent component, Index index) {
    if (static_cast<std::size_t>(component) >= names.size()) {
        throw std::invalid_argument("Unknown Yee field component.");
    }
    return "state " + std::to_string(n) + ", " + names[static_cast<std::size_t>(component)] +
        "[" + std::to_string(index[0]) + "," + std::to_string(index[1]) + "," +
        std::to_string(index[2]) + "]";
}

void check_divergence(const FieldStorage& fields, bool electric) {
    const auto& grid = fields.grid();
    const auto counts = grid.cells().values();
    const Index begin = electric ? Index{1, 1, 1} : Index{0, 0, 0};
    each(begin, counts, [&](Index index) {
        double divergence = 0;
        double magnitude = 0;
        for (std::size_t a = 0; a < 3; ++a) {
            const auto component = components[a + (electric ? 0U : 3U)];
            auto high = index;
            auto low = index;
            if (electric) { --low[a]; } else { ++high[a]; }
            const double hi = fields.at(component, high) / grid.spacing_m()[a];
            const double lo = fields.at(component, low) / grid.spacing_m()[a];
            divergence += hi - lo;
            magnitude += std::abs(hi) + std::abs(lo);
        }
        if (!std::isfinite(divergence) || !std::isfinite(magnitude) ||
            std::abs(divergence) > 1e-11 * std::max(1.0, magnitude)) {
            throw std::invalid_argument(std::string(electric ? "E" : "H") +
                " initial divergence is incompatible at [" + std::to_string(index[0]) +
                "," + std::to_string(index[1]) + "," + std::to_string(index[2]) + "].");
        }
    });
}

UniformGrid checked_initial_grid(const FieldStorage& fields, const VacuumTimeStep& dt) {
    const auto& grid = fields.grid();
    if (grid.spacing_m() != dt.spacing_m()) {
        throw std::invalid_argument("Time-step spacing does not match the field grid.");
    }
    for (auto component : components) {
        each({}, grid.layout(component).extents, [&](Index index) {
            const double value = fields.at(component, index);
            if (!std::isfinite(value)) {
                throw std::invalid_argument("Nonfinite initial field: " + location(0, component, index));
            }
            if ((grid.is_tangential_e_wall(component, index) ||
                 grid.is_normal_h_wall(component, index)) && value != 0) {
                throw std::invalid_argument("Incompatible initial wall: " + location(0, component, index));
            }
        });
    }
    check_divergence(fields, true);
    check_divergence(fields, false);
    return grid;
}
} // namespace

ElectricCurrent::ElectricCurrent(const UniformGrid& grid, std::vector<CurrentSample> samples)
    : grid_(grid), samples_(std::move(samples)) {
    for (const auto& sample : samples_) {
        (void)grid_.offset(sample.component, sample.index);
        if (static_cast<unsigned>(sample.component) >= 3 ||
            grid_.is_tangential_e_wall(sample.component, sample.index) ||
            !std::isfinite(sample.amperes_per_m2)) {
            throw std::invalid_argument("Current requires finite values on unconstrained E edges.");
        }
    }
    const auto key = [&](const CurrentSample& sample) {
        return std::pair{sample.component, grid_.offset(sample.component, sample.index)};
    };
    std::sort(samples_.begin(), samples_.end(), [&](const auto& a, const auto& b) { return key(a) < key(b); });
    for (std::size_t i = 1; i < samples_.size(); ++i) {
        if (key(samples_[i-1]) == key(samples_[i])) {
            throw std::invalid_argument("Duplicate current target.");
        }
    }
}

VacuumTimeStep::VacuumTimeStep(const UniformGrid& grid, double dt_s, double limit_s)
    : spacing_m_(grid.spacing_m()), dt_s_(dt_s), limit_s_(limit_s),
      e_scale_(dt_s / epsilon0), h_scale_(dt_s / mu0) {
    if (!std::isfinite(dt_s_) || dt_s_ <= 0 || dt_s_ >= limit_s_) {
        throw std::invalid_argument("Time step must be finite, positive, and strictly below CFL.");
    }
    positive_finite(dt_s_ / 2, "Half time step");
    positive_finite(e_scale_, "Electric update scale");
    positive_finite(h_scale_, "Magnetic update scale");
    for (const double spacing : spacing_m_) {
        positive_finite(1.0 / spacing, "Reciprocal spacing");
        positive_finite(e_scale_ / spacing, "Electric derivative coefficient");
        positive_finite(h_scale_ / spacing, "Magnetic derivative coefficient");
    }
}

VacuumTimeStep VacuumTimeStep::from_courant(const UniformGrid& grid, double q) {
    if (!std::isfinite(q) || q <= 0 || q >= 1) {
        throw std::invalid_argument("Courant fraction must be finite and strictly between zero and one.");
    }
    const double limit = cfl_limit(grid);
    const double dt = q * limit;
    positive_finite(dt, "Selected time step");
    return VacuumTimeStep{grid, dt, limit};
}

VacuumTimeStep VacuumTimeStep::from_seconds(const UniformGrid& grid, double dt_s) {
    return VacuumTimeStep{grid, dt_s, cfl_limit(grid)};
}

FieldTimes VacuumTimeStep::times_at(std::uint64_t n) const {
    constexpr std::uint64_t max_state = (std::uint64_t{1} << 52) - 1;
    if (n > max_state) { throw std::overflow_error("State cannot represent half-time indices."); }
    const double step = static_cast<double>(n);
    const FieldTimes times{step * dt_s_, (step - 0.5) * dt_s_};
    const double previous_e = (step - 1) * dt_s_;
    const double previous_h = (step - 1.5) * dt_s_;
    if (!std::isfinite(times.e_s) || !std::isfinite(times.h_s) ||
        !(times.h_s < times.e_s) || (n > 0 &&
        (!(previous_e < times.h_s) || !(previous_h < times.h_s)))) {
        throw std::overflow_error("Field timestamps overflow or are no longer strictly ordered.");
    }
    return times;
}

FieldUpdateError::FieldUpdateError(std::uint64_t step, FieldComponent component, Index index)
    : std::runtime_error("Nonfinite update at " + location(step, component, index)),
      step_(step), component_(component), index_(index) {}

ReferenceStepper::ReferenceStepper(const FieldStorage& initial, VacuumTimeStep time_step)
    : fields_(checked_initial_grid(initial, time_step)), time_step_(time_step) {
    for (auto component : components) {
        each({}, fields_.grid().layout(component).extents, [&](Index index) {
            fields_.at(component, index) = initial.at(component, index);
        });
    }
}

void ReferenceStepper::require_valid() const {
    if (failed_) { throw std::logic_error("Reference stepper failed; partial fields are not a valid state."); }
}
const FieldStorage& ReferenceStepper::fields() const { require_valid(); return fields_; }
FieldTimes ReferenceStepper::times() const { require_valid(); return time_step_.times_at(state_index_); }

void ReferenceStepper::step() {
    advance(nullptr, 0);
}

void ReferenceStepper::step(const ElectricCurrent& current, double amplitude) {
    advance(&current, amplitude);
}

void ReferenceStepper::advance(const ElectricCurrent* current, double amplitude) {
    require_valid();
    try {
        (void)time_step_.times_at(state_index_ + 1);
        if (!std::isfinite(amplitude)) { throw std::invalid_argument("Nonfinite current amplitude."); }
        if (current != nullptr) {
            if (current->grid().cells().values() != fields_.grid().cells().values() ||
                current->grid().spacing_m() != fields_.grid().spacing_m()) {
                throw std::invalid_argument("Current/grid mismatch.");
            }
            for (const auto& sample : current->samples()) {
                const double j = amplitude * sample.amperes_per_m2;
                if (!std::isfinite(j) || !std::isfinite(time_step_.e_scale() * j)) {
                    throw FieldUpdateError(state_index_, sample.component, sample.index);
                }
            }
        }
        detail::advance_h(fields_, time_step_, state_index_);
        detail::advance_e(fields_, time_step_, state_index_);
        if (current != nullptr && amplitude != 0) {
            for (const auto& sample : current->samples()) {
                auto& value = fields_.at(sample.component, sample.index);
                const double next = value - time_step_.e_scale() * (amplitude * sample.amperes_per_m2);
                if (!std::isfinite(next)) { throw FieldUpdateError(state_index_, sample.component, sample.index); }
                value = next;
            }
        }
        ++state_index_;
    } catch (...) {
        failed_ = true;
        throw;
    }
}

namespace detail {
double curl_at(const FieldStorage& f, FieldComponent target, Index index) {
    const auto& grid = f.grid();
    (void)grid.offset(target, index);
    if (grid.is_tangential_e_wall(target, index)) {
        throw std::out_of_range("Backward curl is undefined at constrained E walls.");
    }
    const auto [i, j, k] = index;
    const auto [dx, dy, dz] = grid.spacing_m();
    // Positive curl in both families. FND-03 equations fix these twelve terms.
    switch (target) {
    case Hx: return (f.at(Ez, {i,j+1,k}) - f.at(Ez, {i,j,k})) / dy -
                    (f.at(Ey, {i,j,k+1}) - f.at(Ey, {i,j,k})) / dz;
    case Hy: return (f.at(Ex, {i,j,k+1}) - f.at(Ex, {i,j,k})) / dz -
                    (f.at(Ez, {i+1,j,k}) - f.at(Ez, {i,j,k})) / dx;
    case Hz: return (f.at(Ey, {i+1,j,k}) - f.at(Ey, {i,j,k})) / dx -
                    (f.at(Ex, {i,j+1,k}) - f.at(Ex, {i,j,k})) / dy;
    case Ex: return (f.at(Hz, {i,j,k}) - f.at(Hz, {i,j-1,k})) / dy -
                    (f.at(Hy, {i,j,k}) - f.at(Hy, {i,j,k-1})) / dz;
    case Ey: return (f.at(Hx, {i,j,k}) - f.at(Hx, {i,j,k-1})) / dz -
                    (f.at(Hz, {i,j,k}) - f.at(Hz, {i-1,j,k})) / dx;
    case Ez: return (f.at(Hy, {i,j,k}) - f.at(Hy, {i-1,j,k})) / dx -
                    (f.at(Hx, {i,j,k}) - f.at(Hx, {i,j-1,k})) / dy;
    }
    throw std::invalid_argument("Unknown Yee field component.");
}

void advance_h(FieldStorage& fields, const VacuumTimeStep& dt, std::uint64_t n) {
    if (dt.spacing_m() != fields.grid().spacing_m()) {
        throw std::invalid_argument("Time-step/grid spacing mismatch.");
    }
    for (const auto component : {Hx, Hy, Hz}) {
        each({}, fields.grid().layout(component).extents, [&](Index index) {
            const auto next = fields.at(component, index) - dt.h_scale() * curl_at(fields, component, index);
            if (!std::isfinite(next)) { throw FieldUpdateError(n, component, index); }
            fields.at(component, index) = next;
        });
    }
}

void advance_e(FieldStorage& fields, const VacuumTimeStep& dt, std::uint64_t n) {
    if (dt.spacing_m() != fields.grid().spacing_m()) {
        throw std::invalid_argument("Time-step/grid spacing mismatch.");
    }
    const auto counts = fields.grid().cells().values();
    // Half-open ranges from FND-03; subtract only within valid interior ranges.
    for (const auto component : {Ex, Ey, Ez}) {
        Index begin{1, 1, 1};
        begin[static_cast<std::size_t>(component)] = 0;
        each(begin, counts, [&](Index index) {
            const auto next = fields.at(component, index) + dt.e_scale() * curl_at(fields, component, index);
            if (!std::isfinite(next)) { throw FieldUpdateError(n, component, index); }
            fields.at(component, index) = next;
        });
    }
}
} // namespace detail
} // namespace antennasim
