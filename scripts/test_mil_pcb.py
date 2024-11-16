from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time
# import random


# ---------------------------------------------------------------------------- #
def bool_to_color_str(same: bool) -> str:
	if same:
		return utils.bcolors.OKGREEN + "SUCCESS" + utils.bcolors.ENDC
	else:
		return utils.bcolors.FAIL + "FAILURE" + utils.bcolors.ENDC


def test_do_di(hil: HIL):
	hil_do = hil.dout("Millan", "HIL_DO") # A1
	hil_di = hil.din("Millan", "HIL_DI")  # A2

	for _i in range(3):
		for state in [0, 1]:
			hil_do.state = state

			time.sleep(0.2)

			hil_di_state = hil_di.state
			same = hil_di_state == state

			print(f"{hil_di_state} == {state} -> {bool_to_color_str(same)}")

			input("Press Enter to continue...")

			time.sleep(0.5)

		print()

def test_ao_ai(hil: HIL):
	hil_ao = hil.aout("Millan", "HIL_AO") # DAC1
	hil_ai = hil.ain("Millan", "HIL_AI")  # A4

	for _i in range(3):
		# random_voltage = random.uniform(0.0, 5.0)
		for voltage in [0.34]:
			# 5 * 255 / (2^12 - 1) = 0.31135531135
			# 5 * 0.1 / 0.31135531135 = 1.60588235297
			hil_ao.state = voltage
			time.sleep(0.2)

			hil_ai_voltage = hil_ai.state
			within = abs(hil_ai_voltage - voltage) < 0.1

			print(f"{hil_ai_voltage:1.2f} == {voltage:1.2f} -> {bool_to_color_str(within)}")

			time.sleep(0.5)

		print()

def test_rly(hil: HIL):
	hil_do = hil.dout("Millan", "HIL_DO")   # A1
	hil_rly = hil.dout("Millan", "HIL_RLY") # RLY1
	hil_di  = hil.din("Millan", "HIL_DI")   # A2

	# A1 -> RLY1+
	# RLY1- -> A2

	for _i in range(3):
		for do_state in [0, 1]:
			for rly_state in [0, 1]:
				hil_do.state = do_state
				hil_rly.state = rly_state

				expected_state = do_state and rly_state

				time.sleep(0.2)

				hil_di_state = hil_di.state
				same = hil_di_state == expected_state

				print(f"{hil_di_state} == {expected_state} -> {bool_to_color_str(same)}")

				# input("Press Enter to continue...")

				time.sleep(0.5)

# TODO: test POT
# TODO: test PWM?
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
# ONLY RUN ONE TEST AT A TIME AS THEY REFERENCE OVERLAPPING PINS
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_mil_pcb.json")
	hil.load_pin_map("mil_pcb_net_map.csv", "stm32f407_pin_map.csv")
	
	# test_do_di(hil)
	# test_ao_ai(hil)
	test_rly(hil)

	hil.shutdown()