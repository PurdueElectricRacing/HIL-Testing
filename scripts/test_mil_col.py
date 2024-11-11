from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time


# ---------------------------------------------------------------------------- #
def same_to_color_str(same: bool) -> str:
	if same:
		return utils.bcolors.OKGREEN + "SUCCESS" + utils.bcolors.ENDC
	else:
		return utils.bcolors.FAIL + "FAILURE" + utils.bcolors.ENDC


def test(hil: HIL):
	hil_out = hil.dout("Millan", "HIL_OUT")
	hil_ain = hil.ain("Millan", "HIL_AIN")
	hil_din = hil.din("Millan", "HIL_DIN")

	for _i in range(3):
		for state in [0, 1]:
			print(f"\nHIL_OUT: {state}")
			hil_out.state = state
			time.sleep(0.5)

			hil_din_state = hil_din.state
			din_same = hil_din_state == state
			print(f"HIL_DIN: {hil_din_state} == {state} -> {same_to_color_str(din_same)}")

			hil_ain_state = hil_ain.state
			ain_target = state * 5.0
			ain_same = abs(hil_ain_state - ain_target) < 0.1
			print(f"HIL_AIN: {hil_ain_state} == {ain_target} -> {same_to_color_str(ain_same)}")

			time.sleep(1)

		print()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_millan.json")
	hil.load_pin_map("millan_net_map.csv", "stm32f407_pin_map.csv")
	
	test(hil)

	hil.shutdown()