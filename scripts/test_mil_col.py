from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time


# ---------------------------------------------------------------------------- #
def test_collector(hil: HIL):
	mux_a = hil.dout("Collector", "MUX_A")      # A1
	mux_b = hil.dout("Collector", "MUX_B")      # A2
	mux_d = hil.dout("Collector", "MUX_C")      # A3
	
	mux_c = hil.dout("Collector", "MUX_D")      # RLY1: have to wire: 5V -> RLY1 -> MUX_D
	mux_c.state = 1 # turn on relay (it is inverted)

	temp_out = hil.ain("Collector", "TEMP_OUT") # A4

	tolerance_v    = 0.1 # volts
	current_res    = 9100.0 # ohms
	pullup_res     = 4700.0 # ohms
	# test_voltage   = 3.3 # volts
	pullup_voltage = 5 # volts
	num_therm      = 10

	test_voltage = (pullup_voltage / (current_res + pullup_res)) * current_res
	utils.log_warning(f"Test voltage: {test_voltage}")


	for thermistor in range(num_therm):
		print(f"\nPlace test input on thermistor {thermistor}.")
		input("Press Enter when ready...")

		for i in range(num_therm):
			# MUX (multiplexer) = choose which output to return from the thermistor based on the input
			# Like a giant switch statement (0 -> return thermistor 0, 1 -> return thermistor 1, etc.)
			# Encode the current thermistor into binary where each bit corresponds to each pin being high or low
			mux_a.state = i & 0x1
			mux_b.state = i & 0x2
			mux_c.state = not (i & 0x4) # relay is inverted
			mux_d.state = i & 0x8

			# Wait for relay
			time.sleep(0.1)

			temp_out_state = temp_out.state
			if i == thermistor: expected_voltage = test_voltage
			else:               expected_voltage = pullup_voltage
			within = abs(temp_out_state - expected_voltage) < tolerance_v
			
			if within: within_text = utils.bcolors.OKGREEN + "PASS" + utils.bcolors.ENDC
			else:      within_text = utils.bcolors.FAIL    + "FAIL" + utils.bcolors.ENDC

			if i == thermistor: print("- ", end="")

			print(f"({thermistor=}, {i=})  temp_out_state={temp_out_state:.1f} ?= expected_voltage={expected_voltage:.1f}  ->  {within_text}")
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
	hil = HIL()

	hil.load_config("config_mil_col.json")
	hil.load_pin_map("mil_col_net_map.csv", "stm32f407_pin_map.csv")
	
	test_collector(hil)

	hil.shutdown()