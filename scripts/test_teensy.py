from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time


import pytest_check as check
import pytest

# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    hil_instance.load_config("config_teensy.json")
    hil_instance.load_pin_map("teensy_net_map.csv", "stm32f407_pin_map.csv")

    # hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_mux_do(hil: HIL):
    # Outputs (HIL writes)
    do3 = hil.aout("HIL2", "D03")

    # Inputs (HIL reads)
    mux_5v_3 = hil.aout("HIL2", "5vMUX_3")
    dai5 = hil.ain("HIL2", "DAI2", 5)

    # Setup initial state
    do3.state = 1

    while True:
        mux_read = mux_5v_3.state
        dai_read = dai5.state
        print(f"Read: \t{mux_read} \t{dai_read}")
# ---------------------------------------------------------------------------- #
