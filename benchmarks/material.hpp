#pragma once
// closed-v1 material cases (MAT-01 specification V05/V06, MAT-03 contract):
// homogeneous dielectric and lossy eigenwaves, the TE-mode interface, the
// slab-loaded cavity and the closed-grid dissipation identity. Fixture and
// prediction values are deterministic calculations; solver samples are the
// only measured output.
#include "antennasim/run.hpp"

#include <complex>
#include <filesystem>
#include <string>
#include <vector>

namespace antennasim::benchmark::material {
// Wave: V01-grid discrete eigenwave (V05-A lossless, V06-A lossy).
// Sheet: zero fields and a J_b sheet source (V05-B interface).
// Slab: exact discrete slab-cavity eigenvector (V05-C).
// Modular: V03 normalized modular fixture in a lossy dielectric (V06-B).
enum class Kind : unsigned char { Wave, Sheet, Slab, Modular };

struct Case {
    std::string name;
    std::string suite;
    Kind kind;
    UniformGrid grid;
    VacuumTimeStep dt;
    std::uint64_t steps;
    std::array<std::size_t, 3> roles;    // (a, b, c)
    std::size_t p;
    std::size_t mode;                    // slab mode index (1, 2)
    double eps_r;                        // loaded region (everywhere for uniform maps)
    double sigma;                        // S/m, loaded region
    std::size_t i_int;                   // first loaded cell along a; 0 means uniform
    bool diagnostics;                    // per-state U/Q/D/maxima rows
    std::size_t i_src = 0, i_p1 = 0, i_p2 = 0;
    std::uint64_t gate = 0;
    double omega = 0;                    // wave: lossless omega_d; slab: 2 pi f_d
    double f_d = 0, f_c = 0;             // slab discrete and continuum roots (Hz)
    std::complex<double> z{}, h{};       // wave: per-step growth factor and H phasor at -dt/2
};

struct FixtureChecks { double divergence = 0; double plateau = 0; double eigen = 0; };

[[nodiscard]] bool is_suite(std::string_view suite);
// Material cases of a suite; "smoke" returns the five material smoke cases.
[[nodiscard]] std::vector<Case> cases(std::string_view suite, std::uint64_t smoke_steps = 2);
[[nodiscard]] MaterialMap materials(const Case& config);
[[nodiscard]] std::vector<FieldProbe> probes(const Case& config);
[[nodiscard]] FixtureChecks initialize(const Case& config, FieldStorage& fields);
// Half-time amplitudes of the V05-B Gaussian sheet source, one per step.
[[nodiscard]] std::vector<double> sheet_pulse(const Case& config);
void run_case(const Case& config, const std::filesystem::path& path);
} // namespace antennasim::benchmark::material
