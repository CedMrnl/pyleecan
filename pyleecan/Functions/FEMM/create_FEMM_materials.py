# -*- coding: utf-8 -*-

from numpy import exp, pi

from ...Functions.FEMM.create_FEMM_bar import create_FEMM_bar
from ...Functions.FEMM.create_FEMM_circuit_material import create_FEMM_circuit_material
from ...Functions.FEMM.create_FEMM_magnet import create_FEMM_magnet
from ...Functions.labels import (
    LAM_LAB,
    STATOR_LAB,
    ROTOR_LAB,
    AIRGAP_LAB,
    VENT_LAB,
    HOLEV_LAB,
    HOLEM_LAB,
    MAG_LAB,
    WIND_LAB,
    SLID_LAB,
    NO_MESH_LAB,
    get_obj_from_label,
    decode_label,
)
from ...Functions.FEMM import LAM_MAT_NAME, AIRGAP_MAT_NAME


def create_FEMM_materials(
    femm,
    machine,
    surf_list,
    Is,
    Ir,
    is_mmfs,
    is_mmfr,
    type_BH_stator,
    type_BH_rotor,
    is_eddies,
    j_t0,
):
    """Add materials in FEMM

    Parameters
    ----------
    femm : FEMMHandler
        client to send command to a FEMM instance
    machine : Machine
        the machine to simulate
    surf_list : list
        List of surface of the machine
    Is : ndarray
        Stator current matrix [A]
    Ir : ndarray
        Rotor current matrix [A]
    is_mmfs : bool
        1 to compute the stator magnetomotive force/stator magnetic field
    is_mmfr : bool
        1 to compute the rotor magnetomotive force / rotor magnetic field
    type_BH_stator: int
        2 Infinite permeability, 1 to use linear B(H) curve according to mur_lin, 0 to use the B(H) curve
    type_BH_rotor: int
        2 Infinite permeability, 1 to use linear B(H) curve according to mur_lin, 0 to use the B(H) curve
    is_eddies : bool
        1 to calculate eddy currents
    jt_0 : int
        Current time step for winding calculation

    Returns
    -------
    Tuple: dict, list
        Dictionary of properties and list containing the name of the circuits created
    """

    prop_dict = dict()  # Initialisation of the dictionnary to return

    rotor = machine.rotor
    stator = machine.stator

    materials = list()
    circuits = list()
    # Starting creation of properties for each surface of the machine
    for surf in surf_list:
        label_dict = decode_label(surf.label)
        if LAM_LAB in label_dict["surf_type"] and STATOR_LAB in label_dict["lam_type"]:
            lam_obj = get_obj_from_label(machine, label_dict=label_dict)
            mat_name = label_dict["lam_label"] + " " + LAM_MAT_NAME
            if type_BH_stator == 2:
                mu_is = 100000  # Infinite permeability
            else:
                mu_is = lam_obj.mat_type.mag.mur_lin  # Relative
            # Check if the property already exist in FEMM
            if mat_name not in materials:
                # magnetic permeability
                femm.mi_addmaterial(
                    mat_name, mu_is, mu_is, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0
                )
                if type_BH_stator == 0:
                    BHs = lam_obj.mat_type.mag.get_BH()
                    for ii in range(BHs.shape[0]):
                        femm.mi_addbhpoint(mat_name, BHs[ii][1], BHs[ii][0])
                materials.append(mat_name)
            prop_dict[label_dict["full"]] = mat_name
        elif LAM_LAB in label_dict["surf_type"] and ROTOR_LAB in label_dict["lam_type"]:
            lam_obj = get_obj_from_label(machine, label_dict=label_dict)
            mat_name = label_dict["lam_label"] + " " + LAM_MAT_NAME
            # Initialisation from the rotor of the machine
            if type_BH_rotor == 2:
                mu_ir = 100000  # Infinite permeability
            else:
                mu_ir = rotor.mat_type.mag.mur_lin  # Relative
            # Check if the property already exist in FEMM
            if mat_name not in materials:
                # magnetic permeability
                femm.mi_addmaterial(
                    mat_name, mu_ir, mu_ir, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0
                )
                if type_BH_rotor == 0:
                    BHr = lam_obj.mat_type.mag.get_BH()
                    for ii in range(BHr.shape[0]):
                        femm.mi_addbhpoint(mat_name, BHr[ii][1], BHr[ii][0])
                materials.append(mat_name)
            prop_dict[label_dict["full"]] = mat_name
        elif AIRGAP_LAB in label_dict["surf_type"]:  # Airgap surface
            if "Airgap" not in materials:
                femm.mi_addmaterial("Airgap", 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0)
                materials.append("Airgap")
            prop_dict[label_dict["full"]] = "Airgap"
        elif VENT_LAB in label_dict["surf_type"]:  # Ventilation
            vent = get_obj_from_label(machine, label_dict=label_dict)
            material = vent.mat_void
            # Check if the property already exist in FEMM
            if "Air" not in materials:
                femm.mi_addmaterial("Air", 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0)
                materials.append("Air")
            prop_dict[label_dict["full"]] = "Air"
        elif HOLEV_LAB in label_dict["surf_type"]:  # Hole Void
            hole = get_obj_from_label(machine, label_dict=label_dict)
            material = hole.mat_void
            # Check if the property already exist in FEMM
            if "Air" not in materials:
                femm.mi_addmaterial("Air", 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0)
                materials.append("Air")
            prop_dict[label_dict["full"]] = "Air"
        elif WIND_LAB in label_dict["surf_type"]:
            is_stator = STATOR_LAB in label_dict["lam_type"]
            I = Is if is_stator else Ir
            is_mmf = is_mmfs if is_stator else is_mmfr
            lam_obj = get_obj_from_label(machine, label_dict=label_dict)
            prop, materials, circuits = create_FEMM_circuit_material(
                femm, circuits, label, is_eddies, lam_obj, I, is_mmf, j_t0, materials
            )
            prop_dict[label_dict["full"]] = prop
        elif MAG_LAB in label_dict["surf_type"] or HOLEM_LAB in label_dict["surf_type"]:
            is_stator = STATOR_LAB in label_dict["lam_type"]
            is_mmf = is_mmfs if is_stator else is_mmfr
            mag_obj = get_obj_from_label(machine, label_dict=label_dict)
            prop, materials = create_FEMM_magnet(
                femm, label, is_mmf, is_eddies, materials, mag_obj
            )
            prop_dict[label_dict["full"]] = prop
        elif (
            SLID_LAB in label_dict["surf_type"]
            or NO_MESH_LAB in label_dict["surf_type"]
        ):
            prop_dict[label_dict["full"]] = "<No Mesh>"
        else:
            raise Exception("Unknown label " + label_dict["full"])
    return prop_dict, materials, circuits
