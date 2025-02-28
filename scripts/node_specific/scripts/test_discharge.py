from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time
from scripts.common.constants.rules_constants import *
from scripts.common.constants.vehicle_constants import *

import pytest_check as check
import pytest


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    # TODO: new config file
    hil_instance.load_config("config_system_hil_attached.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("tsms_set, hv_plus_set, discharge_plus_expected", [
    (1, 0, 0), # TSMS low = relay open, HV+ low -> discharge disconnected (0)
    (0, 0, 0), # TSMS high = relay closed, HV+ low -> discharge connected but no voltage (0)
    (1, 1, 0), # TSMS low = relay open, HV+ high -> discharge disconnected (0)
    (0, 1, 1), # TSMS high = relay closed, HV+ high -> discharge connected with voltage (1)
])
def test_main_relay(hil, tsms_set, hv_plus_set, discharge_plus_expected):
    # HIL outputs (hil writes)
    tsms    = hil.dout("Discharge", "SDC15 - TSMS")
    hv_plus = hil.dout("Discharge", "HV+")

    # HIL inputs (hil reads)
    discharge_plus = hil.din("Discharge", "discharge+")

    tsms.state = tsms_set
    hv_plus.state = hv_plus_set
    time.sleep(0.1)

    message = f"TSMS: {tsms_set}, HV+: {hv_plus_set} -> Discharge+: {discharge_plus_expected}"
    check.equal(discharge_plus.state, discharge_plus_expected, message)
# ---------------------------------------------------------------------------- #
