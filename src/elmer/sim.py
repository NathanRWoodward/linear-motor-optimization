"""Elmer .sif generator.

This is the second half of the pipeline:

    build123d CAD -> STEP -> gmsh (meshing.Mesher) -> Elmer (this module)

The gmsh `meshing.Mesher` walks the STEP entities, matches each to a material
and a set of tags (parsed from the build123d part names), and creates one gmsh
*physical group* per (material, tags) combination. Each group is recorded as a
`meshing.generator.PhysicalGroup` carrying:

    - the integer gmsh id   (Elmer targets bodies by this id),
    - the compound name     (MATERIAL_TAG1_TAG2, shared verbatim with Elmer),
    - the resolved material  (-> Elmer Material via MaterialProperties.to_elmer),
    - the resolved EntityTags (-> per-region boundary/body-force overrides).

This module consumes exactly that record set plus the same `MeshingConfig`, so
the Elmer bodies line up one-to-one with the mesh by id and by name. Nothing is
hardcoded per geometry: materials, bodies and magnet body-forces are all derived
from the config, mirroring the way the gmsh generator derives its physical
groups.

Currently fully wired: 3D magnetostatics of permanent magnets (WhitneyAVSolver +
MagnetoDynamicsCalcFields). The thermal / electrostatic / current solvers are
scaffolded in SOLVER_LIBRARY and SIMULATION_LIBRARY and can be selected by
passing a different `physics=` to the Generator; their body/boundary wiring is
marked with SCAFFOLD where it still needs project-specific decisions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from elmer.physics import Physics
from meshing.config import MeshingConfig, conditions_for
from physical.conditions import ConditionTarget, Magnetization
from physical.materials.properties import MaterialProperties
from physical.units import U, Quantity
import pyelmer.elmer as elmer

if TYPE_CHECKING:
    # Imported only for type checking: the real module pulls in gmsh, which we
    # don't want at import time (and which pure-logic tests can't load).
    from meshing.generator import PhysicalGroup


# ---------------------------------------------------------------------------
# Simulation / solver "library".
#
# pyelmer normally loads these from yaml (load_simulation / load_solver). We keep
# them inline as plain dicts so the whole CAD->mesh->sif pipeline is driven by
# one Python config with no scattered yaml files. The dicts are copied verbatim
# into pyelmer objects, so the keys/values are exactly Elmer sif syntax.
# ---------------------------------------------------------------------------

SIMULATION_LIBRARY: dict[str, dict] = {
    # 3D steady-state run, used for magnetostatics and for steady thermal.
    "3D_steady": {
        "Max Output Level": 5,
        "Coordinate System": "Cartesian",
        "Coordinate Mapping(3)": "1 2 3",
        "Simulation Type": "Steady state",
        "Steady State Max Iterations": 1,
        "Output Intervals": 1,
        "Timestepping Method": "BDF",
        "BDF Order": 1,
        "Solver Input File": "case.sif",
        "Post File": "case.vtu",
        "Output File": "case.result",
    },
}

# Solver blocks keyed by a short name. Values are exact Elmer sif keyword dicts.
SOLVER_LIBRARY: dict[str, dict] = {
    # --- Magnetostatics: 3D permanent magnets ------------------------------
    # Solves for the magnetic vector potential A. The permanent-magnet drive
    # enters through a Body Force ("Magnetization 1/2/3"), not through this
    # solver directly.
    "MagnetoDynamics": {
        "Equation": "MgDyn",
        "Procedure": '"MagnetoDynamics" "WhitneyAVSolver"',
        "Variable": "A",
        "Fix Input Current Density": True,
        "Exec Solver": "Always",
        "Stabilize": True,
        "Optimize Bandwidth": True,
        "Steady State Convergence Tolerance": 1.0e-5,
        "Nonlinear System Convergence Tolerance": 1.0e-7,
        "Nonlinear System Max Iterations": 20,
        "Linear System Solver": "Iterative",
        "Linear System Iterative Method": "BiCGStab",
        "Linear System Max Iterations": 5000,
        "Linear System Convergence Tolerance": 1.0e-8,
        "Linear System Preconditioning": "ILU0",
        "Linear System Residual Output": 50,
    },
    # Post-processing: recover B, H, fluxes, and the nodal forces/torque on the
    # magnet bodies from the computed A. This is what makes the result useful
    # for motor force optimisation.
    "MagnetoDynamicsCalcFields": {
        "Equation": "MgDynCalc",
        "Procedure": '"MagnetoDynamics" "MagnetoDynamicsCalcFields"',
        "Potential Variable": "A",
        "Calculate Magnetic Field Strength": True,
        "Calculate Magnetic Flux Density": True,
        "Calculate Nodal Forces": True,
        "Calculate Nodal Fields": False,
        "Calculate Elemental Fields": True,
        "Exec Solver": "Always",
    },
    # Write VTU output for ParaView.
    "ResultOutputSolver": {
        "Exec Solver": "After timestep",
        "Equation": "ResultOutputSolver",
        "Procedure": '"ResultOutputSolve" "ResultOutputSolver"',
        "VTU Format": True,
        "Save Geometry Ids": True,
    },
    # --- SCAFFOLD: steady heat conduction ----------------------------------
    # Wire-ready; the body/boundary loop below has a thermal branch stubbed out.
    "HeatSolver": {
        "Equation": "HeatSolver",
        "Procedure": '"HeatSolve" "HeatSolver"',
        "Variable": "Temperature",
        "Variable Dofs": 1,
        "Exec Solver": "Always",
        "Stabilize": True,
        "Optimize Bandwidth": True,
        "Steady State Convergence Tolerance": 1.0e-6,
        "Nonlinear System Convergence Tolerance": 1.0e-6,
        "Nonlinear System Max Iterations": 50,
        "Linear System Solver": "Iterative",
        "Linear System Iterative Method": "BiCGStab",
        "Linear System Max Iterations": 1000,
        "Linear System Preconditioning": "ILU",
        "Linear System Convergence Tolerance": 1.0e-8,
    },
    # --- SCAFFOLD: electrostatics ------------------------------------------
    "Electrostatics": {
        "Equation": "Electrostatics",
        "Procedure": '"StatElecSolve" "StatElecSolver"',
        "Variable": "Potential",
        "Calculate Electric Field": True,
        "Exec Solver": "Always",
        "Stabilize": True,
        "Steady State Convergence Tolerance": 1.0e-5,
        "Linear System Solver": "Iterative",
        "Linear System Iterative Method": "BiCGStab",
        "Linear System Max Iterations": 500,
        "Linear System Convergence Tolerance": 1.0e-10,
        "Linear System Preconditioning": "ILU0",
    },
    # --- SCAFFOLD: linear elasticity (structural) --------------------------
    # Elmer's StressSolve solves linear elasticity. It consumes "Youngs Modulus"
    # and "Poisson Ratio" material keywords; the latter is not yet stored on
    # MechanicalProperties (add it when this physics is prioritised). Loads and
    # supports are boundary conditions, so the body/boundary wiring below is a
    # clearly-marked stub pending the 2D-group work.
    "StressSolver": {
        "Equation": "Linear elasticity",
        "Procedure": '"StressSolve" "StressSolver"',
        "Variable": "Displacement",
        "Variable Dofs": 3,
        "Exec Solver": "Always",
        "Calculate Stresses": True,
        "Optimize Bandwidth": True,
        "Steady State Convergence Tolerance": 1.0e-6,
        "Nonlinear System Convergence Tolerance": 1.0e-7,
        "Nonlinear System Max Iterations": 1,
        "Linear System Solver": "Iterative",
        "Linear System Iterative Method": "BiCGStab",
        "Linear System Max Iterations": 5000,
        "Linear System Convergence Tolerance": 1.0e-8,
        "Linear System Preconditioning": "ILU0",
    },
}

# The operating point at which material property functions are evaluated when
# stripping to Elmer's bare SI floats (doc 05). Static properties ignore it;
# temperature-dependent Calibration / ClosedForm properties consume it. The
# magnetostatics path is temperature-independent today, so a fixed room-temp
# default keeps the existing smoke sif byte-for-byte unchanged while giving the
# property functions a real point to be evaluated at. A preset may override it
# via an "operating_point" key.
DEFAULT_OPERATING_POINT: dict[str, Quantity] = {"temperature": 300 * U.K}

# Which solvers (in order) make up each physics option, and which base
# simulation settings they use. The body force / boundary wiring in the
# Generator switches on the `physics` string too.
PHYSICS_PRESETS: dict[str, dict] = {
    "magnetostatics": {
        "simulation": "3D_steady",
        "solvers": ["MagnetoDynamics", "MagnetoDynamicsCalcFields", "ResultOutputSolver"],
        "constants": {
            # mu0; Elmer uses this for the magnetostatic constitutive relation.
            "Permeability of Vacuum": "1.25663706212e-6",
        },
        "operating_point": DEFAULT_OPERATING_POINT,
    },
    # SCAFFOLD presets: structurally complete, but their per-body wiring in the
    # Generator is intentionally left as clearly-marked stubs.
    "thermal": {
        "simulation": "3D_steady",
        "solvers": ["HeatSolver", "ResultOutputSolver"],
        "constants": {"Stefan Boltzmann": "5.6704e-08"},
        "operating_point": DEFAULT_OPERATING_POINT,
    },
    "electrostatics": {
        "simulation": "3D_steady",
        "solvers": ["Electrostatics", "ResultOutputSolver"],
        "constants": {"Permittivity of Vacuum": "8.8541878128e-12"},
        "operating_point": DEFAULT_OPERATING_POINT,
    },
    "linear_elasticity": {
        "simulation": "3D_steady",
        "solvers": ["StressSolver", "ResultOutputSolver"],
        "constants": {},
        "operating_point": DEFAULT_OPERATING_POINT,
    },
}

# The material `to_elmer()` keys each physics' solvers require on *every* body
# (doc 03). Keyed by the `Physics` enum, not strings (no magic words): a typo is a
# static error and the lookup is autocomplete-discoverable. The values must match
# the exact strings the material `to_elmer()` emits in
# `physical/materials/properties.py`: magnetic -> "Relative Permeability",
# thermal -> "Heat Conductivity", electrical -> "Relative Permittivity".
# `SifWriter.validate()` checks these at construction so a body missing a required
# property fails fast with a region-pointing Python error instead of opaquely at
# ElmerSolver runtime. linear_elasticity is intentionally absent (no body-level
# required property is validated yet); `.get(..., set())` yields no requirement.
PHYSICS_REQUIREMENTS: dict[Physics, set[str]] = {
    Physics.MAGNETOSTATICS: {"Relative Permeability"},
    Physics.THERMAL: {"Heat Conductivity"},
    Physics.ELECTROSTATICS: {"Relative Permittivity"},
}


class SifWriter:
    """Build an Elmer Simulation (and write the .sif) from a meshing config and
    its gmsh physical groups.

    Formerly ``elmer.sim.Generator``; renamed to ``SifWriter`` (and the gmsh
    side to ``meshing.Mesher``) so the optimization driver, which imports both,
    has two unambiguous names instead of one shared ``Generator``.

    Args:
        config: the same MeshingConfig used to drive the gmsh mesher.
        physical_groups: the `meshing.Mesher.physical_groups` list, i.e. the
            (id, name, material, tags) records produced while meshing. Optional
            so the sif writer can also be constructed standalone in tests; if
            omitted, no bodies are created.
        physics: which physics preset to wire, as a `Physics` enum member
            (a plain string with the same value is also accepted for
            convenience). Defaults to the fully implemented magnetostatics path.
        validate: run `validate()` (doc 03) at the end of construction so a
            misconfigured solver setup raises a clear, region-pointing error
            here rather than failing opaquely at ElmerSolver runtime. Set False
            to construct a deliberately incomplete config for experiments (the
            wiring then falls back to its in-sif markers, e.g. the magnet
            "MISSING DIRECTION TAG" comment).
    """

    def __init__(
        self,
        config: MeshingConfig,
        physical_groups: list["PhysicalGroup"] | None = None,
        physics: Physics | str = Physics.MAGNETOSTATICS,
        validate: bool = True,
    ) -> None:
        self.config: MeshingConfig = config
        self.physical_groups: list["PhysicalGroup"] = physical_groups or []
        # Accept either the enum or its string value; normalize to the enum so a
        # bad value fails here with a clear error rather than at preset lookup.
        try:
            self.physics: Physics = Physics(physics)
        except ValueError:
            raise ValueError(f"Unknown physics {physics!r}; choose from {[p.value for p in Physics]}.") from None
        self.preset: dict = PHYSICS_PRESETS[self.physics.value]
        # Operating point for evaluating material property functions (doc 05).
        self.operating_point: Mapping[str, Quantity] = self.preset.get("operating_point", DEFAULT_OPERATING_POINT)

        self.sim: elmer.Simulation = elmer.Simulation()
        self.sim.settings = dict(SIMULATION_LIBRARY[self.preset["simulation"]])
        self.sim.constants.update(self.preset["constants"])

        # Build the sif sections in dependency order.
        self._solvers: list[elmer.Solver] = self._build_solvers()
        self._equation: elmer.Equation = self._build_equation()
        self._materials: dict[str, elmer.Material] = self._build_materials()
        self._build_bodies()

        if validate:
            self.validate()

    # -- validation ----------------------------------------------------------

    def validate(self) -> None:
        """Cross-object solver checks Pydantic can't see (doc 03).

        Field-level validity (units, dimensionality) is already guaranteed by the
        Pydantic config models; this pass covers the material ↔ solver coupling
        that only emerges once a physics is chosen. Every problem is accumulated
        and reported together, so one ``ValueError`` lists *all* misconfigurations
        (each pointing at its region/material) instead of failing on the first.

        Checks (1-3 from doc 03; 4-5 wait for the Phase 4 boundary groups):

        1. **Required material properties.** Each body's material must emit the
           ``to_elmer()`` keys this physics' solvers need (``PHYSICS_REQUIREMENTS``).
        2. **Numeric sanity / unit stripping.** Every emitted material value must
           be a bare number or string — a leaked pint ``Quantity`` means a
           ``to_elmer()`` forgot to strip units.
        3. **Magnets have a direction.** Under magnetostatics, every magnet body
           must resolve a usable ``Magnetization`` (a non-zero direction). This is
           the ``! Magnetization: MISSING DIRECTION TAG`` case in
           ``_wire_magnet_body`` promoted to a hard error so a zero-field magnet
           can't slip through (the marker stays for ``validate=False`` runs).
        """
        problems: list[str] = []
        required: set[str] = PHYSICS_REQUIREMENTS.get(self.physics, set())

        for group in self.physical_groups:
            mat: MaterialProperties = group.material
            emitted: dict = mat.to_elmer(at=self.operating_point)

            # Check 1: required material properties present.
            missing: set[str] = required - emitted.keys()
            if missing:
                problems.append(f"Body {group.name}: material {mat.name} missing {sorted(missing)} for physics '{self.physics.value}'")

            # Check 2: numeric sanity / unit stripping.
            for key, value in emitted.items():
                if not isinstance(value, (int, float, str)):
                    problems.append(
                        f"Body {group.name}: material {mat.name} property '{key}' "
                        f"is a {type(value).__name__}, expected a stripped number/str "
                        f"(a to_elmer() left a pint Quantity unconverted)"
                    )

            # Check 3: magnets must resolve a usable magnetization direction.
            if self.physics is Physics.MAGNETOSTATICS and mat.is_magnet:
                magnetizations: list[Magnetization] = [
                    c for c in conditions_for(group.tags, Physics.MAGNETOSTATICS, ConditionTarget.BODY) if isinstance(c, Magnetization)
                ]
                usable: Magnetization | None = next((m for m in magnetizations if m.direction.magnitude() != 0), None)
                if usable is None:
                    problems.append(
                        f"Body {group.name}: magnet material {mat.name} has no usable "
                        f"Magnetization condition (a non-zero direction is required "
                        f"for physics '{self.physics.value}')"
                    )

        if problems:
            raise ValueError("Solver configuration invalid:\n  - " + "\n  - ".join(problems))

    # -- sif section builders ------------------------------------------------

    def _build_solvers(self) -> list[elmer.Solver]:
        """Instantiate the preset's solvers as pyelmer Solver objects."""
        solvers: list[elmer.Solver] = []
        for name in self.preset["solvers"]:
            solvers.append(elmer.Solver(self.sim, name, dict(SOLVER_LIBRARY[name])))
        return solvers

    def _build_equation(self) -> elmer.Equation:
        """One equation referencing all active solvers, attached to every body.

        (Post-processing solvers like CalcFields/ResultOutput are listed as
        active solvers here, which is how Elmer expects them.)"""
        return elmer.Equation(self.sim, "main", self._solvers)

    def _build_materials(self) -> dict[str, elmer.Material]:
        """One Elmer Material per distinct project material, keyed by material
        name. Deduplicated so two bodies of the same material share one Material
        block (pyelmer's Material(__new__) also guards against clashes)."""
        materials: dict[str, elmer.Material] = {}
        seen: set[str] = set()
        for group in self.physical_groups:
            mat = group.material
            if mat.name in seen:
                continue
            seen.add(mat.name)
            materials[mat.name] = elmer.Material(self.sim, mat.name, data=mat.to_elmer(at=self.operating_point))
        return materials

    def _build_bodies(self) -> None:
        """One Elmer Body per gmsh physical group, targeting the same gmsh id,
        wired to its material + the shared equation, plus any physics-specific
        per-body extras (magnetization body force, fixed temperature, ...)."""
        for group in self.physical_groups:
            body: elmer.Body = elmer.Body(self.sim, group.name, [group.id])
            body.material = self._materials[group.material.name]
            body.equation = self._equation

            if self.physics is Physics.MAGNETOSTATICS:
                self._wire_magnet_body(body, group)
            elif self.physics is Physics.THERMAL:
                self._wire_thermal_body(body, group)
            elif self.physics is Physics.LINEAR_ELASTICITY:
                self._wire_elasticity_body(body, group)
            # electrostatics: bodies need only material + equation here;
            # potentials are applied as boundaries (SCAFFOLD, see note below).

    # -- physics-specific per-body wiring -----------------------------------

    def _wire_magnet_body(self, body: elmer.Body, group: "PhysicalGroup") -> None:
        """Attach a permanent-magnet Body Force if this region is a magnet.

        The magnetization magnitude |M| = Br/mu0 comes from the material. The
        *direction* is per-region and is carried by a `Magnetization` condition on
        the mesh tag: in a Halbach array the same N52 block points N/E/S/W
        depending on its slot, and that orientation is encoded in the build123d
        part name and surfaced via the EntityTag's conditions. Air / PCB regions
        have no remanence and get no body force.

        This is the uniform condition path: resolve the body-target
        magnetostatics conditions for the region and let the `Magnetization`
        condition emit its own Elmer keywords, rather than reading a scalar field
        and open-coding the vector math here.
        """
        if not group.material.is_magnet:
            return

        magnitude: float = group.material.magnetic.magnetization_magnitude(at=self.operating_point)  # A/m

        conditions: list[Magnetization] = [
            c for c in conditions_for(group.tags, Physics.MAGNETOSTATICS, ConditionTarget.BODY) if isinstance(c, Magnetization)
        ]
        magnetization: Magnetization | None = conditions[0] if conditions else None
        if magnetization is None or magnetization.direction.magnitude() == 0:
            # Material is a magnet but no (usable) orientation was found. Emit a
            # commented marker rather than silently producing a zero field.
            body.data.update({"! Magnetization": "MISSING DIRECTION TAG"})
            return

        force: elmer.BodyForce = elmer.BodyForce(
            self.sim,
            f"{group.name}_magnetization",
            data=magnetization.to_elmer(magnitude),
        )
        body.body_force = force

    def _wire_thermal_body(self, body: elmer.Body, group: "PhysicalGroup") -> None:
        """SCAFFOLD: heat-equation per-region wiring.

        The thermal conditions (`FixedTemperature`, `HeatFlux`, `Convection`) are
        all boundary-target: in Elmer they are boundary conditions, not body
        properties, so they are emitted by the condition-driven boundary loop —
        not here. That loop needs the gmsh generator to also emit 2D (boundary)
        physical groups, which it does not do yet (Phase 4). Until then a thermal
        body needs only its material + equation (already attached), so this is a
        deliberate no-op kept so the preset stays selectable.
        """
        return

    def _wire_elasticity_body(self, body: elmer.Body, group: "PhysicalGroup") -> None:
        """SCAFFOLD: linear-elasticity per-region wiring.

        The body already references its material (whose `to_elmer()` emits
        "Youngs Modulus"); a real run also needs a Poisson Ratio material keyword
        and the loads/supports, which are boundary conditions. Both are deferred:
        Poisson Ratio is not yet stored on MechanicalProperties, and loads need
        the 2D boundary groups. Left as a stub so the preset is selectable and
        the sif generates with the right solver wired.
        """
        # No body-level extras yet; material + equation are already attached.
        return

    # -- output --------------------------------------------------------------

    def write(self, sim_dir: str) -> None:
        """Write the ELMERSOLVER_STARTINFO, the .sif, and the boundary-id map."""
        self.sim.write_startinfo(sim_dir)
        self.sim.write_sif(sim_dir)
        if self.sim.boundaries:
            self.sim.write_boundary_ids(sim_dir)
