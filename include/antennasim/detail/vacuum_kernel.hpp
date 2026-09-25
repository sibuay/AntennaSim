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
// Skips masked E samples; the outer closure is already excluded by the ranges,
// so a mask without interior primitives performs the identical arithmetic.
void advance_e(FieldStorage& fields, const VacuumTimeStep& dt, std::uint64_t n, const PecMask& mask);
// MAT-03 material kernel: Enew = Ca*E + Cb*curl H on unmasked update-range
// samples; with vacuum coefficients it is bitwise the masked vacuum kernel.
void advance_e(FieldStorage& fields, const VacuumTimeStep& dt, std::uint64_t n, const PecMask& mask,
               const EdgeCoefficients& coefficients);

} // namespace antennasim::detail
