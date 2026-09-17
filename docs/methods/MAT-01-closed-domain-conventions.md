# MAT-01 — PEC, isotropic material, and spectral conventions

Version 1, 2026-09-18. Status: **specified and author-reviewed**; no P2 solver
code exists and no PEC, material, or spectral capability is validated. The
benchmark obligations are in the
[MAT-01 closed-domain specification](../validation/MAT-01-closed-domain-benchmarks.md);
the audit evidence is in the [MAT-01 review](../validation/MAT-01-review.md).
This note extends [FND-03](FND-03-yee-conventions.md) without changing any P1
convention, and it fixes the numerical conventions that MAT-02, MAT-03, and
MAT-04 must implement. API, error-type, and output-lifecycle decisions remain
those items' contracts.

## Scope and sources

Phase 2 adds, on the unchanged uniform Yee grid: explicit perfect electric
conductor (PEC) edges, interior and outer; a per-cell isotropic, nondispersive
relative permittivity and constant electric conductivity with `mu = mu0`
everywhere; and the frequency-domain processing of native time series. No
magnetic material, magnetic conductivity, dispersive model, anisotropy,
subcell/conformal treatment, absorbing boundary, or port is included.

Sources consulted on 2026-09-18 from the author-hosted text of John B. Schneider,
*Understanding the Finite-Difference Time-Domain Method* (2010):

- [Chapter 9](https://eecs.wsu.edu/~schneidj/ufdtd/chap9.pdf), section 9.3,
  equations 9.9–9.20 (printed pages 248–250) and the coefficient definitions
  9.21–9.32 (pages 250–251): three-dimensional updates with an electric
  conductivity term approximated by the average of the field at two time steps,
  with `Cexe=(1-sigma*dt/(2*eps))/(1+sigma*dt/(2*eps))` and
  `Cexh=(dt/eps)/(1+sigma*dt/(2*eps))`; section 9.7 (page 288): the
  unequal-spacing stability bound already adopted by FND-03.
- [Chapter 3](https://eecs.wsu.edu/~schneidj/ufdtd/chap3.pdf), section 3.11
  (page 64, figure 3.16): an interface collocated with an electric-field node
  uses the average of the permittivities to either side; section 3.12,
  equations 3.48–3.52 (pages 64–65): the time-averaged conduction term and the
  resulting update coefficients.
- [Chapter 7](https://eecs.wsu.edu/~schneidj/ufdtd/chap7.pdf), section 7.6,
  equations 7.47–7.72 (pages 169–173): analytic FDTD reflection/transmission
  coefficients; section 7.7 (page 173): reflection from a PEC node; section
  7.8, equations 7.79–7.97 (pages 175–179): for an interface aligned with an
  electric-field node the arithmetic-average permittivity makes the discrete
  reflection coefficient purely real and is the optimum for all permittivities
  and discretizations.

The three-dimensional specializations, the edge-averaging rule, the PEC mask
semantics, the energy/dissipation identity, the closed-form discrete cavity,
interface, and lossy-eigenwave references, and the spectral conventions below
are project derivations. No source code was copied.

## Material model and supported scope

Materials are assigned **per cell** `(i,j,k)`, `0<=i<Nx`, `0<=j<Ny`,
`0<=k<Nz`, by two finite binary64 values:

| Quantity | Symbol / unit | Allowed values |
| --- | --- | --- |
| Relative permittivity | `eps_r` (dimensionless), `eps=eps_r*epsilon0` | finite, `eps_r >= 1` |
| Electric conductivity | `sigma` / S/m | finite, `sigma >= 0` |
| Permeability | `mu = mu0` | fixed; no magnetic material |

Both are frequency independent. A constant `sigma` is **not** a constant
loss-tangent material: its loss tangent `tan(delta)=sigma/(omega*eps)` falls as
`1/f`. The model must not be presented as a broadband loss-tangent model
(project plan). `eps_r<1`, negative or nonfinite values, and any magnetic
request are rejected before allocation. Vacuum is `eps_r=1`, `sigma=0`.

The governing equations become

```text
eps dE/dt + sigma E = curl H - J
mu0 dH/dt = -curl E
```

with FND-03's SI units, signs, staggering, time levels, and impressed-current
convention unchanged.

## Edge coefficients and the lossy update

Every unconstrained E edge is shared by exactly four cells (the FND-03 update
ranges exclude the tangential outer-face edges, and an interior `E_a` edge at
integer transverse indices `1..N-1` always has the four neighbouring cells in
its transverse plane). Define the edge values as arithmetic means of those four
cells:

```text
eps_r,e = (eps_r,1 + eps_r,2 + eps_r,3 + eps_r,4) / 4
sigma_e = (sigma_1 + sigma_2 + sigma_3 + sigma_4) / 4
eps_e   = eps_r,e * epsilon0
x_e     = sigma_e * dt / (2 * eps_e)
Ca_e    = (1 - x_e) / (1 + x_e)
Cb_e    = (dt / eps_e) / (1 + x_e)
```

The E update at an unconstrained edge is

```text
Enew = Ca_e * E + Cb_e * (curl H_plus - J_half)
```

which is Schneider's 9.27–9.32 form with the conduction term centred at
`(n+1/2)*dt` by the average `(Enew+E)/2` (equation 3.50). The H update is
unchanged. Compute the relative mean first and multiply by `epsilon0`
afterwards; then vacuum gives `eps_r,e=1`, `sigma_e=0`, `x_e=0`, `Ca_e=1`
exactly and `Cb_e=dt/epsilon0` exactly, so the material kernel reproduces the
P1 vacuum arithmetic bitwise (`1.0*E` is exact and the source subtraction keeps
the REF-04 form `E - Cb_e*(amplitude*J)`). This bitwise vacuum equivalence is a
requirement on MAT-03, checked by reproducing the tracked V01–V03 summary at zero
tolerance. Coefficients are validated finite and `Cb_e>0` before stepping.

For a planar interface on a cell face, the E edges lying **in** the interface
plane (tangential to it) receive the mean of the two media; normal edges lie
entirely in one medium. This is the node-aligned interface of Schneider 3.11 and
7.8. Its discrete reflection coefficient is derived in closed form for the V05
fixtures below. Curved or oblique material boundaries are staircased by the
per-cell assignment; version 1 validates only grid-aligned planar interfaces.

## Stability and the lossy energy identity

Let `<.,.>_w` be the FND-04 weighted inner product (weights only touch
constrained samples, which are zero), `C` the forward E-to-H curl and `C*` the
backward H-to-E curl with `<E,C*H>_w=<CE,H>_w` (S05 identity, unchanged by
per-edge coefficients because they multiply the equations, not the operators).
With `eps` the per-edge value and `Ebar=(E^(n+1)+E^n)/2`, multiplying the E
update by `Ebar`, the H update by `H`, and using the adjoint identity gives,
for `J=0`,

```text
U_n = dV/2 * [ <eps E^n, E^n>_w + mu0 <H^(n-1/2), H^(n-1/2)>_w ]
Q_n = dV/2 * [ <eps E^n, E^n>_w + mu0 <H^(n-1/2), H^(n+1/2)>_w ]
    = U_n - dV*dt/2 * <H^(n-1/2), C E^n>_w
D_n = dV*dt * <sigma Ebar_n, Ebar_n>_w >= 0
Q_(n+1) = Q_n - D_n                                   (exact arithmetic)
```

`Q` is the FND-04 invariant with `eps` weighting; `D_n` is the discrete Joule
dissipation over one step, exactly nonnegative. With `sigma=0` the identity
reduces to the V03 conservation. The lower bound follows as in FND-04: since
`eps>=epsilon0` and `mu=mu0`, `dt*c0*||C||/2 <= q` implies
`(1-q) U_n <= Q_n <= (1+q) U_n` with `q` the vacuum Courant fraction. Hence the
**vacuum CFL bound of FND-03 remains the time-step policy** for every allowed
material (`c_max = c0` for `eps_r>=1`, and the centred conduction term is
dissipative for every `sigma>=0` and every `dt`). The `VacuumTimeStep` policy is
therefore retained unchanged; a material configuration with `eps_r<1` would
require a rederived bound and is rejected. This bound is a stability policy, not
an accuracy statement: the conduction discretization has an `O((sigma*dt/(2*eps))^2)`
decay-rate error whose exact value is given below.

The identity holds with interior PEC edges because those E samples are zero:
the summation-by-parts boundary terms vanish on any surface where tangential
E is constrained to zero.

## Explicit PEC edges

A PEC region is represented as a set of **E edges** (`pec_edges`), stored per
E component as a mask over that component's allocated extents. Semantics:

- Two grid-aligned primitives are specified by half-open cell ranges
  `[i0,i1) x [j0,j1) x [k0,k1)` with `0<=i0<i1<=Nx` etc., evaluated with exact
  integer/half-integer index arithmetic, never with floating-point coordinates.
  An `E_a` edge with integer storage index `(i_a, i_b, i_c)` (cyclic `a,b,c`)
  spans the endpoints `i_a` and `i_a+1` along `a` at the node coordinates
  `i_b`, `i_c`. **`pec_box` (solid)** marks every E edge whose two endpoints
  both lie in the closed box, i.e. `i0<=i_a<i1`, `j0<=i_b<=j1`, `k0<=i_c<=k1`
  for `E_a` and cyclically for the others: all edges on the surface and in the
  interior. **`pec_shell` (hollow)** marks only the edges that lie in one of
  the six face planes: the same ranges with the additional condition
  `i_b in {j0,j1}` or `i_c in {k0,k1}` for `E_a` (an `a`-directed edge never
  lies in an `a`-face). The interior of a shell is free and evolves as an
  independent cavity. Primitives may overlap; the mask is their union with the
  outer closure. A single cell, plate, or wire of zero thickness is not a
  version-1 shape.
- The outer `zero_tangential_e` closure of FND-03 is exactly
  `pec_shell([0,Nx) x [0,Ny) x [0,Nz))`; it is always present. Metadata report
  the closure label, every primitive, and the number of masked edges per
  component.
- Masked E samples are held at exactly zero: they are never written by the
  update, initial fields must be exactly zero there (reject otherwise), and
  impressed currents must not target them (reject). Probes may read them. A
  cavity fixture or source therefore belongs inside a `pec_shell`, never inside
  a `pec_box`, whose interior edges are masked.
- H samples are never masked. An H sample whose four surrounding tangential E
  samples are all masked receives a zero curl increment and therefore stays at
  its initial value; the initial screening requires it to be zero on the outer
  normal walls, in the interior of a `pec_box`, and on the face planes of a
  `pec_shell` (the H samples with an integer index on a face are the face-normal
  components), so that a shell's exterior stays exactly zero when only its
  interior is excited, and its interior stays exactly zero when only the
  exterior is excited (V04-C).
- Surface charge on PEC faces is implied by Gauss's law and is not tracked;
  the P1 initial-divergence screening is applied only at nodes whose six
  surrounding E samples are all unmasked and unconstrained.

Cost: one byte per E sample (`Nex+Ney+Nez` bytes) in the reference
implementation, counted in the run budget; a bit mask is a permitted later
optimization after validation. The update cost is unchanged; masked edges are
skipped.

## Closed-form discrete references used by version 1

These are exact properties of the scheme above and serve as the "discrete"
comparators, separate from the continuum references.

**Cavity modes.** In the closed box with all outer E tangential zero, the
separable fields `sin`/`cos` products in the FND-03 positions are exact
eigenvectors. For mode integers `(m,n,p)` with `K_a=(2/d_a) sin(m pi d_a/(2 L_a))`
etc., every polarization of the triple has the single discrete frequency
`omega_d=(2/dt) asin(c0 dt |K| / 2)`, against the continuum
`omega_c=c0 pi sqrt((m/L_x)^2+(n/L_y)^2+(p/L_z)^2)`. A standing mode obeys
`E^n=E_s cos(omega n dt)`, `H^(n+1/2)=H_s sin(omega (n+1/2) dt)` with
`H_s=-C E_s/(mu0 Omega)`, `Omega=(2/dt) sin(omega dt/2)`, independently of
`eps`. For a single-component mode `E_a=sin(k_b r_b) sin(k_c r_c)` (cyclic
`a,b,c`, zero along `a`), `H_b,s=-K_c sin(k_b r_b) cos(k_c r_c')/(mu0 Omega)`
and `H_c,s=+K_b cos(k_b r_b') sin(k_c r_c)/(mu0 Omega)` at the native H
positions. The three-term recurrence `E^(n+1)+E^(n-1)=2 cos(omega dt) E^n`
holds exactly for any sample of a single mode.

**Cavity response to an edge current.** For an impressed current on one `Ez`
edge, the transverse (divergence-free) part of each triple responds with
amplitude proportional to `(1-K_z^2/|K|^2) phi(src) phi(probe)/||phi||^2 /
(eps cos(omega_d dt/2)) * |J_d(omega_d)|`, where `phi` is the separable `Ez`
shape and `J_d` the discrete half-time transform of the pulse; the
longitudinal part returns to zero when the pulse samples sum to zero. This
fixes which spectral lines a driven cavity must show and their relative
strengths.

**Reduced TE system.** With `E=E_b(r_a,r_c) u_b`, `E_b=e(r_a) sin(pi r_c/L_c)`
and `N_b=2`, the scheme reduces exactly to
`mu0 dh_a/dt = K_c e`, `mu0 dh_c/dt = -D_a e`, `eps de/dt = -K_c h_a - D_a^* h_c - J_b`
with `K_c=(2/d_c) sin(pi d_c/(2 L_c))`; the other four components stay
exactly zero and the two `b` planes stay bitwise identical. For a harmonic of
frequency `f` the discrete axial wavenumber in a medium `eps_r` is
`kappa=(2/d_a) asin(d_a sqrt(eps_r Omega^2/c0^2 - K_c^2)/2)`,
`Omega=(2/dt) sin(pi f dt)`.

**Interface reflection.** With the node-aligned interface at axial node
`i_int` using the mean permittivity `eps_avg`, and `G=exp(-i kappa2 d_a) - 2 -
d_a^2 (K_c^2 - mu0 eps_avg Omega^2)`, the discrete coefficients referenced to the
interface node are

```text
R_d = -(G + exp(+i kappa1 d_a)) / (G + exp(-i kappa1 d_a)),   T_d = 1 + R_d
```

which tends to the continuum modal `R=(beta1-beta2)/(beta1+beta2)`,
`beta_i=sqrt(eps_r,i k0^2 - (pi/L_c)^2)`, and is purely real (the audit finds
`|Im R_d|<1e-15` across the band), consistent with Schneider 7.96.

**Slab-loaded cavity.** With `e[i]=sin(kappa1 i d_a)` for `i<=i_int` and
`B sin(kappa2 (N_a-i) d_a)` for `i>=i_int`, the interface-node equation
`(e[i+1]-2e[i]+e[i-1])/d_a^2 = (K_c^2 - mu0 eps_avg Omega^2) e[i]` multiplied by
`sin(kappa2 (N_a-i_int) d_a)` is a pole-free characteristic function whose
roots are the discrete modes; the continuum characteristic function is
`beta1 cos(beta1 L1) sin(beta2 L2) + beta2 sin(beta1 L1) cos(beta2 L2)`.

**Lossy eigenwave.** For a real spatial harmonic with discrete wavenumber `K`
in a uniform `eps`, `sigma` medium, the per-step growth factor `z` (the root
with positive imaginary part) solves
`(eps + sigma dt/2) z^2 + (-2 eps + dt^2 K^2/mu0) z + (eps - sigma dt/2) = 0`.
Its modulus is exactly `sqrt((1-x)/(1+x))`, `x=sigma dt/(2 eps)`, independent of
`K`, so the discrete decay rate `-ln|z|/dt` differs from the continuum
`alpha=sigma/(2 eps)` by the relative amount `x^2/3 + O(x^4)`; the phase
`arg(z)/dt` approximates the continuum `sqrt(c0^2 k^2/eps_r - alpha^2)` with the
usual spatial dispersion error. The exact discrete mode is
`E^n = Re{A z^n exp(-i k r_a)}` with
`H^(n-1/2) = w s_H Re{hhat z^(n-1/2) exp(-i k r_a)}`,
`hhat/A = (i dt K/mu0)/(z^(1/2) - z^(-1/2))` (principal square root), which for
`sigma=0` reduces to the V01 initialization `hhat/A=1/eta`. Both families must
be initialized from the lossy `z`: starting the lossless mode in a lossy medium
excites the conjugate mode as well, and the first per-step ratio is then
`(z0 - x)/(1+x)` instead of `z` (a 4.6e-2 deviation for `sigma=0.1`, `p=24`),
which the V06-A acceptance is designed to reject.

## Spectral processing conventions

Time-domain samples are the native probes of REF-04: an E series has times
`t_n = n dt`, an H series `t_n = (n-1/2) dt`; the phase reference is `t=0`,
the E time origin. The forward transform of a series `x_n`, `n=0..N-1`, with a
window `w_n` is

```text
X(f) = dt * sum_n w_n x_n exp(-2 pi i f t_n)
```

using FND-03's `exp(-i omega t)` kernel, so `X(f)` estimates the continuous-time
transform in `[x]*s` and a real cosine of amplitude `A` at a bin centre with the
rectangular window gives `|X|=A N dt/2`. Requested frequencies may be arbitrary
(running discrete-time sum evaluated during a run); FFT-based analysis uses bins
`f_m=m/(N dt)` and must agree with the direct sum. Windows: rectangular
(`w_n=1`, default) and Hann `w_n = 0.5 - 0.5 cos(2 pi (n+1/2)/N)` (coherent
gain 0.5, main lobe two bins wide, first side lobe -31 dB). Spectral
resolution is the bin spacing `1/(N dt)`; lines closer than about four bins are
not separated by the Hann window and must not be claimed as identified.
Peak location uses fourfold zero padding and parabolic interpolation of the
log magnitude; V07 fixes its accuracy on synthetic two-tone data. No
normalization by the source spectrum, pulse shape, or window energy is implied
unless the benchmark specifies it (V05-B divides by the gated incident
spectrum). An H series is transformed at its own half-step times; shifting it
to E times is never implicit.

Production spectral output (MAT-04) is a deterministic calculation from probe
series, not a solver result; it must reproduce the independent direct sum on
the same samples within `1e-12` of the peak magnitude and is validated on
synthetic signals (V07) and against the independently analysed cavity spectrum
(V04-B) before it may be used for any physical claim.

## Validation obligations

The [closed-domain specification](../validation/MAT-01-closed-domain-benchmarks.md)
fixes V04–V07 (fixtures, comparators, thresholds, resources) and the S09–S14
structural extensions. All twelve existing CTests and the V01–V03 suites remain
permanent regressions; MAT-03 must reproduce the tracked REF-05 summary at zero
tolerance through the material-capable kernel in vacuum. This method note
establishes no validated PEC, material, or spectral capability.
