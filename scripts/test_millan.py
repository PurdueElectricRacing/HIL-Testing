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
		for state in range(2): # 0, 1
			print("\nHIL_OUT: 0")
			hil_out.state = state
			hil_in_state = hil_in.state
			same = hil_in_state == state
			print(f"HIL_IN: {state} == {hil_in_state}: {same}")

			time.sleep(1)

		print()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_do_ai(hil: HIL):
	hil_out = hil.dout("Millan", "HIL_OUT")
	hil_in = hil.ain("Millan", "HIL_IN")

	for _i in range(3):
		for state in range(2): # 0, 1
			print("\nHIL_OUT: 0")
			hil_out.state = state
			time.sleep(1)
			hil_in_state = hil_in.state

			target = state * 5.0
			same = abs(hil_in_state - target) < 0.1
			print(f"HIL_IN: {target} == {hil_in_state}: {same}")

			time.sleep(2)

		print()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_millan.json")
	hil.load_pin_map("millan_net_map.csv", "stm32f407_pin_map.csv")
	
	# test_do_di(hil)
	test_do_ai(hil)

	hil.shutdown()