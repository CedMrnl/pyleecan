# -*- coding: utf-8 -*-
from os.path import join

import matplotlib.pyplot as plt
from numpy import array, pi, zeros

from pyleecan.Classes.Frame import Frame
from pyleecan.Classes.LamSlotWind import LamSlotWind
from pyleecan.Classes.LamSquirrelCage import LamSquirrelCage
from pyleecan.Classes.MachineDFIM import MachineDFIM
from pyleecan.Classes.Shaft import Shaft
from pyleecan.Classes.VentilationCirc import VentilationCirc
from pyleecan.Classes.VentilationPolar import VentilationPolar
from pyleecan.Classes.VentilationTrap import VentilationTrap
from pyleecan.Classes.Winding import Winding
from pyleecan.Classes.WindingUD import WindingUD
from pyleecan.Classes.WindingCW2LT import WindingCW2LT
from pyleecan.Classes.WindingDW2L import WindingDW2L
from pyleecan.Classes.MatMagnetics import MatMagnetics
from pyleecan.Classes.SlotW26 import SlotW26

from Tests import save_plot_path as save_path
from Tests.Plot.LamWind import wind_mat


"""unittest for Lamination with winding plot"""


def test_Lam_Wind_26_wind_22():
    """Test machine plot with Slot 26 and winding rad=2, tan=2
    """
    print("\nTest plot Slot 26")
    plt.close("all")
    test_obj = MachineDFIM()
    test_obj.rotor = LamSlotWind(
        Rint=0.2, Rext=0.5, is_internal=True, is_stator=False, L1=0.9, Nrvd=2, Wrvd=0.05
    )
    test_obj.rotor.axial_vent = [
        VentilationCirc(Zh=6, Alpha0=pi / 6, D0=60e-3, H0=0.35)
    ]
    test_obj.rotor.slot = SlotW26(
        Zs=6, W0=20e-3, R1=30e-3, R2=20e-3, H0=20e-3, H1=20e-3
    )
    test_obj.rotor.winding = WindingUD(user_wind_mat=wind_mat, qs=4, p=4, Lewout=60e-3)
    test_obj.rotor.mat_type.mag = MatMagnetics(Wlam=0.5e-3)
    test_obj.shaft = Shaft(Drsh=test_obj.rotor.Rint * 2, Lshaft=1)

    test_obj.stator = LamSlotWind(
        Rint=0.51,
        Rext=0.8,
        is_internal=False,
        is_stator=True,
        L1=0.9,
        Nrvd=2,
        Wrvd=0.05,
    )
    test_obj.stator.winding = WindingDW2L(qs=3, p=3)
    test_obj.stator.slot = SlotW26(
        Zs=18, W0=40e-3, R1=60e-3, R2=70e-3, H0=20e-3, H1=40e-3
    )
    test_obj.stator.mat_type.mag = MatMagnetics(Wlam=0.5e-3)
    test_obj.stator.winding.Lewout = 60e-3
    test_obj.frame = Frame(Rint=0.8, Rext=0.9, Lfra=1)

    test_obj.plot()
    fig = plt.gcf()
    fig.savefig(join(save_path, "test_Lam_Wind_s26_1-Machine.png"))
    # Rotor + Stator + 2 for frame + 1 for shaft
    assert len(fig.axes[0].patches) == 73

    test_obj.rotor.plot()
    fig = plt.gcf()
    fig.savefig(join(save_path, "test_Lam_Wind_s26_2-Rotor.png"))
    # 2 for lam + 6 vent + 4*Zs for wind
    assert len(fig.axes[0].patches) == 32

    test_obj.stator.plot()
    fig = plt.gcf()
    fig.savefig(join(save_path, "test_Lam_Wind_s26_3-Stator.png"))
    # 2 for lam + Zs*2 for wind
    assert len(fig.axes[0].patches) == 38

    tooth = test_obj.rotor.slot.get_surface_tooth()
    tooth.plot(color="r")
    fig = plt.gcf()
    fig.savefig(join(save_path, "test_Lam_Wind_s26_Tooth_in.png"))

    tooth = test_obj.stator.slot.get_surface_tooth()
    tooth.plot(color="r")
    fig = plt.gcf()
    fig.savefig(join(save_path, "test_Lam_Wind_s26_Tooth_out.png"))
