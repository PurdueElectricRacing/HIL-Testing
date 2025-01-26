from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import utils
import time
from rules_constants import *
from vehicle_constants import *


BRK_SWEEP_DELAY = 0.1
def test_bspd(hil):
    # Begin the test
    hil.start_test(test_bspd.__name__)

    # Outputs
    brk1    = hil.aout("Dashboard",   "BRK1_RAW")
    brk2    = hil.aout("Dashboard",   "BRK2_RAW")

    # Inputs
    brk_fail_tap = hil.mcu_pin("Dashboard", "BRK_FAIL_TAP")
    brk_stat_tap = hil.mcu_pin("Dashboard", "BRK_STAT_TAP")

    # Brake threshold check
    brk1.state = BRK_1_REST_V
    brk2.state = BRK_2_REST_V
    hil.check(brk_stat_tap.state == 0, "Brake stat starts low")
    brk1.state = BRK_1_THRESH_V
    time.sleep(0.1)
    hil.check(brk_stat_tap.state == 1, "Brake stat goes high at brk 1 thresh")
    brk1.state = BRK_1_REST_V
    hil.check(brk_stat_tap.state == 0, "Brake stat starts low")
    brk2.state = BRK_2_THRESH_V
    time.sleep(0.1)
    hil.check(brk_stat_tap.state == 1, "Brake stat goes high at brk 2 thresh")
    brk1.state = BRK_1_THRESH_V
    hil.check(brk_stat_tap.state == 1, "Brake stat stays high for both brakes")

    # Brake threshold scan
    brk1.state = BRK_MIN_OUT_V
    brk2.state = BRK_MIN_OUT_V
    time.sleep(0.1)
    hil.check(brk_stat_tap.state == 0, "Brake Stat Starts Low Brk 1")

    start = BRK_MIN_OUT_V
    stop  = BRK_MAX_OUT_V
    step  = 0.1

    thresh = utils.measure_trip_thresh(brk1, start, stop, step,
                                       BRK_SWEEP_DELAY,
                                       brk_stat_tap, is_falling=False)
    print(f"Brake 1 braking threshold: {thresh}")
    hil.check_within(thresh, BRK_1_THRESH_V, 0.2, "Brake 1 trip voltage")
    hil.check(brk_stat_tap.state == 1, "Brake Stat Tripped for Brk 1")

    brk1.state = BRK_MIN_OUT_V
    brk2.state = BRK_MIN_OUT_V
    hil.check(brk_stat_tap.state == 0, "Brake Stat Starts Low Brk 2")
    thresh = utils.measure_trip_thresh(brk2, start, stop, step,
                                       BRK_SWEEP_DELAY,
                                       brk_stat_tap, is_falling=False)
    print(f"Brake 2 braking threshold: {thresh}")
    hil.check_within(thresh, BRK_2_THRESH_V, 0.2, "Brake 2 trip voltage")
    hil.check(brk_stat_tap.state == 1, "Brake Stat Tripped for Brk 2")

    # Brake Fail scan
    brk1.state = BRK_1_REST_V
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 0, "Brake Fail Check 1 Starts 0")
    brk1.state = 0.0 # Force 0
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 1, "Brake Fail Brk 1 Short GND")
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 0, "Brake Fail Check 2 Starts 0")
    brk2.state = 0.0 # Force 0
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 1, "Brake Fail Brk 2 Short GND")
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 0, "Brake Fail Check 3 Starts 0")
    brk1.state = 5.0 # Short VCC
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 1, "Brake Fail Brk 1 Short VCC")
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 0, "Brake Fail Check 4 Starts 0")
    brk2.state = 5.0 # Short VCC
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 1, "Brake Fail Brk 2 Short VCC")
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 0, "Brake Fail Check 5 Starts 0")
    brk1.hiZ()
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 1, "Brake Fail Brk 1 Hi-Z")
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 0, "Brake Fail Check 6 Starts 0")
    brk2.hiZ()
    time.sleep(0.1)
    hil.check(brk_fail_tap.state == 1, "Brake Fail Brk 2 Hi-Z")
    brk2.state = BRK_2_REST_V

    # End the test
    hil.end_test()

# TODO: add throttle checks


if __name__ == "__main__":
    hil = HIL()

    hil.load_config("config_system_hil_attached.json")
    hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    hil.init_can()

    # Drive Critical Tests
    test_bspd(hil)

    # Peripheral Sensor Tests

    hil.shutdown()
