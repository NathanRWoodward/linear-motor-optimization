"""Elmer .sif generator.

This is the second half of the pipeline:

    build123d CAD -> STEP -> gmsh (meshing.Generator) -> Elmer (this module)

The gmsh `meshing.Generator` walks the STEP entities, matches each to a material
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

from common.vector import Vec3
from meshing.config import MeshingConfig
import pyelmer.elmer as elmer


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
}

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
    },
    # SCAFFOLD presets: structurally complete, but their per-body wiring in the
    # Generator is intentionally left as clearly-marked stubs.
    "thermal": {
        "simulation": "3D_steady",
        "solvers": ["HeatSolver", "ResultOutputSolver"],
        "constants": {"Stefan Boltzmann": "5.6704e-08"},
    },
    "electrostatics": {
        "simulation": "3D_steady",
        "solvers": ["Electrostatics", "ResultOutputSolver"],
        "constants": {"Permittivity of Vacuum": "8.8541878128e-12"},
    },
}


class Generator:
    """Build an Elmer Simulation (and write the .sif) from a meshing config and
    its gmsh physical groups.

    Args:
        config: the same MeshingConfig used to drive the gmsh mesher.
        physical_groups: the `meshing.generator.Generator.physical_groups` list,
            i.e. the (id, name, material, tags) records produced while meshing.
            Optional so the Elmer generator can also be constructed standalone in
            tests; if omitted, no bodies are created.
        physics: which PHYSICS_PRESETS entry to wire. Defaults to the fully
            implemented magnetostatics path.
    """

    def __init__(self, config: MeshingConfig, physical_groups: list | None = None, physics: str = "magnetostatics"):
        self.config = config
        self.physical_groups = physical_groups or []
        self.physics = physics
        if physics not in PHYSICS_PRESETS:
            raise ValueError(f"Unknown physics preset {physics!r}; choose from {list(PHYSICS_PRESETS)}.")
        self.preset = PHYSICS_PRESETS[physics]

        self.sim = elmer.Simulation()
        self.sim.settings = dict(SIMULATION_LIBRARY[self.preset["simulation"]])
        self.sim.constants.update(self.preset["constants"])

        # Build the sif sections in dependency order.
        self._solvers = self._build_solvers()
        self._equation = self._build_equation()
        self._materials = self._build_materials()
        self._build_bodies()

    # -- sif section builders ------------------------------------------------

    def _build_solvers(self) -> list:
        """Instantiate the preset's solvers as pyelmer Solver objects."""
        solvers = []
        for name in self.preset["solvers"]:
            solvers.append(elmer.Solver(self.sim, name, dict(SOLVER_LIBRARY[name])))
        return solvers

    def _build_equation(self):
        """One equation referencing all active solvers, attached to every body.

        (Post-processing solvers like CalcFields/ResultOutput are listed as
        active solvers here, which is how Elmer expects them.)"""
        return elmer.Equation(self.sim, "main", self._solvers)

    def _build_materials(self) -> dict:
        """One Elmer Material per distinct project material, keyed by material
        name. Deduplicated so two bodies of the same material share one Material
        block (pyelmer's Material(__new__) also guards against clashes)."""
        materials: dict = {}
        seen: dict[str, MeshingConfig] = {}
        for group in self.physical_groups:
            mat = group.material
            if mat.name in seen:
                continue
            seen[mat.name] = mat
            materials[mat.name] = elmer.Material(self.sim, mat.name, data=mat.to_elmer())
        return materials

    def _build_bodies(self) -> None:
        """One Elmer Body per gmsh physical group, targeting the same gmsh id,
        wired to its material + the shared equation, plus any physics-specific
        per-body extras (magnetization body force, fixed temperature, ...)."""
        for group in self.physical_groups:
            body = elmer.Body(self.sim, group.name, [group.id])
            body.material = self._materials[group.material.name]
            body.equation = self._equation

            if self.physics == "magnetostatics":
                self._wire_magnet_body(body, group)
            elif self.physics == "thermal":
                self._wire_thermal_body(body, group)
            # electrostatics: bodies need only material + equation here;
            # potentials are applied as boundaries (SCAFFOLD, see note below).

    # -- physics-specific per-body wiring -----------------------------------

    def _wire_magnet_body(self, body, group) -> None:
        """Attach a permanent-magnet Body Force if this region is a magnet.

        The magnetization magnitude |M| = Br/mu0 comes from the material. The
        *direction* is per-region and comes from the mesh tag's
        `magnetic_coercivity` Vec3 (re-used here as the magnetization-direction
        carrier): in a Halbach array the same N52 block points N/E/S/W depending
        on its slot, and that orientation is encoded in the build123d part name
        and surfaced via the EntityTag. Air / PCB regions have no remanence and
        get no body force.
        """
        if not group.material.is_magnet:
            return

        magnitude = group.material.magnetic.magnetization_magnitude  # A/m

        direction = self._magnetization_direction(group)
        if direction is None:
            # Material is a magnet but no orientation tag was found. Emit a
            # commented marker rather than silently producing a zero field.
            body.data.update({"! Magnetization": "MISSING DIRECTION TAG"})
            return

        mx, my, mz = magnitude * direction.x, magnitude * direction.y, magnitude * direction.z
        force = elmer.BodyForce(
            self.sim,
            f"{group.name}_magnetization",
            data={
                "Magnetization 1": f"{mx:.6g}",
                "Magnetization 2": f"{my:.6g}",
                "Magnetization 3": f"{mz:.6g}",
            },
        )
        body.body_force = force

    def _magnetization_direction(self, group) -> Vec3 | None:
        """Resolve a unit magnetization direction from the region's tags.

        Looks for the first tag carrying a `magnetic_coercivity` vector and
        normalises it. Returns None if no oriented tag is present.
        """
        for tag in group.tags:
            vec = getattr(tag, "magnetic_coercivity", None)
            if vec is None:
                continue
            mag = (vec.x**2 + vec.y**2 + vec.z**2) ** 0.5
            if mag == 0:
                continue
            return Vec3(vec.x / mag, vec.y / mag, vec.z / mag)
        return None

    def _wire_thermal_body(self, body, group) -> None:
        """SCAFFOLD: heat-equation per-region wiring.

        EntityTag already carries `fixed_temperature` (K) and `fixed_heat_flux`
        (W/m^2). In Elmer these are boundary conditions, not body properties, so
        the real implementation should create elmer.Boundary objects targeting
        the *surface* physical groups of this body. That requires the gmsh
        generator to also emit 2D (boundary) physical groups, which it does not
        yet. Left as a stub until the thermal solver is prioritised.
        """
        for tag in group.tags:
            if getattr(tag, "fixed_temperature", None) is not None:
                # TODO: create a Boundary on this region's surface group with
                #   {"Temperature": tag.fixed_temperature}. Needs 2D groups.
                body.data.update({"! Fixed Temperature (needs boundary)": tag.fixed_temperature})
            if getattr(tag, "fixed_heat_flux", None) is not None:
                # TODO: {"Heat Flux": tag.fixed_heat_flux} on the surface group.
                body.data.update({"! Fixed Heat Flux (needs boundary)": tag.fixed_heat_flux})

    # -- output --------------------------------------------------------------

    def write(self, sim_dir: str) -> None:
        """Write the ELMERSOLVER_STARTINFO, the .sif, and the boundary-id map."""
        self.sim.write_startinfo(sim_dir)
        self.sim.write_sif(sim_dir)
        if self.sim.boundaries:
            self.sim.write_boundary_ids(sim_dir)
