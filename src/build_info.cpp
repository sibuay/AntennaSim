#include "antennasim/build_info.hpp"
#include "antennasim/version.hpp"

namespace antennasim {

std::string_view version() noexcept {
    return ANTENNASIM_VERSION;
}

} // namespace antennasim
