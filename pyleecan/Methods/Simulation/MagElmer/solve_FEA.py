import numpy as np
import subprocess

from numpy import zeros, pi, roll, mean, max as np_max, min as np_min, sign, angle as np_angle
from os.path import basename, splitext
from SciDataTool import DataTime, VectorField, Data1D
from os.path import join

from ....Functions.Winding.gen_phase_list import gen_name


from ....Classes.Magnetics import Magnetics
from ....Functions.GMSH import surface_label
from ....Functions.Winding.find_wind_phase_color import get_phase_id
from .... import __version__
from ....Functions.get_path_binary import get_path_binary


def solve_FEA(self, output, sym, angle, time, angle_rotor, Is, Ir):
    """
    Solve Elmer model to calculate airgap flux density, torque instantaneous/average/ripple values,
    flux induced in stator windings and flux density, field and permeability maps

    Parameters
    ----------
    self: MagElmer
        A MagElmer object
    output: Output
        An Output object
    sym: int
        Spatial symmetry factor
    time: ndarray
        Time vector for calculation
    angle: ndarray
        Angle vector for calculation
    Is : ndarray
        Stator current matrix (qs,Nt) [A]
    Ir : ndarray
        Stator current matrix (qs,Nt) [A]
    angle_rotor: ndarray
        Rotor angular position vector (Nt,)
    """


    project_name = self.get_path_save_fea(output)
    elmermesh_folder = project_name
    mesh_names_file = join(project_name, "mesh.names")
    boundaries = {}
    bodies = {}
    machine = output.simu.machine
    BHs = output.geo.stator.BH_curve  # Stator B(H) curve
    BHr = output.geo.rotor.BH_curve  # Rotor B(H) curve
    # Is = output.elec.Is  # Stator currents waveforms
    # Ir = output.elec.Ir  # Rotor currents waveforms
    Speed = output.elec.N0
    rotor_mat_file = join(project_name, "rotor_material.pmf")
    stator_mat_file = join(project_name, "stator_material.pmf")

    # TO-DO: Time vector must be greater than one
    timesize_str = np.array2string(np.diff(time), separator=' ', formatter={'float_kind': lambda x: "%.2e" % x})
    timelen = len(time) - 1
    ones_str = np.array2string(np.ones(timelen), separator=' ', formatter={'int': lambda x: "%d" % x})
    timeinterval_str = ones_str.replace('.', '')

    with open(mesh_names_file, 'rt') as f:
        for line in f:
            fields = line.strip().split()
            if fields[0] == '$':
                field_name = fields[1]
                field_value = fields[3]
                # update dictionary
                # _settings['Geometry'][field_name] = field_value
                if field_name.count("BOUNDARY"):
                    boundaries[field_name] = field_value
                else:
                    bodies[field_name] = {'id': field_value,
                                          'mat': 1,  # Air by Default
                                          'eq': 1,  # RigidMeshMapper by Default
                                          'bf': None,
                                          'tg': None}

    with open(rotor_mat_file, 'wt') as ro:
        ro.write("! File Generated by pyleecan v{0}\n".format(__version__))
        ro.write("! Material Name: {0}\n"
                 "! B-H Curve Rotor Material\n"
                 "Electric Conductivity = 0\n"
                 "H-B Curve = Variable coupled iter\n"
                 " Real\t\tCubic Monotone\n".format(machine.rotor.mat_type.name))
        for ii in range(BHr.shape[0]):
            ro.write("   {0}\t\t{1}\n".format(BHr[ii][1], BHr[ii][0]))
        ro.write("End\n")

    with open(stator_mat_file, 'wt') as ro:
        ro.write("! File Generated by pyleecan v{0}\n".format(__version__))
        ro.write("! Material Name: {0}\n"
                 "! B-H Curve Stator Material\n"
                 "Electric Conductivity = 0\n"
                 "H-B Curve = Variable coupled iter\n"
                 " Real\t\tCubic Monotone\n".format(machine.stator.mat_type.name))
        for ii in range(BHs.shape[0]):
            ro.write("   {0}\t\t{1}\n".format(BHs[ii][1], BHs[ii][0]))
        ro.write("End\n")

    elmer_sim_file = join(project_name, "pyleecan_elmer.sif")
    pp = machine.stator.winding.p
    wind_mat = machine.stator.winding.comp_connection_mat(machine.stator.slot.Zs)
    Swire = machine.stator.winding.conductor.comp_surface()
    ror = machine.rotor.comp_radius_mec()
    sir = machine.stator.comp_radius_mec()
    with open(elmer_sim_file, 'wt') as fo:
        fo.write("! File Generated by pyleecan v{0}\n".format(__version__))
        fo.write("$ WM = 2*pi*{0}/60        ! Mechanical Frequency [rad/s]\n".format(Speed))
        fo.write("$ PP = {0}                ! Pole pairs\n".format(pp))
        fo.write("$ WE = PP*WM              ! Electrical Frequency [Hz]\n")

        magnet_dict = machine.rotor.hole[0].get_magnet_dict()
        magnet_0 = magnet_dict["magnet_0"]
        surf_list = machine.build_geometry(sym=1)
        pm_index = 6
        Mangle = list()
        Ncond_Aplus = 1
        Ncond_Aminus = 1
        Ncond_Bplus = 1
        Ncond_Bminus = 1
        Ncond_Cplus = 1
        Ncond_Cminus = 1
        Ncond_Dplus = 1
        Ncond_Dminus = 1
        Ncond_Eplus = 1
        Ncond_Eminus = 1
        Ncond_Fplus = 1
        Ncond_Fminus = 1
        for surf in surf_list:
            label = surface_label.get(surf.label, "UNKNOWN")
            if "MAGNET" in label:
                point_ref = surf.point_ref
                if "RAD" in label and "_N_" in label:  # Radial magnetization
                    mag = "theta"  # North pole magnet
                    magnetization_type = "radial"
                elif "RAD" in label:
                    mag = "theta + 180"  # South pole magnet
                    magnetization_type = "radial"
                elif "PAR" in label and "_N_" in label:
                    mag = np_angle(point_ref) * 180 / pi  # North pole magnet
                    magnetization_type = "parallel"
                elif "PAR" in label:
                    mag = np_angle(point_ref) * 180 / pi + 180  # South pole magnet
                    magnetization_type = "parallel"
                elif "HALL" in label:
                    Zs = machine.rotor.slot.Zs
                    mag = str(-(Zs / 2 - 1)) + " * theta + 90 "
                    magnetization_type = "hallback"
                else:
                    continue
                if bodies.get(label, None) is not None:
                    Mangle.append(mag)
                    bodies[label]['mat'] = pm_index
                    bodies[label]['eq'] = 1
                    bodies[label]['bf'] = 1
                    bodies[label]['tg'] = 1
                    pm_index = pm_index + 1
            elif "W_STA" in label:
                st = label.split("_")
                Nrad_id = int(st[2][1:])  # zone radial coordinate
                Ntan_id = int(st[3][1:])  # zone tangential coordinate
                Zs_id = int(st[4][1:])  # Zone slot number coordinate
                # Get the phase value in the correct slot zone
                q_id = get_phase_id(wind_mat, Nrad_id, Ntan_id, Zs_id)
                Ncond = wind_mat[Nrad_id, Ntan_id, Zs_id, q_id]
                s = sign(Ncond)
                if bodies.get(label, None) is not None:
                    bodies[label]['mat'] = 5
                    bodies[label]['eq'] = 1
                    if q_id == 0 and s == 1:
                        bodies[label]['bf'] = 2
                        Ncond_Aplus = abs(Ncond)
                    elif q_id == 0 and s == -1:
                        bodies[label]['bf'] = 3
                        Ncond_Aminus = abs(Ncond)
                    elif q_id == 1 and s == 1:
                        bodies[label]['bf'] = 4
                        Ncond_Bplus = abs(Ncond)
                    elif q_id == 1 and s == -1:
                        bodies[label]['bf'] = 5
                        Ncond_Bminus = abs(Ncond)
                    elif q_id == 2 and s == 1:
                        bodies[label]['bf'] = 6
                        Ncond_Cplus = abs(Ncond)
                    elif q_id == 2 and s == -1:
                        bodies[label]['bf'] = 7
                        Ncond_Cminus = abs(Ncond)
                    elif q_id == 3 and s == 1:
                        bodies[label]['bf'] = 8
                        Ncond_Dplus = abs(Ncond)
                    elif q_id == 3 and s == -1:
                        bodies[label]['bf'] = 9
                        Ncond_Dminus = abs(Ncond)
                    elif q_id == 4 and s == 1:
                        bodies[label]['bf'] = 10
                        Ncond_Eplus = abs(Ncond)
                    elif q_id == 4 and s == -1:
                        bodies[label]['bf'] = 11
                        Ncond_Eminus = abs(Ncond)
                    elif q_id == 5 and s == 1:
                        bodies[label]['bf'] = 12
                        Ncond_Fplus = abs(Ncond)
                    elif q_id == 5 and s == -1:
                        bodies[label]['bf'] = 13
                        Ncond_Fminus = abs(Ncond)
                    else:
                        pass
            elif "ROTOR_LAM" in label and bodies.get(label, None) is not None:
                bodies[label]['mat'] = 4
                bodies[label]['eq'] = 1
                bodies[label]['bf'] = 1
                bodies[label]['tg'] = 1
            elif "STATOR_LAM" in label and bodies.get(label, None) is not None:
                bodies[label]['mat'] = 3
                bodies[label]['eq'] = 1
            elif "SHAFT" in label and bodies.get(label, None) is not None:
                bodies[label]['mat'] = 1
                bodies[label]['eq'] = 1
                bodies[label]['bf'] = 1
                bodies[label]['tg'] = 1
            elif "H_ROTOR" in label and bodies.get(label, None) is not None:
                bodies[label]['mat'] = 1
                bodies[label]['eq'] = 1
                bodies[label]['bf'] = 1
                bodies[label]['tg'] = 1
            else:
                pass

        # The following bodies are not in the dictionary
        bodies["AG_INT"]['bf'] = 1
        bodies["SB_INT"]['bf'] = 1

        No_Magnets = pm_index - 6
        magnet_temp = 20.0  # Magnet Temperature Fixed for now
        Hcm20 = magnet_0.mat_type.mag.Hc
        Brm20 = magnet_0.mat_type.mag.Brm20
        kt = 0.01  # Br Temperature Coefficient fixed for now
        Br = Brm20 * (1 + kt * 0.01 * (magnet_temp - 20.0))
        magnet_permeability = magnet_0.mat_type.mag.mur_lin
        rho20_m = magnet_0.mat_type.elec.rho
        kt_m = 0.01  # Rho Temperature Coefficient fixed for now
        rho_m = rho20_m * (1 + kt_m * (magnet_temp - 20.0))
        conductivity_m = 1.0 / rho_m

        skip_steps = 1  # Fixed for now
        degrees_step = 1  # Fixed for now
        current_angle = 0 - pp * degrees_step * skip_steps
        angle_shift = self.angle_rotor_shift - self.angle_stator_shift
        rotor_init_pos = angle_shift - degrees_step * skip_steps
        Ncond = 1  # Fixed for Now
        Cp = 1  # Fixed for Now
        qs = len(machine.stator.get_name_phase())

        fo.write("$ H_PM = {0}              ! Magnetization [A/m]\n".format(round(Hcm20, 2)))
        fo.write("$ Shift = 2*pi/{0}        ! N-phase machine [rad]\n".format(qs))
        fo.write("$ Gamma = {0}*pi/180      ! Current Angle [rad]\n".format(round(current_angle, 2)))
        fo.write("$ Ncond = {0}             ! Conductors per coil\n".format(Ncond))
        fo.write("$ Cp = {0}                ! Parallel paths\n".format(Cp))
        fo.write("$ Is = {0}                ! Stator current [A]\n".format(0.0))
        fo.write("$ Aaxis = {0}             ! Axis Coil A [deg]\n".format(0.0))
        fo.write("$ Carea = {0}             ! Coil Side Conductor Area [m2]\n".format(Swire))

        for mm in range(1, No_Magnets + 1):
            fo.write("$ Mangle{0} = {1}      ! Magnetization Angle [deg]\n".format(mm, round(Mangle[mm - 1], 2)))

        fo.write("$ Nsteps = {0}            !\n".format(2))
        fo.write("$ StepDegrees = {0}       !\n".format(degrees_step))
        fo.write("$ DegreesPerSec = WM*180.0/pi  !\n")
        fo.write("$ RotorInitPos = Aaxis - 360 / (4*PP) + {}!\n".format(round(rotor_init_pos, 2)))

        fo.write("\nHeader\n"
                 "\tCHECK KEYWORDS Warn\n"
                 "\tMesh DB \"{0}\"\n"
                 "\tInclude Path \".\"\n"
                 "\tResults Directory \"{1}\"\n"
                 "End\n".format(elmermesh_folder, elmermesh_folder))

        fo.write("\nConstants\n"
                 "\tPermittivity of Vacuum = 8.8542e-12\n"
                 "End\n")

        fo.write("\nSimulation\n"
                 "\tMax Output Level = 4\n"
                 "\tCoordinate System = Cartesian 2D\n"
                 "\tCoordinate Scaling = {0}\n"
                 "\tSimulation Type = Transient\n"
                 "\tTimestepping Method = BDF\n"
                 "\tBDF Order = 2\n"
                 #                 "\tTimestep Sizes = $ (StepDegrees / DegreesPerSec)  ! sampling time\n"
                 #                 "\tTimestep Intervals = $ Nsteps              ! steps\n"
                 #                 "\tOutput Intervals = 1\n"
                 "\tTimestep Sizes({1}) = {2}\n"
                 "\tTimestep Intervals({1}) = {3}\n"
                 "\tUse Mesh Names = Logical True\n"
                 "End\n".format(1.0, timelen, timesize_str[1:-1], timeinterval_str[1:-1]))

        fo.write("\n!--- MATERIALS ---\n")
        fo.write("Material 1\n"
                 "\tName = \"Air\"\n"
                 "\tRelative Permeability = 1\n"
                 "\tElectric Conductivity = 0\n"
                 "End\n")

        fo.write("\nMaterial 2\n"
                 "\tName = \"Insulation\"\n"
                 "\tRelative Permeability = 1\n"
                 "\tElectric Conductivity = 0\n"
                 "End\n")

        fo.write("\nMaterial 3\n"
                 "\tName = \"StatorMaterial\"\n"
                 "\tInclude \"{0}\"\n"
                 "End\n".format(stator_mat_file))

        fo.write("\nMaterial 4\n"
                 "\tName = \"RotorMaterial\"\n"
                 "\tInclude \"{0}\"\n"
                 "End\n".format(rotor_mat_file))

        winding_temp = 20.0  # Fixed for Now
        rho20 = machine.stator.winding.conductor.cond_mat.elec.rho
        kt = 0.01  # Br Temperature Coefficient fixed for now
        rho = rho20 * (1 + kt * (winding_temp - 20.0))
        conductivity = 1.0 / rho

        fo.write("\nMaterial 5\n"
                 "\tName = \"Copper\"\n"
                 "\tRelative Permeability = 1\n"
                 "\tElectric Conductivity = {0}\n"
                 "End\n".format(round(conductivity, 2)))

        magnets_per_pole = No_Magnets  # TO-DO: Assumes only one pole drawn
        for m in range(1, magnets_per_pole + 1):
            mat_number = 5 + m
            if magnetization_type == "parallel":
                fo.write("\nMaterial {0}\n"
                         "\tName = \"PM_{1}\"\n"
                         "\tRelative Permeability = {2}\n"
                         "\tMagnetization 1 = Variable time, timestep size\n"
                         "\t\tReal MATC  \"H_PM*cos(WM*(tx(0)-tx(1)) + {3}*pi/PP + {3}*pi + Aaxis*pi/180 + (Mangle{1}*pi/180))\"\n"
                         "\tMagnetization 2 = Variable time, timestep size\n"
                         "\t\tReal MATC \"H_PM*sin(WM*(tx(0)-tx(1)) + {3}*pi/PP + {3}*pi + Aaxis*pi/180 + (Mangle{1}*pi/180))\"\n"
                         "\tElectric Conductivity = {4}\n"
                         "End\n".format(mat_number, m, magnet_permeability,
                                        int((m - 1) / magnets_per_pole), round(conductivity_m, 2)))
            elif magnetization_type == "radial":
                fo.write("\nMaterial {0}\n"
                         "\tName = \"PM_{1}\"\n"
                         "\tRelative Permeability = {2}\n"
                         "\tMagnetization 1 = Variable Coordinate\n"
                         "\t\tReal MATC  \"H_PM*cos(atan2(tx(1),tx(0)) + {3}*pi)\"\n"
                         "\tMagnetization 2 = Variable Coordinate\n"
                         "\t\tReal MATC \"H_PM*sin(atan2(tx(1),tx(0)) + {3}*pi)\"\n"
                         "\tElectric Conductivity = {4}\n"
                         "End\n".format(mat_number, m, magnet_permeability, m - 1,
                                        round(conductivity_m, 2)))
            elif magnetization_type == "perpendicular":
                fo.write("\nMaterial {0}\n"
                         "\tName = \"PM_{1}\"\n"
                         "\tRelative Permeability = {2}\n"
                         "\tMagnetization 1 = Variable time, timestep size\n"
                         "\t\tReal MATC  \"H_PM*cos(WM*(tx(0)-tx(1)) + {3}*pi/PP + {3}*pi + Aaxis*pi/180 + (Mangle{1}*pi/180))\"\n"
                         "\tMagnetization 2 = Variable time, timestep size\n"
                         "\t\tReal MATC \"H_PM*sin(WM*(tx(0)-tx(1)) + {3}*pi/PP + {3}*pi + Aaxis*pi/180 + (Mangle{1}*pi/180))\"\n"
                         "\tElectric Conductivity = {4}\n"
                         "End\n".format(mat_number, m, magnet_permeability,
                                        int((m - 1) / magnets_per_pole), round(conductivity_m, 2)))
            else:
                fo.write("\nMaterial {0}\n"
                         "\tName = \"PM_{1}\"\n"
                         "\tRelative Permeability = {2}\n"
                         "\tElectric Conductivity = {4}\n"
                         "End\n".format(mat_number, m, magnet_permeability, round(conductivity_m, 2)))

        fo.write("\n!--- BODY FORCES ---\n")

        # fo.write("Body Force 1\n"
        #          "\tName = \"BodyForce_Rotation\"\n"
        #          "\t$omega = (180/pi)*WM\n"
        #          "\tMesh Rotate 3 = Variable time, timestep size\n"
        #          "\t\tReal MATC \"omega*(tx(0)-tx(1)) + RotorInitPos\"\n"
        #          "End\n")
        fo.write("Body Force 1\n"
                 "\tName = \"BodyForce_Rotation\"\n"
                 "\tMesh Rotate 3 = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], angle[tt] * 180.0 / pi))
        fo.write("\tEnd\n"
                 "End\n")

        # fo.write("Body Force 2\n"
        #          "\tName = \"J_A_PLUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) + Gamma)\"\n"
        #          "End\n".format(Ncond_Aplus))

        # fo.write("Body Force 3\n"
        #          "\tName = \"J_A_MINUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"-(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) + Gamma)\"\n"
        #          "End\n".format(Ncond_Aminus))

        # fo.write("Body Force 4\n"
        #          "\tName = \"J_B_PLUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Bplus))
        #
        # fo.write("Body Force 5\n"
        #          "\tName = \"J_B_MINUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"-(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Bminus))
        #
        # fo.write("Body Force 6\n"
        #          "\tName = \"J_C_PLUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 2*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Cplus))
        #
        # fo.write("Body Force 7\n"
        #          "\tName = \"J_C_MINUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"-(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 2*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Cminus))
        #
        # fo.write("Body Force 8\n"
        #          "\tName = \"J_D_PLUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 3*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Dplus))
        #
        # fo.write("Body Force 9\n"
        #          "\tName = \"J_D_MINUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"-(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 3*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Dminus))
        #
        # fo.write("Body Force 10\n"
        #          "\tName = \"J_E_PLUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 4*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Eplus))
        #
        # fo.write("Body Force 11\n"
        #          "\tName = \"J_E_MINUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"-(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 4*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Eminus))
        #
        # fo.write("Body Force 12\n"
        #          "\tName = \"J_F_PLUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 5*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Fplus))
        #
        # fo.write("Body Force 13\n"
        #          "\tName = \"J_F_MINUS\"\n"
        #          "\tCurrent Density = Variable time, timestep size\n"
        #          "\t\tReal MATC \"-(Is/Carea) * ({0}/Cp) * sin(WE * (tx(0)-tx(1)) - 5*Shift + Gamma)\"\n"
        #          "End\n".format(Ncond_Fminus))

        fo.write("Body Force 2\n"
                 "\tName = \"J_A_PLUS\"\n"
                 "\tCurrent Density = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], Is[0, tt]))
        fo.write("\tEnd\n"
                 "End\n")

        fo.write("Body Force 3\n"
                 "\tName = \"J_A_MINUS\"\n"
                 "\tCurrent Density = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], -Is[0, tt]))
        fo.write("\tEnd\n"
                 "End\n")

        fo.write("Body Force 4\n"
                 "\tName = \"J_B_PLUS\"\n"
                 "\tCurrent Density = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], Is[1, tt]))
        fo.write("\tEnd\n"
                 "End\n")

        fo.write("Body Force 5\n"
                 "\tName = \"J_B_MINUS\"\n"
                 "\tCurrent Density = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], -Is[1, tt]))
        fo.write("\tEnd\n"
                 "End\n")

        fo.write("Body Force 6\n"
                 "\tName = \"J_C_PLUS\"\n"
                 "\tCurrent Density = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], Is[2, tt]))
        fo.write("\tEnd\n"
                 "End\n")

        fo.write("Body Force 7\n"
                 "\tName = \"J_C_MINUS\"\n"
                 "\tCurrent Density = Variable time\n"
                 "\t\tReal\n")
        for tt in range(0, timelen + 1):
            fo.write("\t\t{:.2e}\t\t{:.3f}\n".format(time[tt], -Is[2, tt]))
        fo.write("\tEnd\n"
                 "End\n")

        fo.write("\n!--- BODIES ---\n")
        for k, v in bodies.items():
            bid = bodies[k]['id']
            beq = bodies[k]['eq']
            bmat = bodies[k]['mat']
            bf = bodies[k]['bf']
            btg = bodies[k]['tg']
            fo.write("Body {0}\n"
                     "\tName = {1}\n"
                     "\tEquation = {2}\n"
                     "\tMaterial = {3}\n".format(bid, k, beq, bmat))
            if bf is not None:
                fo.write("\tBody Force = {0}\n".format(bf))
            if btg is not None:
                fo.write("\tTorque Groups = Integer {0}\n".format(btg))
            if k == "SB_INT":
                fo.write("\tR Inner = Real {0}\n"
                         "\tR Outer = Real {1}\n".format(ror, sir))
            fo.write("End\n\n")

        fo.write("Equation 1\n"
                 "\tName = \"Model_Domain\"\n"
                 "\tActive Solvers(6) = 1 2 3 4 5 6\n"
                 "End\n")

        fo.write("\n!--- SOLVERS ---\n")
        fo.write("Solver 1\n"
                 "\tExec Solver = Before Timestep\n"
                 "\tEquation = MeshDeform\n"
                 "\tProcedure = \"RigidMeshMapper\" \"RigidMeshMapper\"\n"
                 "End\n")

        fo.write("\nSolver 2\n"
                 "\tEquation = MgDyn2D\n"
                 "\tProcedure = \"MagnetoDynamics2D\" \"MagnetoDynamics2D\"\n"
                 "\tExec Solver = Always\n"
                 "\tVariable = A\n")
        fo.write("\tNonlinear System Convergence Tolerance = {0}\n".format(1e-6))
        fo.write("\tNonlinear System Max Iterations = {0}\n".format(100))
        fo.write("\tNonlinear System Min Iterations = {0}\n".format(1))
        fo.write("\tNonlinear System Newton After Iterations = {0}\n".format(5))
        fo.write("\tNonlinear System Relaxation Factor = {0}\n".format(0.9))
        fo.write(
            "\tNonlinear System Convergence Without Constraints = {0}\n".format("Logical True"))
        fo.write("\tExport Lagrange Multiplier = {0}\n".format("Logical True"))
        fo.write("\tLinear System Abort Not Converged = {0}\n".format("Logical False"))
        fo.write("\tLinear System Solver = {0}\n".format("Direct"))
        fo.write("\tLinear System Direct Method = {0}\n".format("umfpack"))
        fo.write("\tOptimize Bandwidth = {0}\n".format("Logical True"))
        fo.write("\tLinear System Preconditioning =  {0}\n".format("ILU2"))
        fo.write("\tLinear System Max Iterations =  {0}\n".format(5000))
        fo.write("\tLinear System Residual Output =  {0}\n".format(20))
        fo.write("\tLinear System Convergence Tolerance =  {0}\n".format(1e-7))
        fo.write("\tMortar BCs Additive =  {0}\n".format("Logical True"))
        fo.write("End\n")

        fo.write("\nSolver 3\n"
                 "\tExec Solver = Always\n"
                 "\tEquation = CalcFields\n"
                 "\tPotential Variable = \"A\"\n"
                 "\tProcedure = \"MagnetoDynamics\" \"MagnetoDynamicsCalcFields\"\n"
                 "\tCalculate Nodal Forces = Logical True\n"
                 "\tCalculate Magnetic Vector Potential = Logical True\n"
                 "\tCalculate Winding Voltage = Logical True\n"
                 "\tCalculate Current Density = Logical True\n"
                 "\tCalculate Maxwell Stress = Logical True\n"
                 "\tCalculate JxB = Logical True\n"
                 "\tCalculate Magnetic Field Strength = Logical True\n"
                 "End\n")

        fo.write("\nSolver 4\n"
                 "\tExec Solver = After Timestep\n"
                 "\tProcedure = \"ResultOutputSolve\" \"ResultOutputSolver\"\n"
                 "\tOutput File Name = \"{0}\"\n"
                 "\tVtu Format = True\n"
                 "\tBinary Output = True\n"
                 "\tSingle Precision = True\n"
                 "\tSave Geometry Ids = True\n"
                 "\tShow Variables = True\n"
                 "End\n".format("step"))

        fo.write("\nSolver 5\n"
                 "\tExec Solver = After Timestep\n"
                 "\tEquation = SaveLine\n"
                 "\tFilename = \"{0}\"\n"
                 "\tProcedure = \"SaveData\" \"SaveLine\"\n"
                 "\tVariable 1 = Magnetic Flux Density 1\n"
                 "\tVariable 2 = Magnetic Flux Density 2\n"
                 "\tVariable 3 = Magnetic Flux Density 3\n"
                 "\tVariable 4 = Magnetic Flux Density e 1\n"
                 "\tVariable 5 = Magnetic Flux Density e 2\n"
                 "\tVariable 6 = Magnetic Flux Density e 3\n"
                 "End\n".format("lines.dat"))

        fo.write("\nSolver 6\n"
                 "\tExec Solver = After Timestep\n"
                 "\tFilename = \"{0}\"\n"
                 "\tProcedure = \"SaveData\" \"SaveScalars\"\n"
                 "\tShow Norm Index = 1\n"
                 "End\n".format("scalars.dat"))

        fo.write("\n!--- BOUNDARIES ---\n")
        for k, v in boundaries.items():
            if k == "VP0_BOUNDARY":
                fo.write("Boundary Condition {0}\n"
                         "\tName = {1}\n"
                         "\tA = Real 0\n"
                         "End\n\n".format(v, k))
            elif k == "MASTER_STATOR_BOUNDARY":
                for k1, v1 in boundaries.items():
                    if k1 == "SLAVE_STATOR_BOUNDARY":
                        slave = v1
                        break
                if not self.is_periodicity_a:
                    fo.write("Boundary Condition {0}\n"
                             "\tName = {1}\n"
                             "\tMortar BC = Integer {2}\n"
                             "\tMortar BC Static = Logical True\n"
                             "\tRadial Projector = Logical True\n"
                             "\tGalerkin Projector = Logical True\n"
                             "End\n\n".format(v, k, slave))
                else:
                    fo.write("Boundary Condition {0}\n"
                             "\tName = {1}\n"
                             "\tMortar BC = Integer {2}\n"
                             "\tMortar BC Static = Logical True\n"
                             "\tAnti Radial Projector = Logical True\n"
                             "\tGalerkin Projector = Logical True\n"
                             "End\n\n".format(v, k, slave))
            elif k == "MASTER_ROTOR_BOUNDARY":
                for k1, v1 in boundaries.items():
                    if k1 == "SLAVE_ROTOR_BOUNDARY":
                        slave = v1
                        break
                if not self.is_periodicity_a:
                    fo.write("Boundary Condition {0}\n"
                             "\tName = {1}\n"
                             "\tMortar BC = Integer {2}\n"
                             "\tMortar BC Static = Logical True\n"
                             "\tRadial Projector = Logical True\n"
                             "\tGalerkin Projector = Logical True\n"
                             "End\n\n".format(v, k, slave))
                else:
                    fo.write("Boundary Condition {0}\n"
                             "\tName = {1}\n"
                             "\tMortar BC = Integer {2}\n"
                             "\tMortar BC Static = Logical True\n"
                             "\tAnti Radial Projector = Logical True\n"
                             "\tGalerkin Projector = Logical True\n"
                             "End\n\n".format(v, k, slave))
            elif k == "SB_STATOR_BOUNDARY":
                for k1, v1 in boundaries.items():
                    if k1 == "SB_ROTOR_BOUNDARY":
                        slave = v1
                        break
                if not self.is_periodicity_a:
                    fo.write("Boundary Condition {0}\n"
                             "\tName = {1}\n"
                             "\tMortar BC = Integer {2}\n"
                             "\tRotational Projector = Logical True\n"
                             "\tGalerkin Projector = Logical True\n"
                             "End\n\n".format(v, k, slave))
                else:
                    fo.write("Boundary Condition {0}\n"
                             "\tName = {1}\n"
                             "\tMortar BC = Integer {2}\n"
                             "\tAnti Rotational Projector = Logical True\n"
                             "\tGalerkin Projector = Logical True\n"
                             "End\n\n".format(v, k, slave))
            elif k == "AIRGAP_ARC_BOUNDARY":
                fo.write("Boundary Condition {0}\n"
                         "\tName = {1}\n"
                         "\tSave Line = True\n"
                         "End\n\n".format(v, k))
            else:
                fo.write("Boundary Condition {0}\n"
                         "\tName = {1}\n"
                         "End\n\n".format(v, k))

    # setup Elmer solver
    # ElmerSolver v8.4 must be installed and in the PATH

    elmer_settings = join(project_name, "pyleecan_elmer.sif")
    ElmerSolver_binary = get_path_binary("ElmerSolver")
    cmd_elmersolver = [
        ElmerSolver_binary,
        elmer_settings,
    ]
    self.get_logger().info("Calling ElmerSolver: " + ' '.join(map(str, cmd_elmersolver)))
    elmersolver = subprocess.Popen(
        cmd_elmersolver, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    (stdout, stderr) = elmersolver.communicate()
    elmersolver.wait()
    self.get_logger().info(stdout.decode("UTF-8"))
    if elmersolver.returncode != 0:
        self.get_logger().info("ElmerSolver [Error]: " + stderr.decode('UTF-8'))
        return False
    elmersolver.terminate()
    self.get_logger().info("ElmerSolver call complete!")

    #####################################################
    # This should be done in get_meshsolution
    # self.get_meshsolution()

    from ....Classes.MeshSolution import MeshSolution
    from ....Classes.MeshVTK import MeshVTK
    meshsol = MeshSolution(label="Elmer MagnetoDynamics")
    if not self.is_get_mesh or not self.is_save_FEA:
        self.get_logger().info("MagElmer: MeshSolution is not stored by request.")

    meshvtk = MeshVTK(path=elmermesh_folder, name="step_t0001", format="vtu")
    meshsol.mesh = [meshvtk]

    from meshio import read
    result_filename = join(elmermesh_folder, "step_t0001.vtu")
    meshsolvtu = read(result_filename)
    pt_data = meshsolvtu.point_data
    cell_data = meshsolvtu.cell_data
    from numpy import arange
    indices = arange(meshsolvtu.points.shape[0])
    from SciDataTool import Data1D
    Indices = Data1D(name="indice", values=indices, is_components=True)

    store_dict = {
        "a": {
            "name": "a",
            "unit": "Wb",
            "symbol": "a",
            "norm": 1e-3,
        },
        "b": {
            "name": "magnetic flux density",
            "unit": "T",
            "symbol": "b",
            "norm": 1,
        }
    }
    comp_ext = ["x", "y", "z"]
    sol_list = []
    for key, value in pt_data.items():
        if key in store_dict.keys():
            siz = value.shape[1]
            if siz > 3:
                print("Some Message")
                siz = 3
            components = []
            comp_name = []
            for i in range(siz):
                if siz == 1:
                    ext = ""
                else:
                    ext = comp_ext[i]

                data = DataTime(
                    name = store_dict
                )

    output.mag.meshsolution = meshsol

    ####################################################

    Na = angle.size
    Nt = time.size

    # Loading parameters for readibility
    L1 = output.simu.machine.stator.comp_length()
    save_path = self.get_path_save(output)
    # FEM_dict = output.mag.FEM_dict
    #
    if (
            hasattr(output.simu.machine.stator, "winding")
            and output.simu.machine.stator.winding is not None
    ):
        qs = output.simu.machine.stator.winding.qs  # Winding phase number
        Phi_wind_stator = zeros((Nt, qs))
    else:
        Phi_wind_stator = None

    # Initialize results matrix
    Br = zeros((Nt, Na))
    Bt = zeros((Nt, Na))
    Bz = zeros((Nt, Na))
    Tem = zeros((Nt))
    # Phi_wind_stator = zeros((Nt, qs))

    # compute the data for each time step
    # TODO Other than FEMM, in Elmer I think it's possible to compute
    #      all time steps at once
    self.get_logger().debug("Solving Simulation")

    # run the computation
    if self.nb_worker > 1:
        # TODO run solver in parallel
        pass
    else:
        # TODO run solver 'normal'
        pass

    # get the air gap flux result
    # TODO add function (or method)
    # ii -> Time, jj -> Angle
    # Br[ii, jj], Bt[ii, jj] = get_airgap_flux()

    # get the torque
    # TODO add function (or method)
    # Tem[ii] = comp_Elmer_torque(FEM_dict, sym=sym)

    # flux linkage computation
    # if Phi_wind_stator is not None:
    #     # TODO
    #     # Phi_wind[ii, :] = comp_Elmer_Phi_wind()
    #     pass

    return Br, Bt, Bz, Tem, Phi_wind_stator