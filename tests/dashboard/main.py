from typing import Optional

import hil2.hil2 as hil2
import hil2.component as hil2_comp
import hil2.can_helper as can_helper
import mk_assert.mk_assert as mka

import time
import logging

# Consts ------------------------------------------------------------------------------#
PEDAL_LOW_V = 0.5 # volts read when pedal is not pressed
PEDAL_HIGH_V = 4.5 # volts read when pedal is fully pressed
PEDAL_PERCENT_V = (PEDAL_HIGH_V - PEDAL_LOW_V) / 100.0

SLEEP_TIME = 0.03 # seconds

MSG_NAME = "raw_throttle_brake"

# Helpers -----------------------------------------------------------------------------#
def pedal_percent_to_volts_1(percent: float) -> float:
    """
    Normal linear mapping from 0-100% to volts
    
    :param percent: Percent value from 0 to 100
    :return: Corresponding voltage value
    """
    return PEDAL_LOW_V + percent * PEDAL_PERCENT_V

def pedal_percent_to_volts_2(percent: float) -> float:
    """
    Inverted linear mapping from 0-100% to volts
    
    :param percent: Percent value from 0 to 100
    :return: Corresponding voltage value
    """
    return PEDAL_HIGH_V - percent * PEDAL_PERCENT_V

def power_cycle(pow: hil2_comp.DO, delay_s: float = 0.5):
    pow.set(False)
    time.sleep(delay_s)
    pow.set(True)
    time.sleep(delay_s)


def set_both(pedal1: hil2_comp.AO, pedal2: hil2_comp.AO, percent: float) -> None:
    """
    Set a set of two pedals to the same percent value.

    :param pedal1: First pedal AO component
    :param pedal2: Second pedal AO component
    :param percent: Percent value from 0 to 100
    """
    pedal1.set(pe

def check_msg(msg: Optional[can_helper.CanMessage], test_prefix: str):
    mka.assert_true(msg is not None, f"{test_prefix}: VCAN message received")

def check_brakes(msg: Optional[can_helper.CanMessage], exp_percent: float, tol_v: float, test_prefix: str):
    check_msg(msg, test_prefix)
    mka.assert_eqf(msg is not None and msg.data["brake"],          pedal_percent_to_volts(exp_percent), tol_v, f"{test_prefix}: brake left {exp_percent}%")
    mka.assert_eqf(msg is not None and msg.data["brake_right"],    pedal_percent_to_volts(exp_percent), tol_v, f"{test_prefix}: brake right {exp_percent}%")

def check_throttle_left(msg: Optional[can_helper.CanMessage], exp_percent: float, tol_v: float, test_prefix: str):
    mka.assert_eqf(msg is not None and msg.data["throttle"],       pedal_percent_to_volts(exp_percent), tol_v, f"{test_prefix}: throttle left {exp_percent}%")

def check_throttle_right(msg: Optional[can_helper.CanMessage], exp_percent: float, tol_v: float, test_prefix: str):
    mka.assert_eqf(msg is not None and msg.data["throttle_right"], pedal_percent_to_volts(exp_percent), tol_v, f"{test_prefix}: throttle right {exp_percent}%")

def check_throttles(msg: Optional[can_helper.CanMessage], exp_percent: float, tol_v: float, test_prefix: str):
    check_msg(msg, test_prefix)
    check_throttle_left(msg, exp_percent, tol_v, test_prefix)
    check_throttle_right(msg, exp_percent, tol_v, test_prefix)

# EV.4.7.2 ----------------------------------------------------------------------------#
def ev_4_7_2_test(h: hil2.Hil2):
    """
    If brake is activated (5% pressed) and throttle is activated more than 25%, motor
    must shutdown and stay shutdown until throttle is under 5%
    
    - brake low, throttle low, check motor on
    - brake high, throttle low, check motor on
    - brake high, throttle high, check motor off
    - brake low, throttle mid, check motor off (sweep down to 5% on throttle)
    - brake low, throttle low, check motor back on
    Note: Check for motor off: throttle can message is 0
    """

    brk1 = h.ao("Dashboard", "BRK1_RAW")
    brk2 = h.ao("Dashboard", "BRK2_RAW")
    thrtl1 = h.ao("Dashboard", "THRTL1_RAW")
    thrtl2 = h.ao("Dashboard", "THRTL2_RAW")
    mcan = h.can("HIL2", "VCAN")

    # Setup: set brake and throttle to 0%
    set_both(brk1, brk2, pedal_percent_to_volts(0))
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(0))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_brakes(msg, 0, 0.1, "Setup")
    check_throttles(msg, 0, 0.1, "Setup")
    
    # Test 1: brake low, throttle low, check motor on
    set_both(brk1, brk2, pedal_percent_to_volts(5))
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(5))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_brakes(msg, 5, 0.1, "Brakes low, throttle low")
    check_throttles(msg, 5, 0.1, "Brakes low, throttle low")

    # Test 2: brake high, throttle low, check motor on
    set_both(brk1, brk2, pedal_percent_to_volts(50))
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(5))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_brakes(msg, 50, 0.1, "Brakes high, throttle low")
    check_throttles(msg, 5, 0.1, "Brakes high, throttle low")

    # Test 3: brake high, throttle high, check motor off
    set_both(brk1, brk2, pedal_percent_to_volts(50))
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(50))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_brakes(msg, 50, 0.1, "Brakes high, throttle high")
    check_throttles(msg, 0, 0.1, "Brakes high, throttle high")

    # Test 4: brake low, throttle mid, check motor off (sweep down to 5% on throttle)
    set_both(brk1, brk2, pedal_percent_to_volts(5))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_brakes(msg, 5, 0.1, "Brakes low, throttle mid")

    for p in range(50, 4, -1):
        set_both(thrtl1, thrtl2, pedal_percent_to_volts(p))
        time.sleep(SLEEP_TIME)
        msg = mcan.get_last(MSG_NAME)
        expected_throttle = 0 if p > 5 else pedal_percent_to_volts(p)
        check_throttles(msg, expected_throttle, 0.1, f"Brakes low, throttle {p} (expected {expected_throttle}%)")
    
    # Test 5: brake low, throttle mid, check motor back on
    set_both(brk1, brk2, pedal_percent_to_volts(5))
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(25))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_brakes(msg, 5, 0.1, "Brakes low, throttle mid")
    check_throttles(msg, 25, 0.1, "Brakes low, throttle mid")


# T.4.2.5 -----------------------------------------------------------------------------#
def t_4_2_5_impl(left_is_1: bool, sens1: hil2_comp.AO, sens2: hil2_comp.AO, sdc: hil2_comp.DI, mcan: hil2_comp.CAN):
    """
    - sens1 and sens2 similar, check motor on, sdc not triggered
    - sens1 and sens2 slightly different, check motor on, sdc not triggered
    - sens1 and sens2 10% different, check motor on, sdc not triggered
    - sens1 and sens2 slightly different, check motor on, sdc not triggered
    - sens1 and sens2 10% different, check motor on, sdc not triggered
    - sens1 and sens2 still 10% different (~100 msec later), check motor off, sdc not triggered
    - sens1 and sens2 similar, check motor on, sdc not triggered
    Note: Check for motor off: throttle can message is 0
    """

    # Sensors similar, check motor on, sdc not triggered
    set_both(sens1, sens2, pedal_percent_to_volts(20))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_throttles(msg, 20, 0.1, "Sensors similar")
    mka.assert_false(sdc.get(), "SDC not triggered")
    
    # Sensors slightly different, check motor on, sdc not triggered
    sens1.set(pedal_percent_to_volts(20))
    sens2.set(pedal_percent_to_volts(25))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_msg(msg, "Sensors slightly different")
    if left_is_1:
        check_throttle_left(msg, 20, 0.1, "Sensors slightly different")
        check_throttle_right(msg, 25, 0.1, "Sensors slightly different")
    else:
        check_throttle_left(msg, 25, 0.1, "Sensors slightly different")
        check_throttle_right(msg, 20, 0.1, "Sensors slightly different")
    mka.assert_false(sdc.get(), "SDC not triggered")

    # Sensors 10% different, check motor on, sdc not triggered
    sens1.set(pedal_percent_to_volts(20))
    sens2.set(pedal_percent_to_volts(30))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_msg(msg, "Sensors 10% different")
    if left_is_1:
        check_throttle_left(msg, 20, 0.1, "Sensors 10% different")
        check_throttle_right(msg, 30, 0.1, "Sensors 10% different")
    else:
        check_throttle_left(msg, 30, 0.1, "Sensors 10% different")
        check_throttle_right(msg, 20, 0.1, "Sensors 10% different")
    mka.assert_false(sdc.get(), "SDC not triggered")

    # Sensors slightly different, check motor on, sdc not triggered
    sens1.set(pedal_percent_to_volts(25))
    sens2.set(pedal_percent_to_volts(30))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_msg(msg, "Sensors slightly different")
    if left_is_1:
        check_throttle_left(msg, 25, 0.1, "Sensors slightly different")
        check_throttle_right(msg, 30, 0.1, "Sensors slightly different")
    else:
        check_throttle_left(msg, 30, 0.1, "Sensors slightly different")
        check_throttle_right(msg, 25, 0.1, "Sensors slightly different")
    mka.assert_false(sdc.get(), "SDC not triggered")

    # Sensors 10% different, check motor on, sdc not triggered
    sens1.set(pedal_percent_to_volts(20))
    sens2.set(pedal_percent_to_volts(30))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_msg(msg, "Sensors 10% different")
    if left_is_1:
        check_throttle_left(msg, 20, 0.1, "Sensors 10% different")
        check_throttle_right(msg, 30, 0.1, "Sensors 10% different")
    else:
        check_throttle_left(msg, 30, 0.1, "Sensors 10% different")
        check_throttle_right(msg, 20, 0.1, "Sensors 10% different")
    mka.assert_false(sdc.get(), "SDC not triggered")

    # Sensors still 10% different (~100 msec later), check motor off, sdc not triggered
    time.sleep(0.1)
    msg = mcan.get_last(MSG_NAME)
    check_msg(msg, "Sensors still 10% different (~100 msec later)")
    check_throttles(msg, 0, 0.1, "Sensors still 10% different (~100 msec later)")
    mka.assert_false(sdc.get(), "SDC not triggered")

    # Sensors similar, check motor on, sdc not triggered
    set_both(sens1, sens2, pedal_percent_to_volts(20))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_throttles(msg, 20, 0.1, "Sensors similar")
    mka.assert_false(sdc.get(), "SDC not triggered")


def t_4_2_5_test(h: hil2.Hil2):
    """
    If the throttle sensors differ by more than 10% of the pedal travel or disconnects
    and this exists for more than 100 msec, motors must be stopped, sdc isn't tripped
    """
    thrtl1 = h.ao("Dashboard", "THRTL1_RAW")
    thrtl2 = h.ao("Dashboard", "THRTL2_RAW")
    sdc = h.di("Dashboard", "SDC")
    mcan = h.can("HIL2", "VCAN")

    # Setup: set brake and throttle to 0%
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(0))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_throttles(msg, 0, 0.1, "Setup")

    # Test with left as sens1
    t_4_2_5_impl(True, thrtl1, thrtl2, sdc, mcan)

    # Setup: set brake and throttle to 0%
    set_both(thrtl1, thrtl2, pedal_percent_to_volts(0))
    time.sleep(SLEEP_TIME)
    msg = mcan.get_last(MSG_NAME)
    check_throttles(msg, 0, 0.1, "Setup")

    # Test with right as sens1
    t_4_2_5_impl(False, thrtl2, thrtl1, sdc, mcan)

# T.4.2.10 ----------------------------------------------------------------------------#
def t_4_2_10_test_out_of_range(left_is_1: bool, sens1: hil2_comp.AO, sens2: hil2_comp.AO, sdc: hil2_comp.DI, mcan: hil2_comp.CAN):
    """
    - sens1 and sens2 ok, check motor on, sdc not triggered
    - both are out of range high, check motor off, sdc triggered
    """


# Main --------------------------------------------------------------------------------#
def main():
    logging.basicConfig(level=logging.DEBUG)

    with hil2.Hil2(
        "./tests/dash/config.json",
        "device_configs",
        "TODO",
        "TODO"
    ) as h:
        
        pow = h.do("HIL2", "RLY1")
        
        mka.set_setup_fn(lambda: power_cycle(pow, 0.5))
        mka.add_test(ev_4_7_2_test, h)
        mka.add_test(t_4_2_5_test, h)
        mka.run_tests()


if __name__ == "__main__":
    main()