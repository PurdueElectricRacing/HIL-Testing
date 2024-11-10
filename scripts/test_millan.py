from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time


# ---------------------------------------------------------------------------- #
def test_do_di(hil: HIL):
	hil_out = hil.dout("Millan", "HIL_OUT")
	hil_in = hil.din("Millan", "HIL_IN")

	for _i in range(3):
		print("\nHIL_OUT: 0")
		hil_out.state = 0
		hil_in_state = hil_in.state
		same = hil_in_state == 0
		print(f"HIL_IN: {hil_in_state} == 0: {same}")

		time.sleep(3)

		print("\nHIL_OUT: 1")
		hil_out.state = 1
		hil_in_state = hil_in.state
		same = hil_in_state == 1
		print(f"HIL_IN: {hil_in_state} == 1: {same}")

		time.sleep(3)

		print()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_millan.json")
	hil.load_pin_map("millan_net_map.csv", "stm32f407_pin_map.csv")
	
	test_do_di(hil)

	hil.shutdown()