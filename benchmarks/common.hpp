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
