#pragma once

#include "antennasim/vacuum.hpp"

namespace antennasim::detail {

// Internal local algebra, NOT a boundary/initial-condition validated run API.
// H targets return curl E (not minus curl E); E targets return curl H.
// Constrained E targets are rejected before backward index subtraction.
[[nodiscard]] double curl_at(const FieldStorage& fields, FieldComponent target,
                             std::array<std::size_t, 3> index);
void advance_h(FieldStorage& fields, const VacuumTimeStep& dt, std::uint64_t n);
void advance_e(FieldStorage& fields, const VacuumTimeStep& dt, std::uint64_t n);

} // namespace antennasim::detail
