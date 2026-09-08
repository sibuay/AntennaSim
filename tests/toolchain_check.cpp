#include "antennasim/build_info.hpp"

#include <array>
#include <concepts>
#include <iostream>
#include <limits>
#include <span>

// Exercise C++20 language and standard-library support, plus core-library linkage.
// This is an infrastructure check, not a numerical accuracy test.
template <std::floating_point T>
T total(std::span<const T> values) {
    T result{};
    for (const T value : values) {
        result += value;
    }
    return result;
}

int main() {
    static_assert(std::numeric_limits<double>::is_iec559);
    static_assert(std::numeric_limits<double>::digits == 53);
    const std::array values{1.0, 2.0, 4.0};
    if (total<double>(values) != 7.0 || antennasim::version().empty()) {
        std::cerr << "C++20 toolchain or core-library linkage check failed.\n";
        return 1;
    }
    std::cout << "C++20, binary64, and core-library linkage available.\n";
    return 0;
}
