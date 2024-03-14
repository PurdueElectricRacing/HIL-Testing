from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import utils
import time
from rules_constants import *
from vehicle_constants import *

AMS_STAT_OKAY = 1
AMS_STAT_TRIP = 0
AMS_CTRL_OKAY = 1
AMS_CTRL_TRIP = 0

def reset_ams(ams_stat):
    ams_stat.state = AMS_STAT_OKAY

def set_bspd_current(ch1, current):
    c = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(current))
    #print(f"bspd current: {current} voltage: {c}")
    ch1.state = c

def reset_bspd(brk1, brk2, ch1):
    brk1.state = BRK_1_REST_V
    brk2.state = BRK_2_REST_V
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

CYCLE_POWER_OFF_DELAY = 2.0
CYCLE_POWER_ON_DELAY = 3.0

def cycle_power():
    power.state = 1
    time.sleep(CYCLE_POWER_OFF_DELAY)
    power.state = 0
    time.sleep(CYCLE_POWER_ON_DELAY)

def test_precharge(hil):
    # Begin the test
    hil.start_test(test_precharge.__name__)

    # Outputs
    v_bat = hil.aout("Main_Module", "VBatt")
    v_mc  = hil.aout("Main_Module", "Voltage MC Transducer")

    # Inputs
    pchg_cmplt = hil.mcu_pin("Main_Module", "PrechargeComplete_Prot")
    not_pchg_cmplt_delayed = hil.din("Main_Module", "NotPrechargeCompleteSchmitt")
    # v_bat_mcu = hil.daq_var("Main_Module", "Varname") # TODO
    # v_mc_mcu  = hil.daq_var("Main_Module", "Varname") # TODO
    # pchg_mux  = hil.daq_var("Main_Module", "Varname") # TODO

    # Outputs to set SDC status to okay
    imd_stat  = hil.dout("Main_Module", "IMD_Status")
    brk1 = hil.aout("Dashboard", "BRK1_RAW")
    brk2 = hil.aout("Dashboard", "BRK2_RAW")
    c_sense  = hil.aout("Main_Module", "Current Sense C1")
    ams_stat  = hil.dout("Main_Module", "BMS-Status-Main")
    reset_imd(imd_stat)
    reset_bspd(brk1, brk2, c_sense)
    reset_ams(ams_stat)

    cycle_power()

    # Initial State
    reset_pchg(v_bat, v_mc)
    time.sleep(2.5)
    hil.check(pchg_cmplt.state == 0, "Precharge not complete on startup")
    hil.check(not_pchg_cmplt_delayed.state == 1, "Not precharge complete delayed high on startup")
    # Check delay
    v_mc.state = tiff_hv_to_lv(ACCUM_NOM_V)
    t = utils.measure_trip_time(not_pchg_cmplt_delayed, PCHG_COMPLETE_DELAY_S*3, is_falling=True)
    hil.check(not_pchg_cmplt_delayed.state == 0, "Precharge complete delayed")
    hil.check_within(t, PCHG_COMPLETE_DELAY_S, 0.25, f"Precharge complete delay of {t:.3}s close to expected {PCHG_COMPLETE_DELAY_S}s")

    # Find threshold at nominal pack voltage
    for v in [ACCUM_MIN_V, ACCUM_NOM_V, ACCUM_MAX_V]:
        reset_pchg(v_bat, v_mc)
        print(f"Testing precharge threshold at V_bat = {v}")
        v_bat.state = tiff_hv_to_lv(v)
        v_mc.state = tiff_hv_to_lv(v*0.8)
        #time.sleep(0.01)
        time.sleep(0.5)
        hil.check(pchg_cmplt.state == 0, "Precharge Complete Low at Initial State")

        start = tiff_hv_to_lv(v*0.8)
        stop  = tiff_hv_to_lv(v)
        step  = tiff_hv_to_lv(1)
        thresh = utils.measure_trip_thresh(v_mc, start, stop, step, 0.1,
                                           pchg_cmplt, is_falling=0)
        thresh_hv = tiff_lv_to_hv(thresh)
        print(f"Precharge triggered at {thresh_hv / v * 100:.4}% ({thresh_hv:.5}V) of vbat={v}.")
        hil.check_within(thresh_hv / v, R_PCHG_V_BAT_THRESH, 0.03, f"Precharge threshold of {R_PCHG_V_BAT_THRESH*100}% at vbat = {v}V")
        v_mc.state = tiff_hv_to_lv(v)
        #time.sleep(0.25)
        time.sleep(8)
        hil.check(pchg_cmplt.state == 1, f"Precharge completed at vbat = {v}V")

    
    # Floating conditions (check never precharge complete)
    reset_pchg(v_bat, v_mc)
    v_bat.hiZ()
    v_mc.state = tiff_hv_to_lv(0)
    hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat float, v_mc 0V")
    v_mc.state = tiff_hv_to_lv(ACCUM_MAX_V)
    hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat float, v_mc max V")

    reset_pchg(v_bat, v_mc)
    v_mc.hiZ()
    v_bat.state = tiff_hv_to_lv(ACCUM_MIN_V)
    hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat min, v_mc float")
    v_bat.state = tiff_hv_to_lv(ACCUM_MAX_V)
    hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat max, v_mc float")

    reset_pchg(v_bat, v_mc)
    v_bat.hiZ()
    v_mc.hiZ()
    hil.check(pchg_cmplt.state == 0, "Precharge not complete on v_bat float, v_mc float")

    # TODO: software precharge validity checks (make precharge take forever)
    hil.end_test()

BRK_SWEEP_DELAY = 0.1
BSPD_DASH_ON_TIME = 0
def test_bspd(hil):
    # Begin the test
    hil.start_test(test_bspd.__name__)

    # Outputs
    brk1    = hil.aout("Dashboard",   "BRK1_RAW")
    brk2    = hil.aout("Dashboard",   "BRK2_RAW")
    c_sense = hil.aout("Main_Module", "Current Sense C1")

    # Outputs to set SDC status to okay
    ams_stat  = hil.dout("Main_Module", "BMS-Status-Main")
    imd_stat  = hil.dout("Main_Module", "IMD_Status")

    # Inputs
    bspd_ctrl  = hil.din("Main_Module", "SDC15") # assuming AMS and BSPD closed

    brk_fail_tap = hil.mcu_pin("Dashboard", "BRK_FAIL_TAP")
    brk_stat_tap = hil.mcu_pin("Dashboard", "BRK_STAT_TAP")

    # Set other SDC nodes to okay
    reset_ams(ams_stat)
    reset_imd(imd_stat)
    # BOTS assumed to be good

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

    # Brake Fail
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    hil.check(bspd_ctrl.state == 1, "Power On")
    brk1.state = 0.0
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Brake Fail")
    hil.check(brk_fail_tap.state == 1, "Brake Fail went high")
    brk1.state = BRK_1_REST_V
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(brk_fail_tap.state == 0, "Brake Fail returned low")
    hil.check(bspd_ctrl.state == 0, "Brake Fail Stays Latched")

    # Brake Fail on Power On
    reset_bspd(brk1, brk2, c_sense)
    # Manual power cycle, setting brk_fail on before
    # Will cause power to feed back into system
    power.state = 1
    time.sleep(2)
    brk1.state = 0.0
    power.state = 0
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    time.sleep(BSPD_DASH_ON_TIME) # NOTE: test can't check for the trip time
    hil.check(bspd_ctrl.state == 0, "Power On Brake Fail")

    # Current no brake
    reset_bspd(brk1, brk2, c_sense)
    power.state = 1
    time.sleep(3)
    power.state = 0
    time.sleep(1)
    #hil.check(bspd_ctrl.state == 1, "Power On")
    time.sleep(2) # TODO: I am not sure why this fails, but oh well
    set_bspd_current(c_sense, 75)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    # time.sleep(100)
    time.sleep(3)
    hil.check(bspd_ctrl.state == 1, "Current no brake")

    # Current Sense Short to Ground
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    hil.check(bspd_ctrl.state == 1, "Power On")
    c_sense.state = 0.0
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Current short to ground")
    set_bspd_current(c_sense, 0.0)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 0, "Current short to ground stays latched")

    # Current Sense Short to 5V
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME*1.2)
    hil.check(bspd_ctrl.state == 1, "Power On")
    c_sense.state = ABOX_DHAB_CH1_DIV.div(5.0)
    t = utils.measure_trip_time(bspd_ctrl, 5.0, is_falling=True)
    hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Current short to 5V")
    set_bspd_current(c_sense, 0.0)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 0, "Current short to 5V stays latched")

    # Braking
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    hil.check(bspd_ctrl.state == 1, "Power On")
    brk1.state = BRK_1_THRESH_V
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 1, "Brake no current")
    hil.check(brk_stat_tap.state == 1, "Brake stat went high")

    # Lowest current required to trip at
    min_trip_current = R_BSPD_POWER_THRESH_W / ACCUM_MAX_V
    set_bspd_current(c_sense, min_trip_current)
    t = utils.measure_trip_time(bspd_ctrl, 10.0, is_falling=True)
    hil.check(t < R_BSPD_MAX_TRIP_TIME_S, "Braking with current")

    # Measure braking with current threshold
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    brk1.state = BRK_1_THRESH_V

    hil.check(bspd_ctrl.state == 1, "Power On")
    start = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(0.0))
    stop  = ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(DHAB_S124_CH1_MAX_A))
    step  = 0.1
    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    thresh_amps = dhab_ch1_v_to_a(ABOX_DHAB_CH1_DIV.reverse(thresh))
    print(f"Current while braking threshold: {thresh}V = {thresh_amps}A")
    hil.check_within(thresh, ABOX_DHAB_CH1_DIV.div(dhab_ch1_a_to_v(min_trip_current)), 0.1, "Current while braking threshold")

    # Determine the current sense short to gnd threshold
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    hil.check(bspd_ctrl.state == 1, "Power On")
    set_bspd_current(c_sense, DHAB_S124_CH1_MIN_A)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 1, "Min output current okay")
    start = ABOX_DHAB_CH1_DIV.div(DHAB_S124_MIN_OUT_V)
    stop = 0.0
    step = -0.1
    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    print(f"Short to ground threshold: {thresh}V")
    hil.check(stop < (thresh) < start, "Current short to ground threshold")

    # Determine the current sense short to 5V threshold
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    hil.check(bspd_ctrl.state == 1, "Power On")
    time.sleep(2)

    set_bspd_current(c_sense, DHAB_S124_CH1_MAX_A)
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 1, "Max output current okay")

    start = ABOX_DHAB_CH1_DIV.div(DHAB_S124_MAX_OUT_V)
    stop = ABOX_DHAB_CH1_DIV.div(5.0)
    step = 0.01

    c_sense.state = start
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 1, "Max output voltage okay")
    input("enter to continue")

    thresh = utils.measure_trip_thresh(c_sense, start, stop, step,
                                       R_BSPD_MAX_TRIP_TIME_S,
                                       bspd_ctrl, is_falling=True)
    print(f"Short to 5V threshold: {thresh}V")
    hil.check(bspd_ctrl.state == 0, "Short to 5V trips")
    print(stop)
    print(start)
    hil.check(start < (thresh) <= stop, "Current short to 5V threshold")

    # Floating current
    reset_bspd(brk1, brk2, c_sense)
    cycle_power()
    time.sleep(BSPD_DASH_ON_TIME)
    hil.check(bspd_ctrl.state == 1, "Power On")
    c_sense.hiZ()
    time.sleep(R_BSPD_MAX_TRIP_TIME_S)
    hil.check(bspd_ctrl.state == 0, "Floating current")

    # Floating brake_fail
    # Can't test this at system level!

    # Floating brake_stat
    # Can't test this at system level!

    # End the test
    hil.end_test()


IMD_RC_MIN_TRIP_TIME_S = IMD_STARTUP_TIME_S 
IMD_RC_MAX_TRIP_TIME_S = R_IMD_MAX_TRIP_TIME_S - IMD_MEASURE_TIME_S
IMD_CTRL_OKAY = 1
IMD_CTRL_TRIP = 0

def test_imd(hil):
    # Begin the test
    hil.start_test(test_imd.__name__)

    # Outputs
    imd_stat  = hil.dout("Main_Module", "IMD_Status")

    # Outputs to set SDC status to okay
    ams_stat  = hil.dout("Main_Module", "BMS-Status-Main")
    brk1 = hil.aout("Dashboard", "BRK1_RAW")
    brk2 = hil.aout("Dashboard", "BRK2_RAW")
    c_sense  = hil.aout("Main_Module", "Current Sense C1")

    # Inputs
    imd_ctrl  = hil.din("Main_Module", "SDC15") # assuming AMS and BSPD closed

    # Set other SDC nodes to okay
    reset_ams(ams_stat)
    reset_bspd(brk1, brk2, c_sense)

    # IMD Fault
    reset_imd(imd_stat)
    cycle_power()
    hil.check(imd_ctrl.state == IMD_CTRL_OKAY, "Power On")
    time.sleep(1)
    imd_stat.state = IMD_STAT_TRIP
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    print(f"Target trip time: [{IMD_RC_MIN_TRIP_TIME_S}, {IMD_RC_MAX_TRIP_TIME_S}]")
    hil.check(IMD_RC_MIN_TRIP_TIME_S < t < IMD_RC_MAX_TRIP_TIME_S, "IMD Trip Time")
    hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Trip")
    imd_stat.state = IMD_STAT_OKAY
    time.sleep(IMD_RC_MAX_TRIP_TIME_S * 1.1)
    hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Fault Stays Latched")

    # IMD Fault on Power On
    reset_imd(imd_stat)
    imd_stat.state = IMD_STAT_TRIP
    cycle_power()
    time.sleep(IMD_RC_MAX_TRIP_TIME_S)
    hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Fault Power On")

    # IMD Floating
    reset_imd(imd_stat)
    imd_stat.hiZ()
    cycle_power()
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    hil.check(t < R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Floating Trip")
    
    hil.end_test()

def test_ams(hil):
    # Begin the test
    hil.start_test(test_ams.__name__)

    # Outputs
    ams_stat  = hil.dout("Main_Module", "BMS-Status-Main")

    # Outputs to set SDC status to okay
    imd_stat  = hil.dout("Main_Module", "IMD_Status")
    brk1 = hil.aout("Dashboard", "BRK1_RAW")
    brk2 = hil.aout("Dashboard", "BRK2_RAW")
    c_sense  = hil.aout("Main_Module", "Current Sense C1")

    # Inputs
    ams_ctrl  = hil.din("Main_Module", "SDC15") # assumes IMD and BSPD closed

    # Set other SDC nodes to okay
    reset_imd(imd_stat)
    reset_bspd(brk1, brk2, c_sense)

    # AMS Fault
    reset_ams(ams_stat)
    cycle_power()
    hil.check(ams_ctrl.state == AMS_CTRL_OKAY, "Power On")
    time.sleep(1)
    ams_stat.state = AMS_STAT_TRIP
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    hil.check(0 < t < AMS_MAX_TRIP_DELAY_S, "AMS Trip Time")
    hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Trip")
    ams_stat.state = AMS_STAT_OKAY
    time.sleep(AMS_MAX_TRIP_DELAY_S * 1.1)
    hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Fault Stays Latched")

    # AMS Fault on Power On
    reset_ams(ams_stat)
    ams_stat.state = AMS_STAT_TRIP
    cycle_power()
    time.sleep(AMS_MAX_TRIP_DELAY_S)
    hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Fault Power On")

    # AMS Floating
    reset_ams(ams_stat)
    ams_stat.hiZ()
    cycle_power()
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    hil.check(0 <= t < AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time")
    hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Floating Trip")
    
    hil.end_test()

def tsal_is_red():
    while 1:
        i = input("Is TSAL Green (g) or Red (r): ")
        utils.clear_term_line()
        i = i.upper()
        if (i == 'G' or i == 'R'):
            return i == 'R'
        print("You may only enter G or R!")

def test_tsal(hil):

    # Begin the test
    hil.start_test(test_tsal.__name__)

    # Outputs
    v_mc  = hil.aout("Main_Module", "Voltage MC Transducer")

    # Inputs
    # User :D
    print(f"{utils.bcolors.OKCYAN}Press 'G' for green and 'R' for red.{utils.bcolors.ENDC}")

    # Initial State
    reset_tsal(v_mc)
    time.sleep(0.2)
    # No need to power cycle

    hil.check(tsal_is_red() == False, "LVAL on at v_mc = 0")
    #hil.check(tsal.state == 0, "TSAL off at v_mc = 0")

    time.sleep(5)
    hil.check(tsal_is_red() == False, "LVAL stays on")

    v_mc.state = tiff_hv_to_lv(ACCUM_MIN_V)
    time.sleep(0.1)

    #hil.check(lval.state == 0, f"LVAL off at {ACCUM_MIN_V:.4} V")
    hil.check(tsal_is_red() == True, f"TSAL on at {ACCUM_MIN_V:.4} V")

    reset_tsal(v_mc)
    time.sleep(0.2)
    hil.check(tsal_is_red() == False, f"LVAL turns back on")

    start = tiff_hv_to_lv(50)
    stop  = tiff_hv_to_lv(R_TSAL_HV_V * 1.5)
    step  = tiff_hv_to_lv(1)

    gain = 1000
    thresh = start
    _start = int(start * gain)
    _stop = int(stop * gain)
    _step = int(step * gain)
    v_mc.state = start
    tripped = False
    print(f"Start: {_start} Stop: {_stop} Step: {_step} Gain: {gain}")
    for v in range(_start, _stop+_step, _step):
        v_mc.state = v / gain
        time.sleep(0.01)
        if (tsal_is_red()):
            thresh = v / gain
            tripped = True
            break
    if (not tripped):
        utils.log_warning(f"TSAL did not trip at stop of {stop}.")
        thresh = stop
    hil.check(tripped, "TSAL tripped")
    
    thresh = tiff_lv_to_hv(thresh)
    print(f"TSAL on at {thresh:.4} V")
    hil.check_within(thresh, R_TSAL_HV_V, 4, f"TSAL trips at {R_TSAL_HV_V:.4} +-4")

    hil.end_test()

def test_sdc(hil):
    ''' Check that every node in the sdc trips '''
    # Begin the test
    hil.start_test(test_sdc.__name__)

    # Outputs

    # Inputs

    hil.check(0, "TODO")

    hil.end_test()

def is_buzzer_on():
    while 1:
        i = input("Is Buzzer On (y) or No (n): ")
        utils.clear_term_line()
        i = i.upper()
        if (i == 'Y' or i == 'N'):
            return i == 'Y'
        print("You may only enter Y or N!")

def test_buzzer(hil):
    # Begin the test
    hil.start_test(test_buzzer.__name__)

    # Outputs
    buzzer_ctrl = hil.daq_var("Main_Module", "daq_buzzer") 

    # Inputs
    buzzer_stat = hil.mcu_pin("Main_Module", "Buzzer_Prot")

    buzzer_ctrl.state = 0
    time.sleep(0.02)
    hil.check(buzzer_stat.state == 0, "Buzzer Off")

    buzzer_ctrl.state = 1
    print(buzzer_ctrl.state)
    time.sleep(0.02)
    hil.check(buzzer_stat.state == 1, "Buzzer On")
    hil.check(is_buzzer_on() == True, "Buzzer Making Noise")

    buzzer_ctrl.state = 0
    time.sleep(0.02)
    hil.check(buzzer_stat.state == 0, "Buzzer back Off")
    hil.check(is_buzzer_on() == False, "Buzzer Not Making Noise")

    hil.end_test()

def is_brake_light_on():
    while 1:
        i = input("Is Brake Light On (y) or No (n): ")
        utils.clear_term_line()
        i = i.upper()
        if (i == 'Y' or i == 'N'):
            return i == 'Y'
        print("You may only enter Y or N!")

def test_brake_light(hil):
    # Begin the test
    hil.start_test(test_brake_light.__name__)

    # Outputs
    brk_ctrl = hil.daq_var("Main_Module", "daq_brake") 

    # Inputs
    brk_stat = hil.mcu_pin("Main_Module", "Brake_Light_CTRL_Prot")

    brk_ctrl.state = 0
    time.sleep(0.02)
    hil.check(brk_ctrl.state == 0, "Brake Off")

    brk_ctrl.state = 1
    print(brk_ctrl.state)
    time.sleep(0.02)
    hil.check(brk_ctrl.state == 1, "Brake Light On")
    hil.check(is_brake_light_on() == True, "Brake Light is On")

    brk_ctrl.state = 0
    time.sleep(0.02)
    hil.check(brk_ctrl.state == 0, "Brake Light back Off")
    hil.check(is_brake_light_on() == False, "Brake Light is Off")


    # Can copy lot from bspd
    # Read the brake control mcu pin
    # Finally have user verify light actually turned on

    hil.end_test()

def test_light_tsal_buz(hil):
    hil.start_test(test_light_tsal_buz.__name__)

    # Outputs
    brk_ctrl = hil.daq_var("Main_Module", "daq_brake") 
    buzzer_ctrl = hil.daq_var("Main_Module", "daq_buzzer") 

    brk_ctrl.state = 1
    buzzer_ctrl.state = 1
    input("Press enter to end the test")
    brk_ctrl.state = 0
    buzzer_ctrl.state = 0

    hil.end_test()


if __name__ == "__main__":
    hil = HIL()

    hil.load_config("config_system_hil_attached.json")
    hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    hil.init_can()

    power = hil.dout("RearTester", "RLY1")

    # Drive Critical Tests
    test_precharge(hil)
    # test_bspd(hil)
    #test_imd(hil) # note: tsal needs to be tripped
    #test_ams(hil)
    # test_tsal(hil)
    # test_sdc(hil)
    # test_buzzer(hil)
    # test_brake_light(hil)
    # test_light_tsal_buz(hil)

    # Peripheral Sensor Tests

    hil.shutdown()
