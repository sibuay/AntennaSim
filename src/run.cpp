#include "antennasim/run.hpp"
#include <charconv>
#include <cmath>

namespace antennasim {
ProbeSample sample_probe(const ReferenceStepper& stepper, FieldProbe probe) {
    const auto& fields = stepper.fields();
    const auto position = fields.grid().position_m(probe.component, probe.index);
    const auto times = stepper.times();
    const double value = fields.at(probe.component, probe.index);
    if (!std::isfinite(value)) { throw std::runtime_error("Nonfinite probe value."); }
    return {probe, stepper.state_index(), position,
            static_cast<unsigned>(probe.component) < 3 ? times.e_s : times.h_s, value};
}

std::uint64_t parse_steps(std::string_view text) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string_view::npos) {
        throw std::invalid_argument("Step count must contain decimal digits only.");
    }
    std::uint64_t result = 0;
    const auto conversion = std::from_chars(text.data(), text.data() + text.size(), result);
    if (conversion.ec != std::errc{} || conversion.ptr != text.data() + text.size() ||
        result == 0 || result > (std::uint64_t{1} << 52) - 1) {
        throw std::invalid_argument("Step count is zero or exceeds native-time representation.");
    }
    return result;
}

void validate_run_steps(const VacuumTimeStep& dt, std::uint64_t steps) {
    if (steps == 0) { throw std::invalid_argument("Run requires at least one full step."); }
    (void)dt.times_at(steps);
}
} // namespace antennasim
