# FND-03 — Reference Yee-grid conventions

Version 1, 2026-09-05. Status: **specified and author-reviewed**; no solver
implementation or physical validation is implied. Review evidence is in
[FND-03 review](../validation/FND-03-review.md). This resolves decision O002.

## Scope and sources

This is the implementation contract for the initial scalar CPU reference:
three spatial dimensions, homogeneous vacuum, uniform spacing along each axis
with `dx`, `dy`, and `dz` allowed to differ, and a finite rectangular domain.
There is no reduced-dimensional solver mode. Material interfaces, loss,
interior conductors, absorbing/periodic boundaries, ports, nonuniform cells,
and radiation processing require later specifications and validation.

Sources consulted on 2026-09-05:

- John B. Schneider, *Understanding the Finite-Difference Time-Domain Method*,
  2010, [author-hosted Chapter 9](https://eecs.wsu.edu/~schneidj/ufdtd/chap9.pdf),
  section 9.3, figures 9.3–9.4, equations 9.9–9.20: field placement and curl
  updates; section 9.7, equation 9.53: unequal-spacing stability bound.
  Printed pages 246–250 and 288. We specialize to zero conductivity and retain
  SI field values; we do not adopt the scaled fields of section 9.7.
- Schneider, [Chapter 7](https://eecs.wsu.edu/~schneidj/ufdtd/chap7.pdf),
  sections 7.3–7.5, equations 7.33–7.39 and 7.45–7.46: discrete harmonic
  analysis, dispersion, and impedance. Component signs must follow the local
  axes below, rather than an unsigned ratio copied from a different polarization.
- NIST, [2022 CODATA constants table](https://physics.nist.gov/cuu/pdf/all.pdf):
  speed of light and vacuum magnetic permeability. The constant set is pinned
  below; future table changes must not silently change benchmark references.

Equations below are the project's explicit specialization and indexing
derivation. Storage order, allowed inputs, default Courant fraction, and the
provisional boundary contract are project decisions, not source recommendations.
No source implementation has been copied.

## Units, constants, and signs

Use a right-handed Cartesian frame, `x cross y = z`, with origin `(0,0,0)` at
the minimum domain corner. Internal lengths are metres and times are seconds.

| Quantity | Symbol / internal unit |
| --- | --- |
| Electric field | E / V/m |
| Magnetic field intensity | H / A/m; not B |
| Permittivity, permeability | epsilon / F/m, mu / H/m |
| Electric current density | J / A/m^2 |
| Frequency, angular frequency | f / Hz, omega = 2 pi f / rad/s |

Pin `c0 = 299792458 m/s` (exact SI value) and
`mu0 = 1.25663706127e-6 H/m` (rounded 2022 CODATA central value, not exact).
Derive `epsilon0 = 1 / (mu0 * c0 * c0)` and `eta0 = mu0 * c0` from those
same values. Do not separately round a tabulated epsilon0 or use `377` as
the impedance reference. Record the constants version in numerical evidence.
CODATA uncertainty is distinct from discretization or measurement error.

Time-domain fields are real binary64 values. Reserve the phasor convention
`F(r,t) = Re{Fhat(r,omega) exp(+i omega t)}` and forward-transform kernel
`exp(-i omega t)`. A wave travelling in direction `k` has spatial factor
`exp(-i k dot r)`. This fixes signs only; windows, finite-transform
normalization, and production spectral processing remain MAT-01/MAT-04 work.

In vacuum, with an optional prescribed electric current:

```text
epsilon0 dE/dt = curl H - J
mu0      dH/dt = -curl E
div(epsilon0 E) = rho
div(mu0 H) = 0
```

The curl updates do not repair inconsistent initial divergence. Source-free
initial data must satisfy the discrete constraints. Any prescribed J must have
a declared charge interpretation consistent with `d rho/dt + div J = 0`;
arbitrary field edits are not a validated antenna feed.

For a +x travelling plane wave with E along +y, H is along +z and `Ey/Hz = eta0`.
For E along +z, H is along -y and `Ez/Hy = -eta0`. In both cases `E cross H`
points along +x. Use these as independent sign checks.

## Spatial layout and storage

`Nx, Ny, Nz` count cells, not nodes. The domain is
`[0,Nx*dx] x [0,Ny*dy] x [0,Nz*dz]`. Each count is an integer at least 2.
This lower bound keeps an interior update region for every E component;
one-cell and reduced-dimensional configurations are unsupported initially.

Each component owns a contiguous array. Its integer index `(i,j,k)` names the
following physical point; half offsets are implicit, never stored as indices.

| Component | Position in units of (dx,dy,dz) | Array extents (sx,sy,sz) |
| --- | --- | --- |
| Ex | (i+1/2, j, k) | (Nx, Ny+1, Nz+1) |
| Ey | (i, j+1/2, k) | (Nx+1, Ny, Nz+1) |
| Ez | (i, j, k+1/2) | (Nx+1, Ny+1, Nz) |
| Hx | (i, j+1/2, k+1/2) | (Nx+1, Ny, Nz) |
| Hy | (i+1/2, j, k+1/2) | (Nx, Ny+1, Nz) |
| Hz | (i+1/2, j+1/2, k) | (Nx, Ny, Nz+1) |

Allocated indices obey `0 <= i < sx`, `0 <= j < sy`, `0 <= k < sz`.
Choose x-contiguous storage: `offset = i + sx * (j + sy * k)`.
The reference loop order is k outermost, j next, i innermost. This differs
from the source's z-contiguous example without changing the field placement.
No padding, guard cells, periodic wrap, or extra boundary layers are implied.
Never use a common cell-array stride for the six differently sized components.

Use checked `std::size_t` for allocated extents, products, and offsets. Reject
negative parsed inputs before conversion to unsigned values. Check additions,
each extent product, total element count, byte count, and container `max_size`
before allocation. Check index bounds before subtraction; do not evaluate
`j-1` at `j=0` and rely on a later condition to discard it.

Fields, spacings, time step, coefficients, and probe values use IEEE 754
binary64 (`double`, 53 significand bits). Preserve the FND-02 strict
floating-point settings. Do not promise bitwise agreement across platforms.

## Time levels and one complete step

At state index n, store `E^n` at time `n*dt` and `H^(n-1/2)` at
`(n-1/2)*dt`. One step performs, in order:

1. Check/enforce zero tangential E on the outer faces, including at startup.
2. Update all H components from E^n to obtain H^(n+1/2).
3. Update the interior E components from H^(n+1/2) to obtain E^(n+1),
   including `-dt/epsilon0 * J^(n+1/2)` when the specified source is enabled.
4. Keep all tangential boundary E values zero; advance the state index.
5. Record E at `(n+1)*dt` and H at `(n+1/2)*dt` with their actual coordinates.

Do not interleave an E update with unfinished H updates. Separate arrays allow
in-place updates within each field family because its right-hand side uses
only the other family and its own old value. An integer step count controls
the run; derive timestamps by multiplication, not accumulated addition.

Default initialization is `E^0=0`, `H^(-1/2)=0`. An analytical initial-field
fixture must instead evaluate both families at their own positions and time
levels and meet the boundary and divergence constraints relevant to that case.
Setting H to its t=0 value without justification changes the initial-value
problem and introduces an unwanted transient. If a current source is used,
it is sampled at the E edge and half time step; its units and support must be
specified by the benchmark. No source may overwrite a constrained boundary E.

## Six update equations

In the following equations `E` on the right is at n and `H` on the right is
at n+1/2, except each H component's own old value at n-1/2. `Hnew` and `Enew`
denote n+1/2 and n+1, respectively. `J` is at n+1/2. All bracket indices are
integer storage indices from the table above.

```text
Hnew_x[i,j,k] = Hold_x[i,j,k] + dt/mu0 * (
    (Ey[i,j,k+1] - Ey[i,j,k])/dz
  - (Ez[i,j+1,k] - Ez[i,j,k])/dy )

Hnew_y[i,j,k] = Hold_y[i,j,k] + dt/mu0 * (
    (Ez[i+1,j,k] - Ez[i,j,k])/dx
  - (Ex[i,j,k+1] - Ex[i,j,k])/dz )

Hnew_z[i,j,k] = Hold_z[i,j,k] + dt/mu0 * (
    (Ex[i,j+1,k] - Ex[i,j,k])/dy
  - (Ey[i+1,j,k] - Ey[i,j,k])/dx )

Enew_x[i,j,k] = E_x[i,j,k] + dt/epsilon0 * (
    (Hz[i,j,k] - Hz[i,j-1,k])/dy
  - (Hy[i,j,k] - Hy[i,j,k-1])/dz - Jx[i,j,k] )

Enew_y[i,j,k] = E_y[i,j,k] + dt/epsilon0 * (
    (Hx[i,j,k] - Hx[i,j,k-1])/dz
  - (Hz[i,j,k] - Hz[i-1,j,k])/dx - Jy[i,j,k] )

Enew_z[i,j,k] = E_z[i,j,k] + dt/epsilon0 * (
    (Hy[i,j,k] - Hy[i-1,j,k])/dx
  - (Hx[i,j,k] - Hx[i,j-1,k])/dy - Jz[i,j,k] )
```

Set J to zero in source-free runs. These are centred derivatives at the
target component's position and at the midpoint of its old and new times.
For example, the Ez pair in the Hx equation lies at
`(i, j+1, k+1/2)` and `(i, j, k+1/2)`, centred at Hx's
`(i, j+1/2, k+1/2)`. The denominator is dy, regardless of dx or dz.
The same midpoint construction fixes each of the other eleven derivatives.

Use these exact half-open update ranges:

| Component | i range | j range | k range |
| --- | --- | --- | --- |
| Hx | [0,Nx+1) | [0,Ny) | [0,Nz) |
| Hy | [0,Nx) | [0,Ny+1) | [0,Nz) |
| Hz | [0,Nx) | [0,Ny) | [0,Nz+1) |
| Ex | [0,Nx) | [1,Ny) | [1,Nz) |
| Ey | [1,Nx) | [0,Ny) | [1,Nz) |
| Ez | [1,Nx) | [1,Ny) | [0,Nz) |

All H locations have the required forward E neighbours. The omitted E
locations are precisely the tangential outer-face values. All other E
locations have the required backward H neighbours. There is no ghost-value
read and no uninitialized boundary coefficient.

## Provisional outer boundary

Use the explicit label `zero_tangential_e` in initial run metadata. On the two
x faces constrain Ey and Ez; on the y faces constrain Ex and Ez; on the z
faces constrain Ex and Ey. Apply the union of these constraints on edges and
corners. Initial fields must obey them; reject incompatible input rather than
silently changing a supplied fixture.

This is a reflecting, PEC-like box closure, not an absorbing boundary or an
open-space simulation. H normal to each boundary face is allocated and updated;
its curl increment is zero because the surrounding tangential E values are
zero. Require its initial value to be zero for the initial supported fixtures.
Tangential H and the nearest interior normal E remain free to evolve.
Do not zero every component on every outer index plane.

P1 uses this closure only to make the reference stencil well-defined. MAT-02
must validate physical PEC/cavity behavior before claiming that capability.
An extended simulation in this box is not an antenna radiation result.

V01/V02 must exclude boundary contamination from their measurement regions.
A geometric path-length/c0 estimate is a planning aid, not by itself a proof
of exact discrete isolation. Boundary-incompatible initial plane waves can
launch disturbances immediately at transverse walls. FND-04 must account for
all faces, source support, initial data, and the full measurement window using
a stencil domain-of-dependence bound or a specified enlarged-domain comparison.
Do not add an unplanned periodic boundary to make a plane-wave fixture work.

## Stability and supported input policy

For homogeneous vacuum define

```text
dt_max = 1 / (c0 * sqrt(1/dx^2 + 1/dy^2 + 1/dz^2))
q = dt / dt_max
```

Select default `q=0.99`; accept only finite `0 < q < 1`. An explicit dt must
be finite, positive, and strictly less than the computed dt_max. Reject the
equality case and values above the bound; do not clamp a requested value or
silently lower it. The 0.99 value is a margin below the stability limit, not
an accuracy claim. The theoretical equality limit is excluded to avoid relying
on marginal modes and roundoff at the edge of the stable range.

For a representable evaluation, with `d=min(dx,dy,dz)`, use the equivalent
`dt_max = (d/c0) / sqrt((d/dx)^2 + (d/dy)^2 + (d/dz)^2)`.
Validate the computed result and coefficients as finite and positive. Reject
nonrepresentable geometry, coefficients, or timestamps; an algebraically valid
input is not necessarily a supported floating-point configuration.

Reject non-finite/zero/negative spacings; non-integral, too-small, or overflowing
cell counts; invalid extents/allocations; non-finite field/source samples;
out-of-range probes/sources; and unsupported material/boundary requests.
Check domain lengths, coordinate calculations, final time, and time ordering
for representability. Require a positive integer run step count; inspection
of the initial state is a separate operation. A run encountering non-finite
fields must fail with its step/component/location, not emit a successful result.
REF-01/REF-03 will choose concrete error types and enforce these requirements.

The bound applies to this lossless uniform vacuum method. It must be rederived
or justified for later material, nonuniform-grid, or boundary formulations.
Smaller dt alone does not remove spatial dispersion. Both space and time
differences have second-order truncation error for smooth fields; boundaries,
sources, discontinuities, and derived observables may change measured error.

For independent analysis, insertion of a discrete plane harmonic gives

```text
Omega = (2/dt) sin(omega*dt/2)
Ka = (2/da) sin(ka*da/2),  a in {x,y,z}
Omega^2 = c0^2 * (Kx^2 + Ky^2 + Kz^2)
```

On the physical branch this tends to `omega=c0*|k|` as resolution increases.
Bounding each sine by one yields the stated CFL bound. The dispersion relation
is an independent mathematical check of the discrete scheme; agreement with it
alone does not establish agreement with continuum wave speed. FND-04 must
measure both and include unequal cell sizes and multiple polarizations.

## Sampling and diagnostics

Raw probes report component, integer index, physical coordinate, SI unit, time,
and value. E and H values with matching integer indices are not collocated in
space or time. Store their actual timestamps even when written on the same row.

For comparison, either evaluate the analytical field at each native location
and time or specify interpolation/phase translation to a common event. For
example, at the Ey location of an x-directed plane wave, average Hz across
`i-1` and `i` and across times n-1/2 and n+1/2 to compare with Ey^n. This
requires four samples, an interior i, and retaining the old H samples.
For a single harmonic the average introduces the factor
`cos(kx*dx/2) cos(omega*dt/2)`; it is not an exact correction. V02 must specify
its alignment method, treatment of that error, and exclusion of weak samples
before setting an impedance tolerance. Never divide instantaneous E by H
near a zero crossing without a defined estimator and signal floor.

A weighted squared-field norm is a useful diagnostic, but combining E and H
at different times is not an exactly conserved physical energy. V03 must
define its diagnostic, boundary weights, reference normalization, excitation
interval, observation duration, and growth criterion. Do not infer instability
from one oscillation of a naive energy estimate or claim stability from merely
avoiding NaNs in a short run.

## Cost and validation obligations

The six arrays contain exactly

```text
Nfields = Nx*(Ny+1)*(Nz+1) + (Nx+1)*Ny*(Nz+1) + (Nx+1)*(Ny+1)*Nz
        + (Nx+1)*Ny*Nz + Nx*(Ny+1)*Nz + Nx*Ny*(Nz+1)
field_bytes = 8 * Nfields
```

This excludes container overhead, source/probe buffers, diagnostic scratch,
and saved output. Each step costs O(Nx*Ny*Nz); runtime also scales with the
step count. Refining all three spacings by two at fixed physical domain and
duration costs approximately 8 times the field storage and 16 times the
update work. This is a deterministic scaling estimate, not measured performance.
Use scalar loops and scalar vacuum coefficients first; no backend abstraction
or optimization is needed to realize this contract.

Before P1 implementation, FND-04 must supply independently specified V01–V03
cases and structural checks, including:

- Location, extent, flattening, overflow, boundary-union, and invalid-input
  checks, including the smallest supported grid and unequal spacings.
- All six components, all twelve derivative contributions, zero-curl fields,
  independently evaluated affine-field curls, and discrete divergence of curl.
- Source-free and driven time-level checks, current sign/units, boundary
  compatibility, and probe timestamps/alignment.
- Continuum propagation and signed impedance references, three-resolution
  sensitivity, boundary isolation, and long-time stability/input-policy checks.

Numerical thresholds are deliberately absent here. FND-04 must define geometry,
measurement procedures, independent references, concrete tolerances and their
justification, resource estimates, evidence artifacts, and executable command
contracts. FND-05 must review those records before REF-01 starts. This method
note establishes no validated electromagnetic capability.
