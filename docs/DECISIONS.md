# Decision log

Recorded: 2026-09-05. Decisions below derive from the vision and the planning
baseline. They do not imply completed implementation.

## Accepted direction

| ID | Decision | Rationale and consequences | Revisit trigger |
| --- | --- | --- | --- |
| D001 | Begin with a C++20, uniform Cartesian 3D Yee FDTD CPU reference and CMake | Matches the vision; preserves a clear numerical baseline; Python supports analysis rather than hot solver loops | A documented toolchain or numerical constraint |
| D002 | Advance through evidence-based phase gates | Accuracy and reproducibility control readiness | Process revision supported by experience, without weakening numerical evidence |
| D003 | Keep solver, project data, UI, and AI separate | Solver outputs stay traceable; headless validation remains possible | Refine concrete interfaces as actual use cases appear |
| D004 | Preserve permanent analytical/reference regressions and CPU reference | Optimization requires numerical comparisons; reference provenance must be maintained | Extend the suite with every supported numerical capability |
| D005 | Use milestone-based work packages with no assumed dates, durations, or capacity | Explicit owner preference; reviews follow session, item, cycle, and phase events | Owner explicitly requests a time-based schedule |
| D006 | Keep planning and handoff records in repository Markdown | Reviewable, readable, and available to future work sessions without an external service | Team/project tooling needs justify a migration with preserved history |
| D007 | Defer detailed work breakdowns for distant phases | Early solver accuracy, reference access, and compute cost are unknown | Preceding phase passes and later work can be bounded |
| D008 | Use project-local LLVM-MinGW 20250613 / Clang 20.1.7, CMake/CTest 3.31.10, and Ninja package 1.11.1.4 | No working system C++ toolchain was found; avoids system repair and global package changes; Debug/Release scaffold checks pass | New platform, compiler issue, or CUDA host requirements |
| D009 | Start with CTest and small standalone test executables; disable fast math/contraction on Clang/GCC targets | No external C++ framework is needed for foundation checks; establishes an explicit initial floating-point policy | Numerical test complexity warrants a framework, or a documented method requires a policy revision |
| D010 | Use SI binary64 fields, six component-specific x-contiguous Yee arrays, E at integer times/H at half times, and a provisional zero-tangential-E box; default CFL fraction 0.99 with strict fraction <1 | Makes P1 storage, signs, updates, and failure behavior explicit; boundary reflects and requires isolated propagation measurements; see FND-03 method/review | Benchmark specification reveals an inconsistency, or later PEC/material/boundary phases require a documented extension |
| D011 | Fix V01–V03 version-1 benchmarks and S01–S08 structural checks before solver implementation | Compatible discrete-curl initial data and all-face dependency guards isolate native-sampled propagation/impedance; modified-energy diagnostics test closed-grid stability; see FND-04 specification/review | A documented analytical flaw or measurement limitation; preserve old limits and failed evidence before any revision |
| D012 | Use validated grid value types, integral-only counts, standard exception categories, and checked allocation/geometry limits | REF-01 rejects bad geometry and sizes before field allocation; six exact layouts remain independent of storage, CLI, and solver updates; see REF-01 contract/evidence | A supported use case requires different limits, error transport, or coordinate representation |
| D013 | Keep REF-02 field ownership fixed; expose checked sample access and const contiguous views; classify walls on the validated grid without enforcing them in storage | Prevents shape/storage mismatch and implicit large copies; coordinate and wall checks can run without field allocation; physical initialization and boundary evolution remain kernel/run responsibilities | A concrete run/checkpoint/transfer or profiled iteration requirement needs a broader owner/access API |
| D014 | Use validated vacuum time-step values and an owned source-free reference stepper with explicit initial copying, divergence/wall screening, and terminal in-place update failure | Pins constant/spacing/time conventions; protects active fields from external mutation; fails with state/component/index instead of exposing a successful partial step; independent local kernels and Fraction states validate implementation | REF-04 current/run requirements, checkpoint needs, or measured performance/representability limits justify a documented extension |
| D015 | Use validated sparse impressed currents, native probes, separate fixed benchmark runners and streamed CSV/JSON with exclusive completion markers | Preserves initial rho=0 screening, defines later charge by continuity, retains failed evidence and distinguishes raw completion from physical acceptance; see REF-04 contract/evidence | General project/source/charge requirements or measured resource constraints |

## Open decisions

Resolve each choice by its need-by point. Record options, selected approach,
numerical implications, validation plan, and maintenance consequences. Routine
choices can be made during authorized implementation; ownership here identifies
responsibility rather than introducing approval requirements.

| ID | Question | Need by | Responsible role / next step |
| --- | --- | --- | --- |
| O005 | Which source-control host, license, and CI environment should be used? | External hosting/distribution; CI selection | Project owner sets distribution intent; collaborator evaluates relevant dependencies |
| O006 | Which trusted reference solver/data are accessible, reproducible, and suitable for dipole/patch comparisons? | P4/P6 benchmark specifications | Collaborator inventories accessible references; owner resolves access needs |
| O007 | Which absorbing boundary formulation and supported test envelope will be used? | P3 implementation | Collaborator: method/reference study after P2 gate |
| O008 | Which persistent project schema and large-result format should be used? | Persistent benchmark/user project implementation, no later than P6 | Collaborator: evaluate reproducibility, versioning, partial reads, and data sizes |
| O009 | Which CAD/UI/rendering dependencies are justified? | P10/P11 | Collaborator: evaluate Qt/OpenCASCADE/VTK or alternatives against measured needs and licensing |
| O010 | What CPU/GPU hardware and memory budgets should performance phases target? | P8/P9 planning | Collaborator records measurements; owner supplies target hardware priorities |

Add new decisions when needed. Do not preselect every long-term library during
foundation work.

O001 was resolved by D008/D009 on 2026-09-05. See
[environment observations](ENVIRONMENT.md) and [build evidence](validation/FND-02-build.md).
The local toolchain selection did not settle numerical conventions, benchmark
tolerances (O003), or future CUDA host compatibility.

FND-05 reviewed the remaining open decisions on 2026-09-06: none is due before
P1. The [P0 gate record](validation/FND-05-foundation-gate.md) accepts the
foundation and makes REF-01 ready under D001–D011, without changing architecture
or tolerances. The same-author review and approved-execution limitations remain
explicit; no new numerical capability is claimed.

## D010 detail — O002 resolved on 2026-09-05

Status: accepted for the reference specification, not numerically validated.
See [method note](methods/FND-03-yee-conventions.md) and
[author review](validation/FND-03-review.md).

Considered common padded arrays versus exact per-component extents; x versus z
contiguous storage; an initially reflecting box versus early periodic/absorbing
boundaries; and equality versus a strict CFL limit. Choose exact component
extents with explicit update ranges to expose staggering and avoid ghost reads.
X-contiguous storage fixes a simple scalar iteration order without claiming a
performance advantage. Binary64 follows the verified toolchain capability and
provides the reference precision for later backend comparisons.

Choose the reflecting closure to bound the initial stencil without expanding
P1 into an absorbing or periodic boundary implementation. Physical PEC validation
still belongs to P2; open-domain capability belongs to P3. The cost is that
FND-04 must demonstrate boundary isolation, including transverse faces and
initial-field mismatch. Normal H starts at zero on the walls and remains there
under the tangential-E constraint; other unconstrained samples evolve normally.

Choose strict dt<dt_max with default 0.99 of the unequal-spacing vacuum bound;
this avoids the marginal equality case without asserting accuracy. Reserve
positive-time phasors and negative-exponent forward transforms; pin a consistent
2022 CODATA vacuum constant set. Validate the mathematical and input contracts
before optimizing or extending them. O003 remains open for FND-04.

## D011 detail — O003 resolved on 2026-09-05

Status: accepted for version-1 reference validation; no achieved accuracy claim.
See [specification](validation/FND-04-reference-benchmarks.md) and
[author review](validation/FND-04-review.md).

Considered unmodified plane-wave initial fields, early periodic/absorbing
boundaries, and a finite compatible curl fixture. Choose the curl fixture with
a zero collar and explicit dependency guards on every face. This preserves
FND-03's initial boundary/divergence constraints and P1 scope. Its cost is a
larger 3D volume and a short measurement window; an enlarged-domain check must
verify its implementation. The finest mesh requires 489.380 MiB for fields;
serial execution and streamed output fit a 2 GiB working-memory budget.

Choose spatial harmonic fits at native locations/times, with temporal phase
advance measured from initial/final E fits and signed complex impedance shifted
using that measured frequency. This avoids a temporal FFT dependency before
MAT-04, fixes signal-floor behavior, and separates continuum dispersion from
discrete implementation error. The three-mesh continuum tolerances follow the
independent h^2 dispersion budget; all six axis/polarization combinations and
time-step/domain/mesh-shape sensitivity are required.

Choose the positive staggered modified-energy invariant for long-time lossless
tests, backed by the finite-grid curl adjoint identity. A naive mixed-time
squared-field norm can oscillate in a stable run; retain it as a bounded
diagnostic instead of requiring monotonicity. Both initial and finite-current
excitations are specified; physical feed/PEC/radiation validation stays in later
phases. Same-author review is explicit. FND-05 still must close the foundation
gate before REF-01, and all physical/structural production checks remain pending.

## D012 detail — REF-01 API decisions on 2026-09-06

Status: implemented and structurally checked on Windows x64; no validated physics.
See [core grid contract](methods/REF-01-core-grid-contract.md) and
[evidence](validation/REF-01-core-grid.md).

Considered permissive unsigned aggregate inputs versus validated integral
construction, and allocating fields immediately versus checking metadata first.
Choose integral-only counts with pre-conversion negative/range checks and const
grid accessors. This prevents accidental floating truncation at the core API
while leaving malformed-text handling with the future CLI. Keep field storage
in REF-02 so all six extents, products, and total bytes can be checked without
allocation. Invalid input uses invalid_argument, size/budget failures use
length_error, and nonrepresentable geometry uses overflow_error; no general
error framework or solver/backend interface is introduced.

Use the real vector<double> per-component limit, optionally lowered by the
caller, plus an aggregate byte cap. Neither default arithmetic limits nor a
passing grid promise available RAM. REF-04 still must account for diagnostic
and fixture overhead under its 2 GiB working-memory budget. Require exact
half-grid indices through N and a conservative coordinate-spacing guard.
Resolvable subnormal geometry is accepted, but coefficients, CFL, and time
representability remain separate REF-03/04 checks. These choices add no
stability or accuracy claim and do not alter the FND-04 acceptance thresholds.

## D013 detail — REF-02 storage decisions on 2026-09-07

Status: implemented and structurally checked on Windows x64; no validated physics.
See [storage contract](methods/REF-02-field-storage-contract.md) and
[evidence](validation/REF-02-field-storage.md).

Considered exposing resizable vectors, generic field/backend abstractions, and
a fixed owner with checked sample access. Choose the fixed owner with six exact
vector<double> arrays, a private grid value, mutable/const at, and const spans.
Disable copy/move/assignment for now so grid/storage correspondence and borrowed
reference lifetime cannot be broken by partial assignment or moved-from arrays.
This avoids implicit large field copies. Transfer/checkpoint semantics can be
specified when a concrete run requirement appears; no backend framework is added.

Put checked positions, offsets, and wall predicates on UniformGrid so metadata
inspection does not allocate fields. Bounds plus the already checked extent
products prove safe offset arithmetic. Every access pays a component/bounds
check in this reference API; performance work requires later profiling and
validation. Coordinates are deterministic binary64 geometry calculations.

Wall predicates classify without zeroing. Raw storage permits writes needed by
local structural fixtures; a future public run must separately reject invalid
initial conditions and enforce the provisional boundary during evolution.
Zero allocation is not divergence, stability, or physical PEC validation. The
S01 access and S02 classification tests pass; actual kernel evolution remains
REF-03. No fixed numerical tolerance or phase gate changed.

## D014 detail — REF-03 stepping decisions on 2026-09-07

Status: implemented with passing equation-level/structural checks on Windows x64.
No physical propagation, impedance, or stability benchmark is claimed. See the
[contract](methods/REF-03-reference-update-contract.md) and
[evidence](validation/REF-03-reference-updates.md).

Considered borrowed mutable fields versus explicit copying into an owned stepper,
and transactional full-field copies versus in-place updates with a failed state.
Choose one explicit initial copy, const field inspection, and complete H then E
family updates. This retains REF-02's fixed owner and prevents external initial
edits from altering a run. Initial construction costs two payloads temporarily;
release fixtures before integration and count this in REF-04's memory budget.
Avoid a field-size rollback copy per step. A failed step is terminal, state does
not advance, and fields/time accessors reject. Previously borrowed views must be
discarded after an exception; C++ cannot revoke them. The error carries the
input state, component, and index. No output writer exists in REF-03.

Initial public states are finite, zero on tangential E/normal H walls, and pass
the declared source-free divergence screening. This API currently represents
rho=0 and J=0; local algebra harnesses can still exercise incompatible affine/
polynomial data through internal kernels. REF-04 must specify current/charge
continuity rather than repurpose unrestricted field writes as a source.

Use the scaled unequal-spacing CFL formula, strict q/dt rejection, checked
binary64 coefficients, and multiplication-derived native times. Reject extreme
inputs whose selected evaluation is not representable even if an alternative
scaling could evaluate them. Retain straightforward divided differences and
checked field accesses; optimize only after physical validation and profiling.

S01–S05 and the source-free part of S06 pass. A separate Fraction axis-permutation
oracle fixes every small-grid half-stage without using production results.
The existing method/threshold records remain unchanged. C02's structural/CFL
review passes; C03/P1 remain open for run facilities and physical measurements.

## D015 detail — REF-04 source and run decisions on 2026-09-10

Status: implemented with structural and end-to-end smoke evidence. See the
[run contract](methods/REF-04-run-contract.md) and
[REF-04 evidence](validation/REF-04-reference-runs.md). Same-author review.

Considered arbitrary mutable field injection, a general source hierarchy, and
a validated sparse current shape. Choose the shape plus a half-time amplitude:
it supports the prescribed V03 pulse without allowing mutation of active fields
or adding a port framework. Preserve rho=0 initialization; later charge follows
discrete continuity, with no stored charge/projection. Initial copying and
terminal update failure remain D014's policy. Count both field payloads and the
source capacity in the 2 GiB run budget.

Keep benchmark generators/diagnostics in a separate library from the solver.
They use independently transcribed permutation differences, with no production
curl calls. Generate compact potentials on demand to avoid extra volumes.
Expose raw signed probes at native coordinates/times; independent Python fits
test the estimator before REF-05 applies it to physical benchmark outputs.

Use built-in v1 suites and an explicitly named smoke subset. Only smoke accepts
step overrides, and its dependency guard still applies. This is a benchmark
artifact format, not the persistent user-project decision O008. Refuse existing
directories; preserve partial files on failure; close all data/metadata before
renaming the temporary completion marker. A complete raw artifact is not a
physical pass. Record source-content fingerprint, compiler, CPU identifier,
units, configuration, fixture checks, memory budget and elapsed time.

Revisit for a real general-run/project requirement, charge observable, source
performance bottleneck, or measured full-suite resource issue. No v1 numerical
threshold, phase sequence, or physical accuracy claim changed.
