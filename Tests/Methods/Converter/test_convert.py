# -*- coding: utf-8 -*-

import pytest
from pyleecan.Classes.ConvertMC import ConvertMC
from pyleecan.Methods.Converter.ConvertMC.convert_to_P.convert_other_to_dict import (
    convert_other_to_dict,
)


path = "EMD240_v16.mot"


class Test_converter_mot(object):
    def test_convert(self):
        """check if dict are equal"""
        path = "/Users\LAP17\Documents\pyleecan\pyleecan\Methods\Converter\ConvertMC\Matlab_Test_2.mot"

        conv = ConvertMC()
        # conversion file in machine
        machine = conv.convert_to_P(path)

        # conversion machine in dict
        conv.convert_to_other(machine)
        dict_to_other = conv.other_dict
        # conversoin file in dict to compare
        conv.convert_other_to_dict(path)

        dict_to_mot = conv.other_dict

        # selection path and value in dict_to_other created after conversion, and compare this result with dict_to_mot, a file .mot convert in dict
        for path_dict in dict_to_other:
            # find path to select value

            # temp_dict is dict in dict
            temp_dict = dict_to_other[path_dict]

            for path_2 in temp_dict:
                value = temp_dict[path_2]

                # compare value
                value_mot = dict_to_mot[path_dict][path_2]
                msg = f"{value} is different {value_mot} (ref)"
                if not isinstance(value, str):
                    assert abs(value_mot) == pytest.approx(value), msg

                elif value != value_mot:
                    raise ValueError(f"{value} is different {value_mot} (ref)")


if __name__ == "__main__":
    a = Test_converter_mot()
    a.compare(path)
    print("Test Done")
