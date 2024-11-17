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
	hil_dacs = [hil.aout("Millan", f"HIL_DAC{i}") for i in range(1, 5)] # AO -> HIL writes
	hil_ais  = [hil.ain ("Millan", f"HIL_A{i}")   for i in range(1, 5)] # AI -> HIL reads

	for _i in range(3):
		for i in range(4):
			random_voltage = random.uniform(0.0, 5.0)
			voltages = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, random_voltage]
			for voltage in voltages:
				hil_dacs[i].state = voltage
				time.sleep(0.2)

				hil_ai_voltage = hil_ais[i].state
				within = abs(hil_ai_voltage - voltage) < 0.1

				print(f"{i}: {hil_ai_voltage:1.2f} == {voltage:1.2f} -> {bool_to_color_str(within)}")

				time.sleep(0.5)
			print()
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

				print(f"({do_state}, {rly_state}): {hil_di_state} == {expected_state} -> {bool_to_color_str(same)}")

				time.sleep(0.5)
		print()


def test_pwm(hil: HIL):
	hil_pwms = [hil.pwm("Millan", f"HIL_PWM{i}") for i in range(1, 5)] # PWM -> HIL writes
	hil_as   = [hil.ain("Millan", f"HIL_A{i}")   for i in range(1, 5)] # AI -> HIL writes

	for _i in range(3):
		for i in range(4):
			random_voltage = random.uniform(0.0, 5.0)
			voltages = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, random_voltage]
			for voltage in voltages:
				# voltage: [0.0, 5.0] -> pwm_value: [0, 255]
				pwm_value = int(voltage / 5.0 * 255)

				hil_pwms[i].state = pwm_value
				time.sleep(0.2)

				hil_ai_voltage = hil_as[i].state
				within = abs(hil_ai_voltage - voltage) < 0.1

				print(f"{i}: {hil_ai_voltage:1.2f} == {voltage:1.2f} -> {bool_to_color_str(within)}")

				time.sleep(0.5)
			print()
		print()

# TODO: test POT
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
# ONLY RUN ONE TEST AT A TIME AS THEY REFERENCE OVERLAPPING PINS
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_mil_pcb.json")
	hil.load_pin_map("mil_pcb_net_map.csv", "stm32f407_pin_map.csv")
	
	# test_do_di(hil)
	# test_dac_ai(hil)
	# test_rly(hil)
	# test_pwm(hil)

	hil.shutdown()