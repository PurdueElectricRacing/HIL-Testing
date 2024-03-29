from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import utils
import time

def test_collector(hil):
    # Begin the test
    hil.start_test(test_collector.__name__)

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
            m1.state = i & 0x1
            m2.state = i & 0x2
            m3.state = i & 0x4
            m4.state = i & 0x8
            time.sleep(0.01)

            if (i == thermistor):
                hil.check_within(to.state, test_voltage, tolerance_v, f"Input on therm {thermistor}, selecting {i}")
            else:
                hil.check_within(to.state, pullup_voltage, tolerance_v, f"Input on therm {thermistor}, selecting {i}")
            print(to.state)

    # End the test
    hil.end_test()

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_collector_bench.json")
    hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    test_collector(hil)

    hil.shutdown()
