from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hil.hil import HIL
import hil.utils as utils
import time
from scripts.common.constants.rules_constants import *
from scripts.common.constants.vehicle_constants import *

import pytest_check as check
import pytest


# ---------------------------------------------------------------------------- #
AMS_STAT_OKAY = 1
AMS_STAT_TRIP = 0
AMS_CTRL_OKAY = 1
AMS_CTRL_TRIP = 0

def reset_ams(ams_stat):
    ams_stat.state = AMS_STAT_OKAY

def set_bspd_current(ch1, current):
    ch1.state = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(current))

def reset_bspd(fail, stat, ch1):
    fail.state = 0
    stat.state = 0
    set_bspd_current(ch1, 0.0)

IMD_STAT_OKAY = 1
IMD_STAT_TRIP = 0
def reset_imd(imd_stat):
    imd_stat.state = IMD_STAT_OKAY

def reset_pchg(v_bat, v_mc):
    print(f"Setting v_bat to {tiff_hv_to_lv(ACCUM_NOM_V)}")
    v_bat.state = tiff_hv_to_lv(ACCUM_NOM_V)
    print(f"Setting v_mc to {tiff_hv_to_lv(0.0)}")
    v_mc.state  = tiff_hv_to_lv(0.0)

def reset_tsal(v_mc):
    v_mc.state  = tiff_hv_to_lv(0.0)

power = None

CYCLE_POWER_ON_DELAY = 0.1

def cycle_power():
    power.state = 1
    time.sleep(0.75)
    power.state = 0
    time.sleep(CYCLE_POWER_ON_DELAY)
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    global power

    hil_instance = HIL()

    hil_instance.load_config("config_main_base_bench.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    hil_instance.init_can()

    power = hil_instance.dout("Arduino2", "RLY1")

    yield hil_instance

    hil_instance.shutdown()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_precharge(hil):
    # Begin the test
    # hil.start_test(test_precharge.__name__)

    # Outputs
    v_bat = hil.aout("Main_Module", "VBatt")
    v_mc  = hil.aout("Main_Module", "Voltage MC Transducer")

    # Inputs
    pchg_cmplt = hil.mcu_pin("Main_Module", "PrechargeComplete_Prot")
    not_pchg_cmplt_delayed = hil.din("Main_Module", "NotPrechargeCompleteSchmitt")
    # v_bat_mcu = hil.daq_var("Main_Module", "Varname") # TODO
    # v_mc_mcu  = hil.daq_var("Main_Module", "Varname") # TODO
    # pchg_mux  = hil.daq_var("Main_Module", "Varname") # TODO

    # Initial State
    reset_pchg(v_bat, v_mc)
    time.sleep(2.5)
    # hil.check(pchg_cmplt.state == 0, "Precharge not complete on startup")
    # hil.check(not_pchg_cmplt_delayed.state == 1, "Not precharge complete delayed high on startup")
    check.equal(pchg_cmplt.state, 0, "Precharge not complete on startup")
    check.equal(not_pchg_cmplt_delayed.state, 1, "Not precharge complete delayed high on startup")

    # Check delay
    v_mc.state = tiff_hv_to_lv(ACCUM_NOM_V)
    t = utils.measure_trip_time(not_pchg_cmplt_delayed, PCHG_COMPLETE_DELAY_S*3, is_falling=True)
    # hil.check(not_pchg_cmplt_delayed.state == 0, "Precharge complete delayed")
    # hil.check_within(t, PCHG_COMPLETE_DELAY_S, 0.25, f"Precharge complete delay of {t:.3}s close to expected {PCHG_COMPLETE_DELAY_S}s")
    check.equal(not_pchg_cmplt_delayed.state, 0, "Precharge complete delayed")
    check.almost_equal(t, PCHG_COMPLETE_DELAY_S, abs=0.25, rel=0.0, msg=f"Precharge complete delay of {t:.3}s close to expected {PCHG_COMPLETE_DELAY_S}s")


    # Find threshold at nominal pack voltage
    for v in [ACCUM_MIN_V, ACCUM_NOM_V, ACCUM_MAX_V]:
        reset_pchg(v_bat, v_mc)
        print(f"Testing precharge threshold at V_bat = {v}")
        v_bat.state = tiff_hv_to_lv(v)
        v_mc.state = tiff_hv_to_lv(v*0.8)
        time.sleep(0.01)
        # hil.check(pchg_cmplt.state == 0, "Precharge Complete Low at Initial State")
        check.equal(pchg_cmplt.state, 0, "Precharge Complete Low at Initial State")

        start = tiff_hv_to_lv(v*0.8)
        stop  = tiff_hv_to_lv(v)
        step  = tiff_hv_to_lv(1)
        thresh = utils.measure_trip_thresh(v_mc, start, stop, step, 0.01,
                                           pchg_cmplt, is_falling=0)
        thresh_hv = tiff_lv_to_hv(thresh)
        print(f"Precharge triggered at {thresh_hv / v * 100:.4}% ({thresh_hv:.5}V) of vbat={v}.")
        # hil.check_within(thresh_hv / v, R_PCHG_V_BAT_THRESH, 0.03, f"Precharge threshold of {R_PCHG_V_BAT_THRESH*100}% at vbat = {v}V")
        check.almost_equal(thresh_hv / v, R_PCHG_V_BAT_THRESH, abs=0.03, rel=0.0, msg=f"Precharge threshold of {R_PCHG_V_BAT_THRESH*100}% at vbat = {v}V")

        v_mc.state = tiff_hv_to_lv(v)
        time.sleep(0.25)
        # hil.check(pchg_cmplt.state == 1, f"Precharge completed at vbat = {v}V")
        check.equal(pchg_cmplt.state, 1, f"Precharge completed at vbat = {v}V")


    # Floating conditions (check never precharge complete)
    reset_pchg(v_bat, v_mc)
    v_bat.hiZ()
    v_mc.state = tiff_hv_to_lv(0)
    # hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat float, v_mc 0V")
    check.equal(pchg_cmplt.state, 0, "Precharge not complete on v_bat float, v_mc 0V")

    v_mc.state = tiff_hv_to_lv(ACCUM_MAX_V)
    # hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat float, v_mc max V")
    check.equal(pchg_cmplt.state, 0, "Precharge not complete on v_bat float, v_mc max V")

    reset_pchg(v_bat, v_mc)
    v_mc.hiZ()
    v_bat.state = tiff_hv_to_lv(ACCUM_MIN_V)
    # hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat min, v_mc float")
    check.equal(pchg_cmplt.state, 0, "Precharge not complete on v_bat min, v_mc float")
    v_bat.state = tiff_hv_to_lv(ACCUM_MAX_V)
    # hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat max, v_mc float")
    check.equal(pchg_cmplt.state, 0, "Precharge not complete on v_bat max, v_mc float")

    reset_pchg(v_bat, v_mc)
    v_bat.hiZ()
    v_mc.hiZ()
    # hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat float, v_mc float")
    check.equal(pchg_cmplt.state, 0, "Precharge not complete on v_bat float, v_mc float")

    # TODO: software precharge validity checks (make precharge take forever)
    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_bspd(hil):
    # Begin the test
    # hil.start_test(test_bspd.__name__)

    # Outputs
    brk_fail = hil.dout("Main_Module", "Brake Fail")
    brk_stat = hil.dout("Main_Module", "Brake Status")
    c_sense  = hil.aout("Main_Module", "Current Sense C1")

    # Outputs to set SDC status to okay
    ams_stat  = hil.dout("Main_Module", "BMS-Status-Main")
    imd_stat  = hil.dout("Main_Module", "IMD_Status")

    # Inputs
    bspd_ctrl = hil.din("Main_Module", "SDC3") # Assuming IMD and AMS closed

    # Set other SDC nodes to okay
    reset_ams(ams_stat)
    reset_imd(imd_stat)

    # Brake Fail
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    brk_fail.state = 1
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Brake Fail")
    check.less(t, R_BSPD_MAX_TRIP_TIME_S, "Brake Fail")
    brk_fail.state = 0
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Brake Fail Stays Latched")
    check.equal(bspd_ctrl.state, 0, "Brake Fail Stays Latched")

    # Brake Fail on Power On
    reset_bspd(brk_fail, brk_stat, c_sense)
    # Manual power cycle, setting brk_fail on before
    # Will cause power to feed back into system
    power.state = 1
    time.sleep(2)
    brk_fail.state = 1
    power.state = 0
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Power On Brake Fail")
    check.equal(bspd_ctrl.state, 0, "Power On Brake Fail")

    # Current no brake
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
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
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    c_sense.state = 0.0
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Current short to ground")
    check.less(t, R_BSPD_MAX_TRIP_TIME_S, "Current short to ground")
    set_bspd_current(c_sense, 0.0)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Current short to ground stays latched")
    check.equal(bspd_ctrl.state, 0, "Current short to ground stays latched")

    # Current Sense Short to 5V
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    c_sense.state = ABOX_DHAB_CH1_DIV.div(5.0)
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    # hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Current short to 5V")
    check.less(t, R_BSPD_MAX_TRIP_TIME_S, "Current short to 5V")
    set_bspd_current(c_sense, 0.0)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Current short to 5V stays latched")
    check.equal(bspd_ctrl.state, 0, "Current short to 5V stays latched")

    # Braking
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
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
    check.less(t, R_BSPD_MAX_TRIP_TIME_S, "Braking with current")

    # Measure braking with current threshold
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    brk_stat.state = 1

    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    start = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(0.0))
    stop  = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(DHAB_S124_CH1_MAX_A))
    step  = 0.1
    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    thresh_amps = dhab_ch1_v_to_a(ABOX_DHAB_CH1_DIV.reverse(thresh))
    print(f"Current while braking threshold: {thresh}V = {thresh_amps}A")
    # hil.check_within(thresh, ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(min_trip_current)), 0.1, "Current while braking threshold")
    check.almost_equal(
        thresh, ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(min_trip_current)),
        abs=0.1, rel=0.0,
        msg="Current while braking threshold"
    )

    # Determine the current sense short to gnd threshold
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    set_bspd_current(c_sense, DHAB_S124_CH1_MIN_A)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 1, "Min output current okay")
    check.equal(bspd_ctrl.state, 1, "Min output current okay")
    start = ABOX_DHAB_CH1_DIV.div(DHAB_S124_MIN_OUT_V)
    stop = 0.0
    step = -0.1
    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    print(f"Short to ground threshold: {thresh}V")
    # hil.check(stop < (thresh) < start, "Current short to ground threshold")
    check.between(thresh, stop, start, "Current short to ground threshold")

    # Determine the current sense short to 5V threshold
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    time.sleep(2)

    set_bspd_current(c_sense, DHAB_S124_CH1_MAX_A)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 1, "Max output current okay")
    check.equal(bspd_ctrl.state, 1, "Max output current okay")
    start = ABOX_DHAB_CH1_DIV.div(DHAB_S124_MAX_OUT_V)
    stop = ABOX_DHAB_CH1_DIV.div(5.0)
    step = 0.01

    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    print(f"Short to 5V threshold: {thresh}V")
    # hil.check(bspd_ctrl.state == 0, "Short to 5V trips")
    check.equal(bspd_ctrl.state, 0, "Short to 5V trips")
    print(stop)
    print(start)
    # hil.check(start < (thresh) <= stop, "Current short to 5V threshold")
    check.between(thresh, stop, start, "Current short to 5V threshold", le=True)

    # Floating current
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    c_sense.hiZ()
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Floating current")
    check.equal(bspd_ctrl.state, 0, "Floating current")

    # Floating brake_fail
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
    # hil.check(bspd_ctrl.state == 1, "Power On")
    check.equal(bspd_ctrl.state, 1, "Power On")
    brk_fail.hiZ()
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # hil.check(bspd_ctrl.state == 0, "Floating brake fail")
    check.equal(bspd_ctrl.state, 0, "Floating brake fail")

    # Floating brake_stat
    reset_bspd(brk_fail, brk_stat, c_sense)
    cycle_power()
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
IMD_CTRL_OKAY = 1
IMD_CTRL_TRIP = 0

def test_imd(hil):
    # Begin the test
    # hil.start_test(test_imd.__name__)

    # Outputs
    imd_stat  = hil.dout("Main_Module", "IMD_Status")

    # Outputs to set SDC status to okay
    ams_stat = hil.dout("Main_Module", "BMS-Status-Main")
    brk_fail = hil.dout("Main_Module", "Brake Fail")
    brk_stat = hil.dout("Main_Module", "Brake Status")
    c_sense  = hil.aout("Main_Module", "Current Sense C1")

    # Inputs
    imd_ctrl  = hil.din("Main_Module", "SDC3") # assuming AMS and BSPD closed

    # Set other SDC nodes to okay
    reset_ams(ams_stat)
    reset_bspd(brk_fail, brk_stat, c_sense)

    # IMD Fault
    reset_imd(imd_stat)
    cycle_power()
    # hil.check(imd_ctrl.state == IMD_CTRL_OKAY, "Power On")
    check.equal(imd_ctrl.state, IMD_CTRL_OKAY, "Power On")
    time.sleep(1)
    imd_stat.state = IMD_STAT_TRIP
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    print(f"Target trip time: [{IMD_RC_MIN_TRIP_TIME_S}, {IMD_RC_MAX_TRIP_TIME_S}]")
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
    cycle_power()
    time.sleep(IMD_RC_MAX_TRIP_TIME_S)
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Fault Power On")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Fault Power On")

    # IMD Floating
    reset_imd(imd_stat)
    imd_stat.hiZ()
    cycle_power()
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    # hil.check(t < R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Floating Trip")
    check.between(t, 0, R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Floating Trip")

    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_ams(hil):
    # Begin the test
    # hil.start_test(test_ams.__name__)

    # Outputs
    ams_stat  = hil.dout("Main_Module", "BMS-Status-Main")

    # Outputs to set SDC status to okay
    imd_stat  = hil.dout("Main_Module", "IMD_Status")
    brk_fail = hil.dout("Main_Module", "Brake Fail")
    brk_stat = hil.dout("Main_Module", "Brake Status")
    c_sense  = hil.aout("Main_Module", "Current Sense C1")

    # Inputs
    ams_ctrl  = hil.din("Main_Module", "SDC3") # assumes IMD and BSPD closed

    # Set other SDC nodes to okay
    reset_imd(imd_stat)
    reset_bspd(brk_fail, brk_stat, c_sense)

    # AMS Fault
    reset_ams(ams_stat)
    cycle_power()
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
    cycle_power()
    time.sleep(AMS_MAX_TRIP_DELAY_S)
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Fault Power On")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Fault Power On")

    # AMS Floating
    reset_ams(ams_stat)
    ams_stat.hiZ()
    cycle_power()
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    # hil.check(0 < t < AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time")
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Floating Trip")
    check.between(t, 0, AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Floating Trip")

    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_tsal(hil):

    # Begin the test
    # hil.start_test(test_tsal.__name__)

    # Outputs
    v_mc  = hil.aout("Main_Module", "Voltage MC Transducer")

    # Inputs
    tsal = hil.din("Main_Module", "TSAL+")
    lval = hil.din("Main_Module", "LVAL+")

    # Initial State
    reset_tsal(v_mc)
    time.sleep(0.2)
    # No need to power cycle

    # hil.check(lval.state == 1, "LVAL on at v_mc = 0")
    # hil.check(tsal.state == 0, "TSAL off at v_mc = 0")
    check.equal(lval.state, 1, "LVAL on at v_mc = 0")
    check.equal(tsal.state, 0, "TSAL off at v_mc = 0")

    time.sleep(5)
    # hil.check(lval.state == 1, "LVAL stays on")
    check.equal(lval.state, 1, "LVAL stays on")

    v_mc.state = tiff_hv_to_lv(ACCUM_MIN_V)
    time.sleep(0.1)

    # hil.check(lval.state == 0, f"LVAL off at {ACCUM_MIN_V:.4} V")
    # hil.check(tsal.state == 1, f"TSAL on at {ACCUM_MIN_V:.4} V")
    check.equal(lval.state, 0, f"LVAL off at {ACCUM_MIN_V:.4} V")
    check.equal(tsal.state, 1, f"TSAL on at {ACCUM_MIN_V:.4} V")

    reset_tsal(v_mc)
    time.sleep(0.2)
    # hil.check(lval.state == 1, f"LVAL turns back on")
    check.equal(lval.state, 1, f"LVAL turns back on")

    start = tiff_hv_to_lv(0.0)
    stop  = tiff_hv_to_lv(R_TSAL_HV_V * 1.5)
    step  = tiff_hv_to_lv(1)
    thresh = utils.measure_trip_thresh(v_mc, start, stop, step,
                                       0.01,
                                       tsal, is_falling=False)
    thresh = tiff_lv_to_hv(thresh)
    print(f"TSAL on at {thresh:.4} V")
    # hil.check_within(thresh, R_TSAL_HV_V, 4, f"TSAL trips at {R_TSAL_HV_V:.4} +-4")
    # hil.check(lval.state == 0, f"LVAL off  V")
    # hil.check(tsal.state == 1, f"TSAL on V")
    check.almost_equal(thresh, R_TSAL_HV_V, abs=4, rel=0.0, msg=f"TSAL trips at {R_TSAL_HV_V:.4} +-4")
    check.equal(lval.state, 0, f"LVAL off  V")
    check.equal(tsal.state, 1, f"TSAL on V")

    # hil.end_test()
# ---------------------------------------------------------------------------- #
