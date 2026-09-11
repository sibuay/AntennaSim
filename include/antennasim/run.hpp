#pragma once
#include "antennasim/vacuum.hpp"
#include <string_view>

namespace antennasim {
struct FieldProbe {
    FieldComponent component;
    std::array<std::size_t, 3> index;
};
struct ProbeSample {
    FieldProbe probe;
    std::uint64_t state;
    std::array<double, 3> position_m;
    double time_s;
    double value;
};
[[nodiscard]] ProbeSample sample_probe(const ReferenceStepper& stepper, FieldProbe probe);
[[nodiscard]] std::uint64_t parse_steps(std::string_view text);
void validate_run_steps(const VacuumTimeStep& dt, std::uint64_t steps);
} // namespace antennasim
