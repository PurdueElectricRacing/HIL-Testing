from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time
import random
from scripts.common.constants.rules_constants import *
from scripts.common.constants.vehicle_constants import *

import pytest_check as check
import pytest


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    hil_instance.load_config("config_system_hil_attached.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
BRK_SWEEP_DELAY = 0.1


def test_bspd(hil):
    # HIL outputs (hil writes)
    brk1 = hil.aout("Dashboard", "BRK1_RAW")
    brk2 = hil.aout("Dashboard", "BRK2_RAW")

    # HIL inputs (hil reads)
    brk_fail_tap = hil.mcu_pin("Dashboard", "BRK_FAIL_TAP")
    brk_stat_tap = hil.mcu_pin("Dashboard", "BRK_STAT_TAP")

    # Brakes 1 and 2 are at rest
    brk1.state = BRK_1_REST_V
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    check.equal(brk_stat_tap.state, 0, f"Brakes 1 ({BRK_1_REST_V}) and 2 ({BRK_2_REST_V}) -> rests")

    # Brake 1 trips
    brk1.state = BRK_1_THRESH_V
    time.sleep(0.1)
    check.equal(brk_stat_tap.state, 1, f"Brake 1 ({BRK_1_THRESH_V}) -> trips")

    # Brake 1 resets -> rest
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    check.equal(brk_stat_tap.state, 0, f"Brake 1 ({BRK_1_REST_V}) -> rests")

    # Brake 2 trips
    brk2.state = BRK_2_THRESH_V
    time.sleep(0.1)
    check.equal(brk_stat_tap.state, 1, f"Brake 2 ({BRK_2_THRESH_V}) -> trips")

    # Brake 1 high -> still tripped
    brk1.state = BRK_1_THRESH_V
    time.sleep(0.1)
    check.equal(brk_stat_tap.state, 1, f"Brakes (1 -> {BRK_1_REST_V}) stay tripped")

    # Reset both brakes
    brk1.state = BRK_MIN_OUT_V
    brk2.state = BRK_MIN_OUT_V
    time.sleep(0.1)
    check.equal(brk_stat_tap.state, 0, f"Brakes 1 ({BRK_MIN_OUT_V}) and 2 ({BRK_MIN_OUT_V}) -> rests")

    # Brake 1 trips at the correct voltage
    start = BRK_MIN_OUT_V
    stop  = BRK_MAX_OUT_V
    step  = 0.1

    thresh = utils.measure_trip_thresh(brk1, start, stop, step,
                                       BRK_SWEEP_DELAY,
                                       brk_stat_tap, is_falling=False)
    print(f"Brake 1 braking threshold: {thresh}")
    check.almost_equal(
        thresh, BRK_1_THRESH_V,
        abs=0.2, rel=0.0,
        msg="Brake 1 trips at correct voltage"
    )
    check.equal(brk_stat_tap.state, 1, "Brake 1 tripped")

    # Reset both brakes
    brk1.state = BRK_MIN_OUT_V
    brk2.state = BRK_MIN_OUT_V
    time.sleep(0.1)
    hil.check(brk_stat_tap.state == 0, f"Brakes 1 ({BRK_MIN_OUT_V}) and 2 ({BRK_MIN_OUT_V}) -> rests")
    
    # Brake 2 trips at the correct voltage
    thresh = utils.measure_trip_thresh(brk2, start, stop, step,
                                       BRK_SWEEP_DELAY,
                                       brk_stat_tap, is_falling=False)
    print(f"Brake 2 braking threshold: {thresh}")
    check.almost_equal(
        thresh, BRK_2_THRESH_V,
        abs=0.2, rel=0.0,
        msg="Brake 2 trips at correct voltage"
    )
    check.equal(brk_stat_tap.state, 1, "Brake 2 tripped")


    # Brakes at rest
    brk1.state = BRK_1_REST_V
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 0, f"Brakes 1 ({BRK_1_REST_V}) and 2 ({BRK_2_REST_V}) -> no fail")

    # Brake 1 forced to 0V (short to GND)
    brk1.state = 0.0
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 1, "Brake 1 short to GND -> fail")

    # Reset brake 1
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 0, "Brake 1 reset -> no fail")

    # Brake 2 forced to 0V (short to GND)
    brk2.state = 0.0
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 1, "Brake 2 short to GND -> fail")

    # Reset brake 2
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 0, "Brake 2 reset -> no fail")

    # Brake 1 forced to 5V (short to VCC)
    brk1.state = 5.0
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 1, "Brake 1 short to VCC -> fail")

    # Reset brake 1
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 0, "Brake 1 reset -> no fail")

    # Brake 2 forced to 5V (short to VCC)
    brk2.state = 5.0
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 1, "Brake 2 short to VCC -> fail")

    # Reset brake 2
    brk2.state = BRK_2_REST_V
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 0, "Brake 2 reset -> no fail")

    # Brake 1 Hi-Z
    brk1.hiZ()
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 1, "Brake 1 Hi-Z -> fail")

    # Reset brake 1
    brk1.state = BRK_1_REST_V
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 0, "Brake 1 reset -> no fail")

    # Brake 2 Hi-Z
    brk2.hiZ()
    time.sleep(0.1)
    check.equal(brk_fail_tap.state, 1, "Brake 2 Hi-Z -> fail")

    # Reset brake 2
    brk2.state = BRK_2_REST_V
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
THROTTLE_VARIANCE = 0.1

# 0-5V throttle sweep with 0.2 step
@pytest.mark.parametrize("voltage", [x / 10.0 for x in range(0, 52, 2)])
def test_throttle(hil, voltage):
    # HIL outputs (hil writes)
    thrtl1 = hil.aout("Dashboard", "THRTL1_RAW")
    thrtl2 = hil.aout("Dashboard", "THRTL2_RAW")

    # HIL inputs (hil reads)
    thrtl1_flt = hil.mcu_pin("Dashboard", "THRTL1_FLT")
    thrtl2_flt = hil.mcu_pin("Dashboard", "THRTL2_FLT")

    throttle_values = [x / 10.0 for x in range(0, 52, 2)]
    random.shuffle(throttle_values)

    thrtl1.state = voltage
    time.sleep(0.1)
    check.almost_equal(
        thrtl1_flt.state, voltage,
        abs=THROTTLE_VARIANCE, rel=0.0,
        msg=f"Throttle 1: {voltage}V"
    )

    thrtl2.state = voltage
    time.sleep(0.1)
    check.almost_equal(
        thrtl2_flt.state, voltage,
        abs=THROTTLE_VARIANCE, rel=0.0,
        msg=f"Throttle 2: {voltage}V"
    )
# ---------------------------------------------------------------------------- #

