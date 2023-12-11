from pyleecan.Classes.SlotM11 import SlotM11
from pyleecan.Classes.SlotM12 import SlotM12
from pyleecan.Classes.SlotM13 import SlotM13
from pyleecan.Classes.SlotM14 import SlotM14
from pyleecan.Classes.SlotM15 import SlotM15
from pyleecan.Classes.SlotM16 import SlotM16


def select_magnet_rules(self, is_stator):
    """select step to add rules for magnet and convert the magnet

    Parameters
    ----------
    self : ConvertMC
        A ConvertMC object
    is_stator : bool
        True slot is in stator, False slot is in rotor

    """
    # set the machine or dict with the corect conversion of magnet to
    if self.is_P_to_other:
        self.convert_magnet_to_other()

    else:
        self.convert_magnet_to_P()

    # add the correct rule depending on the hole
    if isinstance(self.machine.rotor.slot, SlotM14) and self.machine.rotor.slot.H0 == 0:
        self.add_rule_surface_radial_slotM14()

    elif (
        isinstance(self.machine.rotor.slot, SlotM15) and self.machine.rotor.slot.H0 == 0
    ):
        self.add_rule_surface_parallel_slotM15()

    elif (
        isinstance(self.machine.rotor.slot, SlotM13) and self.machine.rotor.slot.H0 == 0
    ):
        self.add_rule_surface_breadloaf_slotM13()

    elif isinstance(self.machine.rotor.slot, SlotM11):
        self.add_rule_inset_radial_slotM11()

    elif (
        isinstance(self.machine.rotor.slot, SlotM15) and self.machine.rotor.slot.H0 != 0
    ):
        self.add_rule_inset_parallel_slotM15()

    elif isinstance(self.machine.rotor.slot, SlotM12):
        self.add_rule_inset_breadloaf_slotM12()

    elif isinstance(self.machine.rotor.slot, SlotM16):
        self.add_rule_spoke_slotM16()
