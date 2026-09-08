#pragma once

#include <string_view>

namespace antennasim {

// Build metadata only. A version number does not imply validated physics.
[[nodiscard]] std::string_view version() noexcept;

} // namespace antennasim
