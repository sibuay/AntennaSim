#pragma once
// closed-v1 benchmark cases (MAT-01 specification, V04): PEC cavity eigenmodes,
// the driven cavity spectrum, and interior PEC enforcement. Fixture values are
// deterministic calculations; solver samples are the only measured output.
#include "antennasim/run.hpp"

#include <filesystem>
#include <string>
#include <vector>

namespace antennasim::benchmark::closed {
// Mode: exact discrete standing mode initialized inside a cavity (V04-A, V04-C C1).
// Source: zero fields and the antisymmetric pulse on one Ez edge (V04-B, V04-C C2/C3).
enum class Kind : unsigned char { Mode, Source };

struct Case {
    std::string name;
    std::string suite;
    Kind kind;
    UniformGrid grid;
    VacuumTimeStep dt;
    std::uint64_t steps;
    std::size_t a;                       // polarization axis of the mode
    std::array<std::size_t, 2> mode;     // transverse integers (n_b, n_c)
    std::size_t s;                       // refinement factor of the (12,16,20) cavity
    std::array<std::size_t, 3> origin;   // cavity origin in cells
    std::array<std::size_t, 3> cavity;   // cavity cells
    std::vector<PecPrimitive> primitives;
    bool region;                         // classify every sample against the shell box
    std::vector<std::array<std::size_t, 3>> ez_probes;
    std::array<std::size_t, 3> source;   // Ez edge carrying the pulse (Source kind)
    bool diagnostics;                    // per-state U/Q/maxima rows
};

// Discrete and continuum mode quantities of a Mode case (role axes cyclic from a).
struct ModeReference {
    double k_b, k_c, big_k_b, big_k_c, omega_c, omega_d, big_omega;
};
[[nodiscard]] ModeReference mode_reference(const Case& config);

struct FixtureChecks { double divergence = 0; double eigen = 0; };

[[nodiscard]] std::vector<Case> cases(std::string_view suite, std::uint64_t smoke_steps = 2);
// V04-C C1 fixture with the hollow shell (the benchmark) or the solid box of the
// same ranges (the S09 rejection case).
[[nodiscard]] Case pec_mode_case(std::size_t a, PecShape shape);
[[nodiscard]] PecMask mask(const Case& config);
[[nodiscard]] std::vector<FieldProbe> probes(const Case& config);
[[nodiscard]] FixtureChecks initialize(const Case& config, FieldStorage& fields);
// Half-time pulse samples g_m, m = 0..2M, applied during steps 0..2M.
[[nodiscard]] std::vector<double> pulse(const Case& config);
void run_suite(std::string_view suite, const std::filesystem::path& output, std::uint64_t smoke_steps = 2);
} // namespace antennasim::benchmark::closed
