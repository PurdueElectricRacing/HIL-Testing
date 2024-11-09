from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time


# ---------------------------------------------------------------------------- #
def do_on_off(hil: HIL):
	# Outputs
	mux_a = hil.dout("Collector", "MUX_A")

	while True:
		mux_a.state = 1
		print("ON")
		time.sleep(5)

		mux_a.state = 0
		print("OFF")
		time.sleep(5)

	# # Inputs
	# temp_out = hil.ain("Collector", "TEMP_OUT")

	# for thermistor in range(num_therm):
	# 	print(f"\nPlace test input on thermistor {thermistor}.")
	# 	input("Press Enter when ready...")

	# 	for i in range(num_therm):
	# 		# MUX (multiplexer) = choose which output to return from the thermistor based on the input
	# 		# Like a giant switch statement (0 -> return thermistor 0, 1 -> return thermistor 1, etc.)
	# 		# Encode the current thermistor into binary where each bit corresponds to each pin being high or low
	# 		mux_a.state = i & 0x1
	# 		mux_b.state = i & 0x2
	# 		mux_c.state = i & 0x4
	# 		mux_d.state = i & 0x8
	# 		time.sleep(0.01)

	# 		temp_out_state = temp_out.state
	# 		if i == thermistor: expected_voltage = test_voltage
	# 		else:               expected_voltage = pullup_voltage
	# 		within = abs(temp_out_state - expected_voltage) < tolerance_v
			
	# 		if within: within_text = utils.bcolors.OKGREEN + "PASS" + utils.bcolors.ENDC
	# 		else:      within_text = utils.bcolors.FAIL + "FAIL" + utils.bcolors.ENDC

	# 		print(f"({thermistor=}, {i=})  temp_out_state={temp_out_state:.1f} ?= expected_voltage={expected_voltage:.1f}  ->  {within_text}")
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_collector_bench.json")
	hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")
	
	do_on_off(hil)

	hil.shutdown()