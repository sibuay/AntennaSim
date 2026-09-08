# Project: AI-Native Antenna Simulation and Design Software

I want to build a professional antenna simulation and design application inspired by CST Studio Suite, HFSS, and open-source electromagnetic solvers, but focused exclusively on antenna engineering.

The goal is NOT to create a full general-purpose electromagnetic simulation suite or to copy CST feature-for-feature. The goal is to build a modern, specialized, AI-native antenna engineering environment that combines:

- full-wave electromagnetic simulation,
- antenna-oriented CAD and geometry tools,
- intelligent meshing,
- automated simulation setup,
- optimization,
- engineering interpretation,
- and an AI-assisted design workflow.

The software should eventually be capable of serious engineering use for designing and analyzing antennas such as:

- dipoles,
- monopoles,
- patch antennas,
- microstrip antennas,
- Yagi-Uda antennas,
- LPDA antennas,
- helices,
- horn antennas,
- antenna arrays,
- wire antennas,
- PCB antennas,
- and other common RF antenna structures.

The project can take a long time. Development speed is not the primary constraint. Correctness, maintainability, numerical validation, and a strong architecture are more important than quickly producing a demo.

---

# Core Philosophy

CST should be treated as a reference for:

- electromagnetic simulation capabilities,
- professional antenna workflows,
- expected engineering outputs,
- solver validation,
- meshing concepts,
- boundary conditions,
- ports,
- post-processing,
- and visualization.

However, the application should NOT blindly reproduce CST's user experience.

The objective is to rethink antenna simulation as if such a tool were designed today around automation, optimization, and AI.

The fundamental distinction should be:

Traditional workflow:

Geometry → Materials → Ports → Mesh → Solver → Results

Our preferred workflow:

Engineering Goal → Intelligent Setup → EM Solver → Validation → Interpretation → Optimization → Improved Design

The user must still be able to access all low-level simulation controls in an Expert Mode.

---

# Critical Architectural Rule

The AI must NEVER replace the electromagnetic solver.

The architecture must strictly maintain:

AI != Physics Solver

Quantities such as:

- S-parameters,
- S11,
- impedance,
- VSWR,
- electric fields,
- magnetic fields,
- surface currents,
- radiation patterns,
- gain,
- realized gain,
- directivity,
- efficiency,
- radiated power,

must always come from numerical electromagnetic calculations.

The AI layer may:

- generate geometry,
- recommend solver settings,
- configure simulations,
- inspect geometry,
- detect likely setup mistakes,
- select appropriate solvers,
- interpret results,
- propose design changes,
- define optimization variables,
- orchestrate simulations,
- compare results,
- and explain electromagnetic behavior.

It must never fabricate numerical simulation results.

---

# Target Capability Level

The long-term target is approximately a serious Level-3 antenna engineering tool.

This means the system should eventually include:

- a validated 3D full-wave solver,
- FDTD,
- later a Method of Moments solver,
- nonuniform meshing,
- automatic mesh generation,
- local mesh refinement,
- CPU parallelization,
- GPU acceleration,
- professional antenna CAD,
- dielectric and conductive materials,
- ports and excitations,
- absorbing boundaries,
- S-parameter extraction,
- near-field calculation,
- far-field transformation,
- antenna radiation metrics,
- parameter sweeps,
- automatic optimization,
- professional 2D and 3D visualization,
- project management,
- import/export capabilities,
- and extensive numerical regression testing.

It is NOT necessary to compete with CST in:

- multiphysics,
- thermal simulation,
- particle simulation,
- EMC,
- motors,
- transformers,
- arbitrary industrial electromagnetic problems,
- every possible solver type,
- distributed supercomputer solving,
- or decades of specialized legacy features.

Stay focused on antenna engineering.

---

# Phase 1 Solver Strategy

The first electromagnetic solver should be a 3D FDTD solver using a Yee grid.

Start simple and correct.

Initial solver functionality should include:

- 3D Cartesian Yee grid,
- Ex, Ey, Ez,
- Hx, Hy, Hz,
- arbitrary dx, dy, dz,
- Courant stability handling,
- PEC boundaries,
- free-space propagation,
- dielectric materials,
- conductivity,
- dielectric loss,
- sources,
- field probes,
- Fourier transforms,
- lumped/discrete ports,
- S11 extraction,
- input impedance,
- CPML or another high-quality absorbing boundary,
- near-field recording,
- near-field to far-field transformation,
- gain,
- directivity,
- radiation efficiency.

The first versions may use a uniform grid.

Later introduce:

- nonuniform Cartesian meshing,
- geometry-aware refinement,
- local refinement around feed regions,
- wavelength-based mesh constraints,
- dielectric-aware refinement,
- automatic convergence testing.

---

# Solver Validation Is a First-Class Feature

Numerical correctness is more important than GUI development.

Every major solver capability must be validated.

Build a permanent automated validation suite.

Examples include:

## Free-Space Plane Wave

Validate:

E/H ≈ 376.73 ohms

Verify:

- propagation speed,
- numerical dispersion,
- amplitude behavior.

## PEC Resonant Cavity

Compare simulated resonant frequencies against analytical cavity mode equations.

## Half-Wave Dipole

Compare:

- resonance,
- input impedance,
- radiation pattern,
- directivity,
- gain,

against analytical theory and trusted reference solvers.

## Patch Antenna

Use a standard rectangular microstrip patch antenna as a benchmark.

Compare against:

- analytical estimates,
- CST,
- openEMS,
- or other trusted numerical solvers.

## Horn Antenna

Validate:

- radiation pattern,
- gain,
- beamwidth,
- impedance behavior where applicable.

All benchmarks should become regression tests.

A new feature must not silently degrade existing solver accuracy.

Where practical, define numerical acceptance criteria such as:

- resonance frequency error,
- impedance error,
- gain error,
- field error,
- convergence behavior.

---

# Future Solver Architecture

The software should support multiple solvers through a common abstraction.

Possible structure:

ISolver

- FDTDSolver
- MoMSolver
- future solvers if justified

The user should be able to choose:

- Automatic
- FDTD
- MoM

Automatic should eventually inspect the model and recommend an appropriate solver.

For example:

Patch antenna with dielectric substrate:
→ Prefer FDTD

Large wire antenna / Yagi / LPDA:
→ Prefer MoM

The application should explain why it selected a solver.

Do not implement unnecessary solvers until FDTD is reliable.

---

# Method of Moments

After the FDTD implementation is stable, add a MoM solver primarily for wire and conducting-surface antennas.

Eventually investigate:

- triangular surface meshes,
- RWG basis functions,
- Green's functions,
- impedance matrix construction,
- excitation vectors,
- iterative solvers,
- GMRES,
- preconditioning,
- far-field calculation.

Do NOT make MLFMM an early requirement.

MLFMM can be considered much later if large MoM problems justify it.

---

# Performance

The numerical core should ultimately be written for high performance.

Preferred long-term technology direction:

- C++20 or newer for the solver core,
- OpenMP or another suitable CPU parallelization system,
- CUDA for NVIDIA GPU acceleration,
- Eigen or another appropriate numerical library where useful,
- CMake for builds.

Python may be used for:

- prototyping,
- analytical validation,
- plotting,
- test generation,
- numerical comparison,
- research scripts.

Do not keep performance-critical solver loops in Python.

The architecture should allow CPU and GPU backends.

Example:

FDTD Backend

- CPU scalar reference implementation
- CPU multithreaded implementation
- CUDA implementation

The reference implementation should prioritize clarity and correctness.

Optimized implementations must be numerically checked against it.

---

# Geometry and CAD

The application eventually needs antenna-oriented 3D CAD.

Required primitives may include:

- box,
- rectangle,
- polygon,
- cylinder,
- sphere,
- wire,
- sheet,
- extrusion.

Operations:

- translate,
- rotate,
- scale,
- mirror,
- duplicate,
- Boolean union,
- Boolean subtract,
- intersection if needed.

Possible geometry engine:

OpenCASCADE or another robust CAD kernel.

Do not build a complete CAD kernel from scratch unless necessary.

The CAD system should support parameterized geometry.

---

# Semantic Antenna Geometry

A key feature should be that the application understands engineering meaning, not just geometric primitives.

Traditional CAD sees:

- rectangles,
- boxes,
- cylinders,
- wires.

Our software should additionally support semantic antenna structures such as:

PatchAntenna

- patch
- substrate
- ground
- feed

YagiAntenna

- reflector
- driven element
- directors

LPDA

- elements
- boom
- feed
- scale factor
- spacing factor

HornAntenna

- throat
- flare
- aperture
- waveguide section

This enables AI-assisted engineering.

For example, if the user asks:

"Increase the gain of this Yagi without making it longer than 700 mm."

The system can reason in terms of:

- number of directors,
- director spacing,
- element lengths,

instead of blindly deforming arbitrary geometry.

---

# Materials

Support at minimum:

- PEC,
- finite conductivity metals,
- isotropic dielectrics,
- relative permittivity,
- relative permeability,
- conductivity,
- loss tangent.

Eventually include a material database.

Common examples:

- vacuum,
- air,
- copper,
- aluminum,
- FR4,
- Rogers substrates.

Keep the material system extensible.

---

# Ports and Excitations

Start with a reliable lumped/discrete port.

Later consider:

- coaxial excitation,
- waveguide ports,
- microstrip ports,
- plane-wave excitation,
- voltage/current sources.

Ports are numerically sensitive and must be treated as a major subsystem, not as a minor UI feature.

Do not add many port types before the basic one is fully validated.

---

# Mesh System

The mesh is one of the most important parts of the software.

Long-term goals:

- automatic mesh generation,
- wavelength-based sizing,
- material-aware sizing,
- geometry-aware refinement,
- local refinement,
- feed-gap refinement,
- thin-substrate handling,
- edge refinement,
- nonuniform grid spacing,
- convergence testing.

The program should identify problematic regions.

Example:

"Feed gap is 0.4 mm while the local mesh cell size is 1.2 mm. The feed is under-resolved."

It should be able to recommend or automatically apply a refinement.

---

# Intelligent Simulation Audit

Before a simulation begins, create a Simulation Audit system.

It should inspect the project for potential problems such as:

- disconnected feed,
- invalid geometry,
- overlapping solids,
- undefined materials,
- missing port,
- misplaced port,
- inadequate mesh,
- insufficient cells across thin substrates,
- absorbing boundary too close,
- invalid frequency range,
- frequency range not covering predicted resonance,
- excessive memory usage,
- extremely small features causing mesh explosion,
- poor numerical stability.

Example output:

Simulation Audit

✓ Geometry valid
✓ Material definitions complete
✓ Port connected

Warning:
PML boundary is only 0.08 wavelength from the radiator.

Warning:
Only 2 cells exist through the substrate thickness.

Estimated RAM:
14.2 GB

Estimated GPU VRAM:
9.8 GB

This system should combine deterministic engineering checks with AI explanations.

Critical warnings must come from deterministic checks whenever possible.

---

# Automatic Solver Selection

The application should eventually analyze:

- geometry type,
- electrical size,
- amount of dielectric material,
- wire vs surface structure,
- required frequency bandwidth,
- expected memory use,

and recommend the best available solver.

Example:

Recommended Solver: MoM

Reason:
The model consists primarily of conducting wires and contains very little dielectric volume. MoM is expected to require substantially less memory than volumetric FDTD.

Users must still be able to override the recommendation.

---

# Automatic Mesh Convergence

The application should support automatic convergence workflows.

Example:

Simulation 1
→ analyze result

Refine mesh

Simulation 2
→ compare resonance and S11

Refine mesh

Simulation 3
→ compare again

Stop when change is below tolerance.

Possible convergence metrics:

- resonant frequency,
- S11,
- impedance,
- gain,
- stored energy,
- far-field metrics.

The user should be able to see the convergence history.

---

# Engineering Results

The software should calculate and display:

## Network Results

- S11,
- eventually multi-port S-parameters,
- VSWR,
- return loss,
- input impedance,
- resistance,
- reactance.

## Field Results

- E-field magnitude,
- H-field magnitude,
- vector fields,
- field slices,
- phase,
- animations when useful.

## Current Results

- conductor current,
- surface current density,
- current phase.

## Radiation Results

- 2D radiation patterns,
- 3D radiation pattern,
- directivity,
- gain,
- realized gain,
- radiation efficiency,
- total efficiency,
- beamwidth,
- front-to-back ratio,
- polarization,
- axial ratio where applicable.

The internal post-processing architecture should be modular.

---

# Engineering Interpretation Layer

The software should not only show graphs.

It should explain results.

Example:

"Resonance occurs at 2.39 GHz while the design target is 2.45 GHz.

The dominant current distribution indicates that the effective electrical length is too large.

Reducing the patch length is likely to shift resonance upward."

The user should be able to ask questions such as:

- Why did resonance move?
- Why is S11 poor?
- Why did gain decrease?
- Where is the dominant current mode?
- Is the mesh converged?
- Is the feed position causing mismatch?
- Which dimension most strongly controls resonance?
- Why is cross-polarization high?

The AI should use actual simulation data and project metadata as context.

It must clearly distinguish:

- verified simulation result,
- deterministic calculation,
- engineering inference,
- AI hypothesis.

---

# Optimization

Optimization should be a central capability.

Support parameterized geometry from the beginning.

Potential optimization methods:

- parameter sweep,
- grid search,
- gradient-free methods,
- CMA-ES,
- genetic algorithms,
- Bayesian optimization.

Example goal:

Frequency:
2.45 GHz

Constraints:
S11 < -20 dB
Gain > 5 dBi
Board width <= 60 mm
Board height <= 60 mm

Variables:
patch length
patch width
feed position

The optimizer should run simulations, evaluate objectives, and iteratively modify parameters.

Optimization history must be preserved.

---

# AI-Guided Design Mode

The program should eventually support two main workflows.

## Expert Mode

For experienced RF engineers.

Full access to:

- geometry,
- materials,
- ports,
- mesh,
- boundaries,
- solver,
- monitors,
- post-processing,
- optimization settings.

## Guided Design Mode

The user describes the engineering problem in natural language.

Example:

"Design a 2.45 GHz rectangular patch antenna on 1.6 mm FR4. Maximum board size is 60 × 60 mm. Use a 50-ohm feed. Target realized gain is above 5 dBi and S11 below -20 dB."

The system should:

1. parse the engineering requirements,
2. estimate an initial antenna geometry,
3. create materials,
4. place the feed,
5. define the simulation domain,
6. choose a solver,
7. generate a mesh,
8. run the simulation,
9. evaluate the results,
10. propose or automatically perform optimization.

The user must be able to inspect and modify everything generated by the AI.

---

# Design Intent

Every parameterized antenna project should be able to preserve design intent.

Example:

Target frequency:
2.45 GHz

Target impedance:
50 ohms

Minimum gain:
5 dBi

Maximum size:
60 × 60 × 10 mm

Substrate:
FR4

Optimization parameters:
patch_length
patch_width
feed_x

This information should remain part of the project and influence:

- simulation audits,
- AI recommendations,
- optimization,
- result interpretation.

---

# Result Comparison

Allow the user to compare simulations.

Example:

Baseline
vs
Iteration 12

Compare:

- geometry changes,
- S11,
- resonance,
- impedance,
- gain,
- efficiency,
- radiation pattern.

The software should make optimization evolution visually understandable.

---

# Project File Architecture

Use a clear human-readable project description where possible.

For example:

JSON or YAML for:

- geometry definitions,
- materials,
- ports,
- solver configuration,
- mesh settings,
- design goals,
- optimization variables.

Large numerical results should use efficient binary formats.

Project files should be versioned.

Never make file compatibility depend entirely on internal C++ object serialization.

---

# Suggested High-Level Architecture

A possible architecture:

Application
│
├── UI
│
├── AI Assistant
│
├── Project Model
│
├── Geometry Engine
│
├── Material System
│
├── Mesher
│
├── Simulation Audit
│
├── Solver Interface
│ ├── FDTD
│ └── MoM
│
├── Compute Backends
│ ├── CPU
│ └── CUDA
│
├── Post Processing
│
├── Optimization Engine
│
├── Visualization
│
└── Validation Framework

Keep subsystems loosely coupled.

Do not allow GUI code to contain electromagnetic solver logic.

---

# Testing Philosophy

Testing must be built into the architecture from the beginning.

Required categories:

- unit tests,
- numerical tests,
- analytical benchmark tests,
- solver regression tests,
- geometry tests,
- serialization tests,
- GPU-vs-CPU consistency tests,
- mesh convergence tests.

When implementing a new electromagnetic feature:

1. define the physical expectation,
2. define a benchmark,
3. implement the simplest correct version,
4. validate it,
5. optimize only after validation.

Never optimize an unvalidated solver.

---

# Development Priorities

Use this order unless there is a strong engineering reason to deviate.

Priority 1:
Correct electromagnetic solver.

Priority 2:
Validation framework.

Priority 3:
Reliable ports, boundaries, and materials.

Priority 4:
Post-processing.

Priority 5:
Meshing.

Priority 6:
Performance.

Priority 7:
CAD and GUI.

Priority 8:
AI automation.

Priority 9:
Advanced optimization and additional solvers.

Do not spend months building a beautiful interface around an unverified solver.

---

# Initial Development Milestones

## Milestone 1

Create a minimal repository and architecture.

Implement:

- CMake project,
- core mathematical types,
- grid,
- field storage,
- basic FDTD update loop,
- simple source,
- basic output,
- tests.

Goal:

Demonstrate stable electromagnetic propagation in free space.

---

## Milestone 2

Add:

- PEC,
- dielectric materials,
- conductivity,
- boundary handling,
- field probes,
- FFT.

Validate simple analytical cases.

---

## Milestone 3

Implement high-quality absorbing boundaries such as CPML.

Measure numerical reflection.

Create automated boundary tests.

---

## Milestone 4

Implement a lumped/discrete antenna port.

Calculate:

- voltage,
- current,
- impedance,
- S11.

Validate against simple antennas.

---

## Milestone 5

Implement near-field and far-field processing.

Calculate:

- radiation pattern,
- directivity,
- gain,
- efficiency.

Validate a dipole.

---

## Milestone 6

Validate a microstrip patch antenna against trusted reference data.

At this point, the project becomes a basic real antenna simulator.

---

## Milestone 7

Add nonuniform meshing and automatic refinement.

---

## Milestone 8

Add multithreaded CPU solving.

---

## Milestone 9

Add CUDA acceleration.

Keep the CPU reference implementation permanently available.

---

## Milestone 10

Add a desktop GUI.

Possible technology:

Qt 6.

Features:

- project tree,
- 3D viewport,
- geometry editor,
- properties panel,
- simulation controls,
- result plots.

---

## Milestone 11

Add professional visualization.

Possible technology:

VTK or a suitable modern rendering layer.

Support:

- 3D geometry,
- fields,
- surface currents,
- radiation patterns,
- mesh visualization.

---

## Milestone 12

Add parameter sweeps and optimization.

---

## Milestone 13

Begin development of a MoM solver.

---

# Coding Standards

The codebase should prioritize:

- clarity,
- modularity,
- strong typing,
- documentation,
- deterministic behavior,
- numerical stability,
- testability,
- profiling.

Avoid giant classes.

Prefer clearly defined interfaces between:

- geometry,
- mesh,
- solver,
- results,
- visualization.

Document electromagnetic equations and numerical assumptions near their implementation.

Where formulas come from published numerical methods, record the source in documentation.

---

# Scientific Development Rules

For electromagnetic algorithms:

Do not guess.

Before implementing:

1. identify the governing equations,
2. derive or verify the discretization,
3. identify assumptions,
4. identify numerical stability requirements,
5. design a validation test,
6. then implement.

For difficult components such as:

- CPML,
- port extraction,
- dispersive materials,
- NF2FF,
- nonuniform grids,
- RWG MoM,

use trusted papers, textbooks, and established open-source implementations as references.

Do not copy code blindly.

Understand the mathematics and reimplement it cleanly.

---

# Development Behavior Expected from Codex

Act as a senior numerical electromagnetics software engineer.

Do not treat this project as a normal CRUD application.

For every significant technical decision:

- explain the numerical implications,
- identify possible stability problems,
- identify accuracy risks,
- identify performance implications,
- propose validation methods.

When writing code:

- keep changes focused,
- compile frequently,
- run tests,
- create tests for new numerical features,
- avoid unnecessary abstractions,
- avoid premature optimization.

If an implementation fails validation, prioritize investigating the physics or numerical method rather than hiding the error.

When uncertainty exists, state it explicitly.

---

# Long-Term Product Vision

The final product should feel like a modern antenna engineering environment rather than merely a small CST clone.

A user should eventually be able to write:

"Design a compact 915 MHz PCB antenna for LoRa on an 80 × 40 mm FR4 board. Reserve the upper 20 mm for the antenna. Maximize realized gain while maintaining S11 below -10 dB from 902 to 928 MHz."

The software should then be able to:

- understand the constraints,
- generate a reasonable initial topology,
- construct the simulation,
- audit it,
- select the solver,
- mesh it,
- simulate it,
- analyze the results,
- optimize the geometry,
- compare iterations,
- and explain the final design.

At every stage, the engineer must remain able to inspect, override, and verify the system.

The ultimate principle of this project is:

Use AI to reduce the effort required to perform electromagnetic engineering.

Do not use AI to replace electromagnetic engineering.
