from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import utils
import time
from rules_constants import *
from vehicle_constants import *

import pytest_check as check
import pytest


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    hil_instance.load_config("config_main_sdc_bench.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")
    
    # hil_instance.init_can()
    
    yield hil_instance
    
    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
# SETUP for CSENSE
# Current Sensor (DHAB) -> ABOX V Divider -> MAIN_SDC

DAC_GAIN = 1 + 4.7 / 4.7 - 0.05

def cycle_power(pow):
    pow.state = 0
    time.sleep(0.75)
    pow.state = 1

def set_bspd_current(ch1, current):
    v = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(current))
    ch1.state = v / DAC_GAIN

def reset_bspd(fail, stat, ch1):
    fail.state = 0
    stat.state = 0
    set_bspd_current(ch1, 0.0)


# ---------------------------------------------------------------------------- #
def test_bspd(hil):
    # Begin the test
    # hil.start_test(test_bspd.__name__)

    # Outputs
    brk_fail  = hil.dout("MainSDC", "Brake Fail")
    brk_stat  = hil.dout("MainSDC", "Brake Status")
    c_sense   = hil.aout("MainSDC", "Current Sense C1")
    pow       = hil.dout("MainSDC", "5V_Crit")

    # Inputs
    bspd_ctrl = hil.din("MainSDC", "BSPD_Control")

    # Brake Fail
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    brk_fail.state = 1
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Brake Fail")
    check.below(t, R_BSPD_MAX_TRIP_TIME_S, "Brake Fail")
    brk_fail.state = 0
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Brake Fail Stays Latched")
    check.equal(bspd_ctrl.state, 0, "Brake Fail Stays Latched")

    # Brake Fail on Power On
    reset_bspd(brk_fail, brk_stat, c_sense)
    brk_fail.state = 1
    cycle_power(pow)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Power On Brake Fail")
    check.equal(bspd_ctrl.state, 0, "Power On Brake Fail")

    # Current no brake
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    time.sleep(2) # TODO: I am not sure why this fails, but oh well
    set_bspd_current(c_sense, 75)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # time.sleep(100)

    # hil.check(bspd_ctrl.state == 1, "Current no brake")
    check.equal(bspd_ctrl.state, 1, "Current no brake")

    # Current Sense Short to Ground
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    c_sense.state = 0.0
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Current short to ground")
    check.below(t, R_BSPD_MAX_TRIP_TIME_S, "Current short to ground")
    set_bspd_current(c_sense, 0.0)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Current short to ground stays latched")
    check.equal(bspd_ctrl.state, 0, "Current short to ground stays latched")

    # Current Sense Short to 5V
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    c_sense.state = ABOX_DHAB_CH1_DIV.div(5.0) / DAC_GAIN
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Current short to 5V")
    check.below(t, R_BSPD_MAX_TRIP_TIME_S, "Current short to 5V")
    set_bspd_current(c_sense, 0.0)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Current short to 5V stays latched")
    check.equal(bspd_ctrl.state, 0, "Current short to 5V stays latched")

    # Braking
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    brk_stat.state = 1
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 1, "Brake no current")
    check.equal(bspd_ctrl.state, 1, "Brake no current")

    # Lowest current required to trip at
    min_trip_current = R_BSPD_POWER_THRESH_W / ACCUM_MAX_V
    set_bspd_current(c_sense, min_trip_current)
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Braking with current")
    check.below(t, R_BSPD_MAX_TRIP_TIME_S, "Braking with current")

    # Measure braking with current threshold
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    brk_stat.state = 1

    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    start = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(0.0)) / DAC_GAIN
    stop  = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(DHAB_S124_CH1_MAX_A)) / DAC_GAIN
    step  = 0.1 / DAC_GAIN
    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    thresh *= DAC_GAIN
    thresh_amps = dhab_ch1_v_to_a(ABOX_DHAB_CH1_DIV.reverse(thresh))
    print(f"Current while braking threshold: {thresh}V = {thresh_amps}A")
    # hil.check_within(thresh, ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(min_trip_current)), 0.1, "Current while braking threshold")
    check.within(thresh, ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(min_trip_current)), 0.1, "Current while braking threshold")

    # Determine the current sense short to gnd threshold
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    set_bspd_current(c_sense, DHAB_S124_CH1_MIN_A)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 1, "Min output current okay")
    check.equal(bspd_ctrl.state, 1, "Min output current okay")
    start = ABOX_DHAB_CH1_DIV.div(DHAB_S124_MIN_OUT_V) / DAC_GAIN
    stop = 0.0
    step = -0.1 / DAC_GAIN
    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    thresh *= DAC_GAIN
    print(f"Short to ground threshold: {thresh}V")
    # hil.check(stop < (thresh / DAC_GAIN) < start, "Current short to ground threshold")
    check.between(thresh / DAC_GAIN, stop, start, "Current short to ground threshold")

    # Determine the current sense short to 5V threshold
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    time.sleep(2)

    set_bspd_current(c_sense, DHAB_S124_CH1_MAX_A)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 1, "Max output current okay")
    check.equal(bspd_ctrl.state, 1, "Max output current okay")
    start = ABOX_DHAB_CH1_DIV.div(DHAB_S124_MAX_OUT_V) / DAC_GAIN
    stop = ABOX_DHAB_CH1_DIV.div(5.0) / DAC_GAIN
    step = 0.01 / DAC_GAIN

    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    thresh *= DAC_GAIN
    print(f"Short to 5V threshold: {thresh}V")
    # hil.check(bspd_ctrl.state == 0, "Short to 5V trips")
    check.equal(bspd_ctrl.state, 0, "Short to 5V trips")
    print(stop * DAC_GAIN)
    print(start * DAC_GAIN)
    # hil.check(start < (thresh / DAC_GAIN) <= stop, "Current short to 5V threshold")
    check.between(thresh / DAC_GAIN, stop, start, "Current short to 5V threshold")

    # Floating current
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    c_sense.hiZ()
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Floating current")
    check.equal(bspd_ctrl.state, 0, "Floating current")

    # Floating brake_fail
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    brk_fail.hiZ()
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Floating brake fail")
    check.equal(bspd_ctrl.state, 0, "Floating brake fail")

    # Floating brake_stat
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power(pow)
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    brk_stat.hiZ()
    set_bspd_current(c_sense, min_trip_current)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Floating brake status")
    check.equal(bspd_ctrl.state, 0, "Floating brake status")

    # End the test
    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
IMD_RC_MIN_TRIP_TIME_S = IMD_STARTUP_TIME_S 
IMD_RC_MAX_TRIP_TIME_S = R_IMD_MAX_TRIP_TIME_S - IMD_MEASURE_TIME_S
IMD_STAT_OKAY = 1
IMD_STAT_TRIP = 0
IMD_CTRL_OKAY = 1
IMD_CTRL_TRIP = 0

def reset_imd(imd_stat):
    imd_stat.state = IMD_STAT_OKAY


def test_imd(hil):
    # Begin the test
    # hil.start_test(test_imd.__name__)

    # Outputs
    imd_stat  = hil.dout("MainSDC", "IMD_Status")
    pow       = hil.dout("MainSDC", "5V_Crit")

    # Inputs
    imd_ctrl  = hil.din("MainSDC", "IMD_Control")

    # IMD Fault
    reset_imd(imd_stat)
    cycle_power(pow)
    # hil.check(imd_ctrl.state == IMD_CTRL_OKAY, "Power On")
    check.equal(imd_ctrl.state, IMD_CTRL_OKAY, "Power On")
    time.sleep(1)
    imd_stat.state = IMD_STAT_TRIP
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    # hil.check(IMD_RC_MIN_TRIP_TIME_S < t < IMD_RC_MAX_TRIP_TIME_S, "IMD Trip Time")
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Trip")
    check.between(t, IMD_RC_MIN_TRIP_TIME_S, IMD_RC_MAX_TRIP_TIME_S, "IMD Trip Time")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Trip")
    imd_stat.state = IMD_STAT_OKAY
    time.sleep(IMD_RC_MAX_TRIP_TIME_S * 1.1)
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Fault Stays Latched")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Fault Stays Latched")

    # IMD Fault on Power On
    reset_imd(imd_stat)
    imd_stat.state = IMD_STAT_TRIP
    cycle_power(pow)
    time.sleep(IMD_RC_MAX_TRIP_TIME_S)
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Fault Power On")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Fault Power On")

    # IMD Floating
    reset_imd(imd_stat)
    imd_stat.hiZ()
    cycle_power(pow)
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    # hil.check(t < R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Floating Trip")
    check.below(t, R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Floating Trip")
    
    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
AMS_STAT_OKAY = 1
AMS_STAT_TRIP = 0
AMS_CTRL_OKAY = 1
AMS_CTRL_TRIP = 0

def reset_ams(ams_stat):
    ams_stat.state = AMS_STAT_OKAY


def test_ams(hil):
    # Begin the test
    # hil.start_test(test_ams.__name__)

    # Outputs
    ams_stat  = hil.dout("MainSDC", "BMS-Status-Main")
    pow       = hil.dout("MainSDC", "5V_Crit")

    # Inputs
    ams_ctrl  = hil.din("MainSDC", "BMS_Control")

    # AMS Fault
    reset_ams(ams_stat)
    cycle_power(pow)
    # hil.check(ams_ctrl.state == AMS_CTRL_OKAY, "Power On")
    check.equal(ams_ctrl.state, AMS_CTRL_OKAY, "Power On")
    time.sleep(1)
    ams_stat.state = AMS_STAT_TRIP
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    # hil.check(0 < t < AMS_MAX_TRIP_DELAY_S, "AMS Trip Time")
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Trip")
    check.between(t, 0, AMS_MAX_TRIP_DELAY_S, "AMS Trip Time")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Trip")
    ams_stat.state = AMS_STAT_OKAY
    time.sleep(AMS_MAX_TRIP_DELAY_S * 1.1)
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Fault Stays Latched")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Fault Stays Latched")

    # AMS Fault on Power On
    reset_ams(ams_stat)
    ams_stat.state = AMS_STAT_TRIP
    cycle_power(pow)
    time.sleep(AMS_MAX_TRIP_DELAY_S)
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Fault Power On")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Fault Power On")

    # AMS Floating
    reset_ams(ams_stat)
    ams_stat.hiZ()
    cycle_power(pow)
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    # hil.check(0 < t < AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time")
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Floating Trip")
    check.between(t, 0, AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time", ge=True)
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Floating Trip")
    
    # hil.end_test()
# ---------------------------------------------------------------------------- #