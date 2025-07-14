"""
Set 2 DACs to 2v, then create a deviation in DAC2 by 20% (2.4v)
Then check if a fault is thrown over the CAN bus.
"""

from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time


import pytest_check as check
import pytest

DAC_VOLTAGE = 2.0
BASE_WAIT = 1 # seconds
DAC2_DEVIATION = 0.2 # 20%
WAIT_FOR_CAN = 0.5 # seconds
POLL_INTERVAL = 0.05


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    hil_instance.load_config("config_irving.json")
    hil_instance.load_pin_map("irving_net_map.csv", "stm32f407_pin_map.csv")

    # hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_fault(hil: HIL):
    # Outputs (HIL writes)
    dac1 = hil.aout("Irving", "DAC1")
    dac2 = hil.aout("Irving", "DAC2")

    # Inputs (HIL reads)
    fault_can = hil.can("Irving", "FAULT_CAN")

    # Setup initial state
    dac1.state = DAC_VOLTAGE
    dac2.state = DAC_VOLTAGE

    time.sleep(BASE_WAIT)

    # Create deviation in DAC2
    dac2.state = DAC_VOLTAGE * (1 + DAC2_DEVIATION)

    # Can has 0.5 sec to have can.state != None
    start = time.time()
    can_state = None

    while time.time() - start < WAIT_FOR_CAN:
        can_state = fault_can.state
        if can_state is not None:
            break
        time.sleep(POLL_INTERVAL)

    check.is_not_none(can_state, "Should throw fault")
# ---------------------------------------------------------------------------- #
