from pyleecan.Classes.RuleComplex import RuleComplex


def add_rule_lamination(rule_list, is_stator):
    """Create and adapt all the rules related to lamination (lam radius,...)
    Extend rules_list within Converter object

    Parameters
    ----------
    self : ConvertMC
        A ConvertMC object
    is_stator : Bool
        A booleen to know, position in lamination
    """

    rule_list.append(RuleComplex(fct_name="add_duct_layer", folder="MotorCAD"))
