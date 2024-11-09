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

    hil_instance.load_config("config_collector_bench.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")
    
    # hil_instance.init_can()
    
    yield hil_instance
    
    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_collector(hil):
    # Begin the test
    # hil.start_test(test_collector.__name__)

    # Outputs
    m1 = hil.dout("Collector", "MUX_A")
    m2 = hil.dout("Collector", "MUX_B")
    m3 = hil.dout("Collector", "MUX_C")
    m4 = hil.dout("Collector", "MUX_D")

    # Inputs
    to = hil.ain("Collector", "TEMP_OUT")

    tolerance_v    = 0.1 # volts
    current_res    = 9100.0 # ohms
    pullup_res     = 4700.0 # ohms
    test_voltage   = 3.3 # volts
    pullup_voltage = 5 # volts
    num_therm      = 10

    test_voltage = (pullup_voltage / (current_res + pullup_res)) * current_res

    utils.log_warning(test_voltage)

    for thermistor in range(num_therm):
        print(f"Place test input on thermistor {thermistor}. Press Enter when ready")
        input("")

        for i in range(num_therm):
            # MUX (multiplexer) = choose which output to return from the thermistor based on the input
            # Like a giant switch statement (0 -> return thermistor 0, 1 -> return thermistor 1, etc.)
            # Encode the current thermistor into binary where each bit corresponds to each pin being high or low
            m1.state = i & 0x1
            m2.state = i & 0x2
            m3.state = i & 0x4
            m4.state = i & 0x8
            time.sleep(0.01)

            to_state = to.state
            if i == thermistor:
                expected_voltage = test_voltage
            else:
                expected_voltage = pullup_voltage
            within = abs(to_state - expected_voltage) < tolerance_v

            print(f"({thermistor=}, {i=}) {to_state=} ?= {expected_voltage=} -> {within=}")
            check.almost_equal(to_state, expected_voltage, abs=tolerance_v, rel=0.0, msg=f"Input on therm {thermistor}, selecting {i}")

            # if i == thermistor:
            #     # hil.check_within(to.state, test_voltage, tolerance_v, f"Input on therm {thermistor}, selecting {i}")
            #     # check.almost_equal(to.state, test_voltage, abs=tolerance_v, rel=0.0, msg=f"Input on therm {thermistor}, selecting {i}")
            # else:
            #     # hil.check_within(to.state, pullup_voltage, tolerance_v, f"Input on therm {thermistor}, selecting {i}")
            #     # check.almost_equal(to.state, pullup_voltage, abs=tolerance_v, rel=0.0, msg=f"Input on therm {thermistor}, selecting {i}")

    # End the test
    # hil.end_test()
# ---------------------------------------------------------------------------- #
