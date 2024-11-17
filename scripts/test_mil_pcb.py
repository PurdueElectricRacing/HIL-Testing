from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time
import random


# ---------------------------------------------------------------------------- #
def bool_to_color_str(same: bool) -> str:
	if same:
		return utils.bcolors.OKGREEN + "SUCCESS" + utils.bcolors.ENDC
	else:
		return utils.bcolors.FAIL + "FAILURE" + utils.bcolors.ENDC


def test_do_di(hil: HIL):
	hil_a1 = hil.dout("Millan", "HIL_A1") # DO -> HIL writes
	hil_a2 = hil.din ("Millan", "HIL_A2") # DI -> HIL reads

	for _i in range(3):
		for state in [0, 1]:
			hil_a1.state = state

			time.sleep(0.2)

			hil_di_state = hil_a2.state
			same = hil_di_state == state

			print(f"{hil_di_state} == {state} -> {bool_to_color_str(same)}")

			input("Press Enter to continue...")

			time.sleep(0.5)

		print()

def test_dac_ai(hil: HIL):
	hil_dac1 = hil.aout("Millan", "HIL_DAC1") # AO -> HIL writes
	hil_a4   = hil.ain ("Millan", "HIL_A3")   # AI -> HIL reads

	for _i in range(3):
		random_voltage = random.uniform(0.0, 5.0)
		voltages = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, random_voltage]
		for voltage in voltages:
			hil_dac1.state = voltage
			time.sleep(0.2)

			hil_ai_voltage = hil_a4.state
			within = abs(hil_ai_voltage - voltage) < 0.1

			print(f"{hil_ai_voltage:1.2f} == {voltage:1.2f} -> {bool_to_color_str(within)}")

			time.sleep(0.5)

		print()

def test_rly(hil: HIL):
	hil_a1   = hil.dout("Millan", "HIL_A1")   # DO -> HIL writes
	hil_rly1 = hil.dout("Millan", "HIL_RLY1") # DO -> HIL writes
	hil_a2   = hil.din ("Millan", "HIL_A2")   # DI -> HIL reads

	# A1 -> RLY1+
	# RLY1- -> A2

	for _i in range(3):
		for do_state in [0, 1]:
			for rly_state in [0, 1]:
				hil_a1.state = do_state
				hil_rly1.state = rly_state

				expected_state = do_state and rly_state

				time.sleep(0.2)

				hil_di_state = hil_a2.state
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
	# test_dac_ai(hil)
	test_rly(hil)

	hil.shutdown()