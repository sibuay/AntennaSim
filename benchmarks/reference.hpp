#pragma once
#include "antennasim/run.hpp"
#include <filesystem>
#include <string>
#include <vector>

namespace antennasim::benchmark {
struct Case {
    std::string name;
    UniformGrid grid;
    VacuumTimeStep dt;
    std::uint64_t steps;
    std::size_t a = 0, b = 1, p = 24;
    bool propagation = true, enlarged = false, driven = false;
};
struct FixtureChecks { double divergence = 0; double plateau = 0; };
[[nodiscard]] std::vector<Case> cases(std::string_view suite, std::uint64_t smoke_steps = 2);
[[nodiscard]] std::vector<FieldProbe> probes(const Case& config);
[[nodiscard]] FixtureChecks initialize(const Case& config, FieldStorage& fields);
void run_suite(std::string_view suite, const std::filesystem::path& output, std::uint64_t smoke_steps = 2);
} // namespace antennasim::benchmark
