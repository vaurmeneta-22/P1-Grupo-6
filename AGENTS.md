# AGENTS.md — P1 Laboratorio Estructural Digital

## Project
Laboratorio estructural digital 3D del Edificio de Ingeniería.
Curso: Métodos Computacionales (8vo semestre).
Grupo: 6

## Units
SI. Siempre: kN, m, kg, Pa, N·m. Todos los campos JSON deben tener unidades explícitas o convención global documentada.

## Structural model
- Global model: linear elastic 3D.
- 6 DOF per node.
- elasticBeamColumn for beams, columns, and equivalent walls.
- Rigid diaphragms per floor (one per floor, constrains UX, UY, RZ).
- Slabs are NOT modeled with FE.
- Floor gravity load = slab self weight + uniform finishes → q_G.
- Slab loads transferred through tributary areas (explicit, mandatory).
- RC capacity analysis (fiber sections) is SEPARATE from the global model.
- Fiber sections for M-phi and P-M curves.

## Loads
- G: gravity (slab + finishes)
- Q: live load (same tributary geometry, different intensity q_Q)
- EX: seismic lateral in X
- EY: seismic lateral in Y
- Superposition: R = λ_G·R_G + λ_Q·R_Q + λ_EX·R_EX + λ_EY·R_EY

## Architecture
- OpenSeesPy owns structural analysis.
- Unity (C#) owns visualization, preprocessing, postprocessing, interaction.
- JSON is the contract between OpenSees and Unity.
- Mobile does NOT run OpenSees in the base project (Honors: client-server reanalysis).
- AR uses AR Foundation with image tracking.

## File structure
- `opensees/` → Python scripts for analysis
- `opensees/results/` → JSON files exported from OpenSees
- `unity/` → Unity project (Assets, Scripts, Scenes)
- `data/` → Shared data files (geometry, materials, tributary areas)
- `tests/` → Verification scripts
- `scripts/` → Utility scripts
- `docs/` → Documentation and reports

## Verification rules (ALWAYS CHECK)
- Equilibrium: ΣF_applied + ΣR = 0 (tolerance < 1e-10)
- Tributary areas: Σ(transferred_loads) = q × A (tolerance < 1e-10)
- Superposition: R(A+B) = R(A) + R(B) (tolerance < 1e-10)
- IDs: every exported elementTag must exist exactly once in viewer
- Units: every JSON field must have explicit units or global convention
- Local axes: verify direction matches course convention

## Development cycle
Issue → Plan → Build → Test → Review → Merge

## What NOT to delegate without review
- Structural idealization choices
- Local axis meaning and direction
- Tributary distribution rules
- Support definitions and boundary conditions
- Capacity criteria for RC sections
- P-M interpretation
- SQ4 load distribution rule
- AR physical alignment and coordinate transforms

## Invariants
- sum(F_applied) + sum(R) = 0
- sum(transferred_loads) = q * A
- R(A+B) = R(A) + R(B)
- Every elementTag appears exactly once in viewer
- All JSON fields have explicit units
