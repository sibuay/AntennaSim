# FND-04 — Benchmark specification review evidence

Date: 2026-09-05. Decision: **FND-04 complete; FND-05 ready; P0 remains open.**
Scope: [version-1 specification](FND-04-reference-benchmarks.md) and
[analytical audit](../../scripts/check_reference_benchmarks.py).
Identity: local snapshot, no Git repository/revision. Source/build identities
from [FND-02](FND-02-source-sha256.txt) are unchanged (nine of nine).
[FND-04 snapshot hashes](FND-04-source-sha256.txt) identify this specification,
audit, review, and updated project records.

The same collaborator authored and reviewed this work. No second agent or
independent human reviewer participated. Analytical comparators are independent
of the future solver, but the reviewer is not independent. The audit imports
FND-03's handwritten stencil transcription for the exact adjoint check; neither
script parses the specification or exercises a production electromagnetic kernel.

## Completion matrix

| FND-04 obligation | Evidence / outcome |
| --- | --- |
| Exact references, equations, assumptions | Schneider chapters 7/9 revisited; FND-03 pinned vacuum constants retained; project-specific derivations explicitly separated |
| Concrete V01/V02 geometry and excitation | Six axis/polarization pairs; three unequal-spacing meshes; initial curls of masked potentials at native time levels; 36 total primary/sensitivity/domain configurations |
| Initial divergence and all-face boundary policy | Curl identity and zero collar reviewed algebraically; conservative 2N+6 cell dependency guard; enlarged-domain comparison mandatory in REF-05 |
| Independent phase and impedance measurement | Two-column spatial fit, final/initial phase ratio, continuum and discrete errors separately required; signed complex E/H with native-time translation and signal floors |
| Tolerances and refinement | Fixed preimplementation h^2 continuum caps, discrete consistency limits, complex impedance bound, three-level order range, q and mesh-shape sensitivity |
| V03 energy/stability | Exact staggered invariant derived, weighted adjoint checked, positive norm bound, four 20,000-step source-free observation cases including driven startup; explicit input rejection matrix |
| Structural suite | S01–S08 specified with fixtures, independent formulas, normalized floors, exact integer constraints, and REF owners |
| Commands and evidence | Working specification-audit commands distinguished from future CLI/analysis contracts; required metadata/raw samples/reports and failure behavior declared |
| Resource feasibility | Finest six-field storage 489.380 MiB; serial working-memory budget 2 GiB; operation estimates and streaming outputs; actual runtime/memory still to be measured |
| Review and capability status | Author-reviewed specification only; no numerical capability validated and no phase gate closed |

## Deterministic calculations executed

Environment: existing Anaconda Python 3.9.7, standard library only; Windows x64,
as recorded in [environment](../ENVIRONMENT.md). Commands from project root:

```powershell
python scripts/check_yee_conventions.py
python scripts/check_reference_benchmarks.py
```

The existing convention audit passes: 12 derivative midpoint/axis checks, six
affine curls, 676 stencil endpoint reads, and storage counts on two grids.
The new audit produced the following **analytical predictions**, not solver
measurements:

| p | Steps | Continuum phase-speed error | Fixed cap | All-face guard in cell units |
| --- | --- | --- | --- | --- |
| 24 | 3 | 0.00120829246432 | 0.0015 | 23.5 > 12 |
| 48 | 6 | 0.000301257333745 | 0.000375 | 47.5 > 18 |
| 96 | 12 | 0.0000752634589699 | 0.00009375 | 95.5 > 30 |

- Predicted refinement orders: 2.003901430 and 2.000974863, inside [1.8,2.2].
- q=0.5 sensitivity: six steps, error 0.00243512003878 <0.003.
- Cubic sensitivity: four steps, error 0.00192599561389 <0.003.
- Synthetic native-space/time fits, both ratio signs and travel directions:
  normalized complex-impedance error at most 1.43e-15; recovered frequency
  meets the synthetic 1e-12 comparison. No solver samples were used.
- Eighteen exact-rational modal identities verify the sign/time convention
  of the modified invariant. Exact nontrivial weighted adjoint comparisons on
  (2,3,4) and (5,4,3) give equal dot products -52411/30 and -27929/6.
- Propagation suite: 865,603,584 full-grid cell-steps; stability suite:
  215,083,008. These exclude diagnostic costs and are not runtime estimates.

The audit does not generate/evolve the 3D physical fixtures, evaluate their
production divergence, validate production probe output, or perform long-time
integration. Those remain required REF-04/05 work. The compatible-curl fixture
and dependency proof were reviewed from the documented equations. S05 must
repeat the adjoint check on production operators before using the invariant.

Review corrected two draft transcription issues before fixing version 1: a
redundant phase-ratio expression was simplified to Arg(C_N/C_0), and the cost
audit was corrected to distinguish the 20,000-step initial runs from the
20,008-step driven runs. No solver results existed and no tolerance was loosened.

## Infrastructure regression

No C++ source, build configuration, or existing test was changed. Ran:

```powershell
./scripts/build.ps1 -Configuration Debug
./scripts/build.ps1 -Configuration Release
```

| Execution | Configure/build | CTest | Interpretation |
| --- | --- | --- | --- |
| Sandbox Debug | Pass, Ninja no work | 1/3; two CLI failures, 0xc0000135; 0.18 s | Failed run preserved |
| Sandbox Release | Pass, Ninja no work | 1/3; same CLI failures; 0.16 s | Failed run preserved |
| Approved Debug | Pass, Ninja no work | 3/3; 0.14 s | Existing infrastructure passes |
| Approved Release | Pass, Ninja no work | 3/3; 0.17 s | Existing infrastructure passes |

This repeats FND-03's environment-specific CLI startup behavior. Identical
sources succeed outside the sandbox; the precise DLL/access mechanism remains
unisolated. No build-policy change was made. Failed logs were retained at
`build/FND-04-debug-sandbox-LastTest.log` and
`build/FND-04-release-sandbox-LastTest.log`; successful logs are in the existing
build trees' `Testing/Temporary/LastTest.log`. This is an incremental regression,
not a fresh clean-build claim. FND-05 must reproduce the clean-build gate checks.

Local Markdown file targets and the nine FND-02 file hashes were checked.
Physical benchmarks and future command contracts were **not run: no solver or
benchmark runner exists**. The specifications must not be reported as numerical
validation successes.

## Decision and handoff

D011 resolves O003 by fixing V01–V03 version-1 observables, tolerances, fixtures,
and structural obligations before implementation. The resulting supported
validation envelope is intentionally axis-aligned vacuum propagation and a
finite closed-grid stability experiment. Oblique propagation, broadband source
accuracy, physical PEC resonances, materials, ports, and radiation remain later
work; these limitations do not permit omitting any required P1 check.

Next exact action: **FND-05 foundation gate review**. Review FND-02/03/04 evidence
and remaining decisions; run the applicable clean Debug/Release build/test
checks, preserving the known sandbox failures if repeated; record a P0 acceptance
matrix and supported limits. Only after the gate passes mark REF-01 ready.
No calendar schedule, automation, publication, or external service changed.
