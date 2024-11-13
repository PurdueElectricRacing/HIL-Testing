from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time
import random


# ---------------------------------------------------------------------------- #
def within_to_color_str(same: bool) -> str:
	if same:
		return utils.bcolors.OKGREEN + "SUCCESS" + utils.bcolors.ENDC
	else:
		return utils.bcolors.FAIL + "FAILURE" + utils.bcolors.ENDC


def test(hil: HIL):
	hil_ao = hil.ao("Millan", "HIL_AO") # HIL writes
	hil_ai = hil.ai("Millan", "HIL_AI") # HIL reads

	for _i in range(3):
		random_voltage = random.uniform(0.0, 5.0)
		for voltage in [0.0, 1.0, 2.5, 3.3, 5.0, random_voltage]:
			hil_ao.voltage = voltage

			time.sleep(0.2)

			hil_ai_voltage = hil_ai.voltage
			ai_within = abs(hil_ai_voltage - voltage) < 0.1

			print(f"HIL_AI: {hil_ai_voltage:1.2f} == {voltage:1.2f} -> {within_to_color_str(ai_within)}")
			

			time.sleep(0.5)

		print()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_mil_dac.json")
	hil.load_pin_map("mil_dac_net_map.csv", "stm32f407_pin_map.csv")
	
	test(hil)

	hil.shutdown()