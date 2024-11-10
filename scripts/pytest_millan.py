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

	hil_instance.load_config("config_millan.json")
	hil_instance.load_pin_map("millan_net_map.csv", "stm32f407_pin_map.csv")

	yield hil_instance

	hil_instance.shutdown()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_do_di(hil: HIL):
	hil_out = hil.dout("Millan", "HIL_OUT")
	hil_in = hil.din("Millan", "HIL_IN")

	for _i in range(3):
		for state in range(2): # 0, 1
			hil_out.state = state
			hil_in_state = hil_in.state
			check.equal(hil_in_state, state	, f"Expected HIL_IN to be {state}, got {hil_in_state}")

			time.sleep(1)
# ---------------------------------------------------------------------------- #