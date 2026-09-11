# Development routines

## Session routine

1. Read the vision, current backlog/handoff, and active phase gate. Inspect the
   current repository state so existing user work is preserved.
2. Select the first ready item or follow the owner's explicit priority. State the
   intended result and the evidence that will establish completion.
3. Check the numerical specification before implementation. If it is missing,
   create it first; an unresolved numerical assumption is work to investigate.
4. Make a focused change, compile, and run applicable checks. Keep failures visible.
5. Update the item's state and evidence. End with what changed, what was tested,
   unresolved limitations, and the exact next action.

Do not advance automatically into a large unrelated feature merely because one
item finished. Continue within the user's authorized scope and active phase.

## Numerical feature routine

For each significant electromagnetic change:

1. Identify the physical quantity and governing equations.
2. Consult trusted primary references or established numerical-method texts;
   record exact sources and which parts of the method they support.
3. Derive or verify the discretization, spatial/time placement, units, sign and
   transform conventions, boundary treatment, and supported material assumptions.
4. Document stability, expected error mechanisms, and memory/runtime implications.
5. Specify an independent analytical or reference benchmark and justify its
   acceptance thresholds before using candidate solver outputs to judge success.
6. Implement the simplest correct reference version.
7. Run structural tests, physical comparisons, and sensitivity/convergence checks.
8. Investigate failures. Change a tolerance only for a documented physical or
   measurement reason, preserve the old result, and review the impact.
9. Record validated scope and add the benchmark to the permanent regression suite.
10. Optimize only after this evidence exists; compare optimized backends with the
    reference and physical benchmarks.

## Build and test routine

Phase 0 establishes and records the actual commands in the root README. Do not
document an unverified command as working. The intended route is CMake presets
for configure/build and CTest for execution, with Python for independent analysis
where useful.

- On each coherent code change: build affected targets and run relevant tests.
- On a numerical feature completion: run the fast suite and affected numerical
  benchmarks, including prior cases that exercise the modified subsystem.
- At a gate or release: run the full applicable validation set from a clean build.
- Split fast checks and long benchmarks so runtime is explicit. Introduce CI when
  a repository host is selected; introduce scheduled long runs only when configured.
- Record environment, commands, pass/fail/skipped status, errors, and relevant
  runtime. A skipped check is not a pass.

## Evidence and source control

Keep changes reviewable and group related implementation, tests, and method notes.
GitHub is the selected source-control and CI host. Repository hosting, licensing,
and public distribution remain separate choices; a configured remote is not itself
authorization to publish releases or change repository visibility.

Use stable benchmark IDs. Store small inputs and reference provenance with the
case; keep large generated arrays out of source control. Evidence reports identify
the code revision, or an explicitly described local snapshot if no revision exists.
Document regeneration commands and reference checksums where appropriate.

For every important result, preserve enough metadata to reproduce it: geometry,
materials, units, mesh, time step, duration, source/port, boundaries, sampling,
post-processing conventions, backend, and environment.

## Templates

### Work item

```markdown
ID / title:
Phase / status / responsible role:
Problem and intended behavior:
Dependencies:
In scope / deferred scope:
Method note and references:
Stability, accuracy, and performance implications:
Acceptance criteria and independent comparison:
Build/test commands:
Evidence links:
Unresolved issues:
Next action:
```

### Phase review

```markdown
Phase / date / code revision:
Reviewer and independence limitations:
Required deliverables:
Acceptance matrix (criterion, measured result, evidence, pass/fail):
Previous regression results:
Convergence and sensitivity evidence:
Known limits and unresolved failures:
Decision: pass / continue work / blocked
Reason:
Next-phase ready items and revised sequence:
```

A failed required criterion means the gate remains open. A change to phase scope
must be recorded explicitly, with its effect on downstream capability claims.

### Session handoff

```markdown
Date / active item:
Completed changes:
Checks and results, including skipped checks:
Evidence links:
Open issues or decisions:
Next exact action:
Schedule impact:
```

### Decision record

```markdown
ID / date / status:
Question and context:
Options considered:
Decision and rationale:
Numerical, stability, performance, and maintenance consequences:
Validation implications:
Revisit trigger:
```
