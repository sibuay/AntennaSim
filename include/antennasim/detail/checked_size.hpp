#pragma once

#include <cstddef>
#include <limits>
#include <stdexcept>

namespace antennasim::detail {

// Allocation arithmetic only. Call before evaluating the potentially
// overflowing operation; unsigned wrap is never a valid storage estimate.
inline std::size_t checked_add(std::size_t a, std::size_t b) {
    if (b > std::numeric_limits<std::size_t>::max() - a) {
        throw std::length_error("Grid size addition exceeds size_t.");
    }
    return a + b;
}

inline std::size_t checked_multiply(std::size_t a, std::size_t b) {
    if (a != 0 && b > std::numeric_limits<std::size_t>::max() / a) {
        throw std::length_error("Grid size product exceeds size_t.");
    }
    return a * b;
}

} // namespace antennasim::detail
