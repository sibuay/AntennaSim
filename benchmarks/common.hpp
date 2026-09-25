#pragma once
// Internal helpers shared by the benchmark libraries (not a public API).
// Fixture/diagnostic differences use an independent permutation construction;
// no production curl or update routine is called from here.
#include "antennasim/run.hpp"

#include <array>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <locale>
#include <numbers>
#include <string>
#include <utility>

namespace antennasim::benchmark::common {
using Index = std::array<std::size_t, 3>;
constexpr double pi = std::numbers::pi;
constexpr std::array names{"Ex", "Ey", "Ez", "Hx", "Hy", "Hz"};
constexpr std::size_t budget = std::size_t{2} * 1024 * 1024 * 1024;
constexpr std::size_t overhead = 16 * 1024 * 1024;

inline FieldComponent component(std::size_t id) { return static_cast<FieldComponent>(id); }

template<class Function> void each(Index end, Function function) {
    for (std::size_t k = 0; k < end[2]; ++k)
        for (std::size_t j = 0; j < end[1]; ++j)
            for (std::size_t i = 0; i < end[0]; ++i) function(Index{i,j,k});
}
template<class Function> void all(const UniformGrid& grid, Function function) {
    for (std::size_t id = 0; id < 6; ++id)
        each(grid.layout(component(id)).extents, [&](Index index) { function(id, index); });
}

// Independent permutation construction used by fixtures/diagnostics only.
// Forward differences for H targets, backward for E targets.
template<class Get> double curl(const UniformGrid& grid, std::size_t target, Index index, Get get) {
    const bool forward = target >= 3;
    const std::size_t axis = target % 3, u = (axis+1)%3, v = (axis+2)%3;
    const auto derivative = [&](std::size_t source_axis, std::size_t direction) {
        auto high = index, low = index;
        if (forward) ++high[direction]; else --low[direction];
        const auto source = source_axis + (forward ? 0U : 3U);
        return (get(source, high) - get(source, low)) / grid.spacing_m()[direction];
    };
    return derivative(v, u) - derivative(u, v);
}

// Compensated (Kahan) accumulation for the weighted diagnostics.
struct Sum {
    double total = 0, correction = 0;
    void add(double value) {
        const double y = value-correction, t = total+y;
        correction = (t-total)-y; total = t;
    }
};

inline std::ofstream stream(const std::filesystem::path& path) {
    std::ofstream out;
    out.exceptions(std::ios::badbit | std::ios::failbit);
    out.imbue(std::locale::classic());
    out.open(path);
    out << std::setprecision(17);
    return out;
}
template<class Array> void json_array(std::ostream& out, const Array& values) {
    out << '[';
    bool first = true;
    for (auto value : values) { if (!first) out << ','; first = false; out << value; }
    out << ']';
}
// Benchmark-side four-cell mean of an interior E_a edge, summed in its own
// order ((b,c), (b-1,c), (b,c-1), (b-1,c-1)); independent of the solver table.
inline std::pair<double, double> edge_average(const MaterialMap& map, std::size_t a, Index edge) {
    const auto b = (a + 1) % 3, c = (a + 2) % 3;
    double eps = 0, sigma = 0;
    for (std::size_t dc = 0; dc < 2; ++dc)
        for (std::size_t db = 0; db < 2; ++db) {
            Index cell = edge;
            cell[b] -= db;
            cell[c] -= dc;
            eps += map.eps_r(cell);
            sigma += map.sigma(cell);
        }
    return {eps / 4, sigma / 4};
}

// Solver coefficient table as emitted provenance (17 significant digits).
inline void coefficients_json(std::ostream& out, const EdgeCoefficients& table) {
    out << "\"coefficients\":{\"provenance\":\"solver table: four-cell mean of eps_r and sigma per unconstrained E edge, "
           "eps_e=eps_r_e*epsilon0, x=sigma_e*dt/(2 eps_e), Ca=(1-x)/(1+x), Cb=(dt/eps_e)/(1+x); deduplicated, uint32 index per E sample\","
        << "\"index_bytes\":" << table.index_bytes() << ",\"table_bytes\":" << table.table_bytes() << ",\"entries\":[";
    bool first = true;
    for (const auto& entry : table.table()) {
        out << (first ? "" : ",") << "{\"eps_r\":" << entry.eps_r << ",\"sigma_S_per_m\":" << entry.sigma_s_per_m
            << ",\"x\":" << entry.x << ",\"Ca\":" << entry.ca << ",\"Cb\":" << entry.cb << ",\"edges\":" << entry.edges << '}';
        first = false;
    }
    out << "]}";
}

inline void json_string(std::ostream& out, const char* value) {
    out << '"';
    for (const char character : std::string(value)) {
        const auto ch = static_cast<unsigned char>(character);
        if (ch == '"' || ch == '\\') out << '\\' << static_cast<char>(ch);
        else if (ch < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                             << static_cast<unsigned>(ch) << std::dec << std::setfill(' ');
        else out << static_cast<char>(ch);
    }
    out << '"';
}
} // namespace antennasim::benchmark::common
