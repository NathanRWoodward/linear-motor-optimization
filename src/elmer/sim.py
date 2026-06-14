from meshing.config import MeshingConfig
import pyelmer.elmer as elmer


# TODO: create the physical groups BEFORE meshing.. we're gonna need them here + gmsh tags
#  to assign the right materials and boundary conditions in the solver config.
#
# We can create the physical groups based on the material and tags of each entity,
# which we can extract from the name of the entity in gmsh (which is imported from the STEP file).
#
#  We can then use these physical groups to assign the right materials and boundary conditions in the solver config.


### GO look at https://github.com/nemocrys/pyelmer/blob/master/examples/3D_Electrostatic_Capacitance/3d_electrostatic_capacitance.py for an example of how to use pyelmer to create a simulation config based on the mesh config.
##  Emuplate the way they create the simulation config based on the mesh config, but instead of hardcoding the materials and boundary conditions, we will create them based on the materials and tags in the mesh config.


class Generator:
    def __init__(self, config: MeshingConfig):
        self.config = config
        """
        1) Create the equation and add the solver and boundary conditions, forces in a similar way we did for gmsh. 
        2) Unify the preprocessing before sending that same data bundle to gmsh meshing  -> then to -> this sim as a smooth pipeline
        3) This example is NOT for MY halbach simpluation, it's just an example of what we can do with the config and how to use it to create the simulation config. 
            There are some relevant examples in the pyelmer repo, at https://github.com/nemocrys/pyelmer
        """


#                                   ############################################################################
#                                   ### Elmer Setup
#                                   ############################################################################

#                                   sim = elmer.load_simulation("3D_steady", "my_simulations.yml")
#                                   # adding constants is very important, otherwise the solver calculates wrong results!
#                                   sim.constants.update({"Permittivity of Vacuum": "8.8542e-12"})
#                                   sim.constants.update({"Gravity(4)": "0 -1 0 9.82"})
#                                   sim.constants.update({"Boltzmann Constant": "1.3807e-23"})
#                                   sim.constants.update({"Unit Charge": "1.602e-19"})
#
#                                   ~~~~~~~~~~~~~~~~~~  materials ~~~~~~~~~~~~~~~~~~
#                                   air = elmer.load_material("air", sim, "my_materials.yml")
#                                   ro4003c = elmer.load_material("ro4003c", sim, "my_materials.yml")
#
#                                   # ~~~~~~~~~~~~~~~~~~ solver ~~~~~~~~~~~~~~~~~~
#                                   solver_electrostatic = elmer.load_solver("Electrostatics", sim, r"my_solvers.yml")
#                                   # very important, the value must match the boundary condition abs(potential difference) !!!
#                                   # otherwise the capacitance will be calculated wrong !
#                                   solver_electrostatic.data.update({"Potential Difference": "1.0"})
#
#                                   # ~~~~~~~~~~~~~~~~~~ equation ~~~~~~~~~~~~~~~~~~
#                                   eqn = elmer.Equation(sim, "main", [solver_electrostatic])
#
#                                   # ~~~~~~~~~~~~~~~~~~ bodies ~~~~~~~~~~~~~~~~~~
#                                   bdy_sub = elmer.Body(sim, "substrate", [ph_sub])
#                                   bdy_sub.material = ro4003c
#                                   bdy_sub.equation = eqn
#
#                                   bdy_ab = elmer.Body(sim, "airbox", [ph_ab])
#                                   bdy_ab.material = air
#                                   bdy_ab.equation = eqn
#
#                                   # ~~~~~~~~~~~~~~~~~~ boundaries ~~~~~~~~~~~~~~~~~~
#                                   bndry_m1 = elmer.Boundary(sim, "top metal", [ph_m1_sfs])
#                                   bndry_m1.data.update({"Potential": "1.0"})
#
#                                   bndry_m2 = elmer.Boundary(sim, "bottom metal", [ph_m2_sfs])
#                                   bndry_m2.data.update({"Potential": "0.0"})
#
#                                   bndry_airbox = elmer.Boundary(sim, "FarField", [ph_ab_sfs])
#                                   bndry_airbox.data.update({"Electric Infinity BC": "True"})
#
#                                   # ~~~~~~~~~~~~~~~~~~ export ~~~~~~~~~~~~~~~~~~
#                                   sim.write_startinfo(sim_dir)
#                                   sim.write_sif(sim_dir)
#
