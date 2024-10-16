from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil.hil import HIL
import hil.utils as utils
import time
from rules_constants import *
from vehicle_constants import *


import pytest_check as check
import pytest



# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    hil_instance.load_config("config_abox_bench.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_abox_ams(hil):
    # Begin the test
    # hil.start_test(test_abox_ams.__name__)

    # Outputs
    den = hil.dout("a_box", "Discharge Enable")
    csafe = hil.dout("a_box", "Charger Safety")
    bms_override = hil.daq_var("a_box", "bms_daq_override")
    bms_stat = hil.daq_var("a_box", "bms_daq_stat")

    # Inputs
    chrg_stat = hil.din("a_box", "BMS Status Charger")
    main_stat = hil.din("a_box", "BMS Status PDU")

    bms_override.state = 1

    for i in range(0, 8):
        dchg_set = bool(i & 0x1)
        chg_set = bool(i & 0x2)
        bms_set = bool(i & 0x4)
        exp_chrg = not (chg_set or bms_set)
        exp_dchg = not (dchg_set or bms_set)

        den.state = dchg_set
        csafe.state = chg_set
        bms_stat.state = bms_set
        print(f"Combo {i}")
        time.sleep(0.1)
        # hil.check(chrg_stat.state == exp_chrg, f"Chrg stat {exp_chrg}")
        # hil.check(main_stat.state == exp_dchg, f"Main stat {exp_dchg}")
        check.equal(chrg_stat.state, exp_chrg, f"Chrg stat {exp_chrg}")
        check.equal(main_stat.state, exp_dchg, f"Main stat {exp_dchg}")

    bms_override.state = 0

    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_isense(hil):
    # Begin the test
    # hil.start_test(test_isense.__name__)

    # Outputs
    ch1_raw = hil.aout("a_box", "Isense_Ch1_raw")

    # Inputs
    ch1_filt = hil.ain("a_box", "ISense Ch1")

    # Need to test voltage divider transfer function correct
    for v in [0.0, DHAB_S124_MIN_OUT_V, DHAB_S124_OFFSET_V, 3.2, DHAB_S124_MAX_OUT_V, 5.0]:
        ch1_raw.state = v
        time.sleep(1)
        exp_out = ABOX_DHAB_CH1_DIV.div(v)
        input(f"enter to meas, set to {v}, expected {exp_out}")
        meas = ch1_filt.state
        print(f"isense expected: {exp_out}V, measured: {meas}V")
        # hil.check_within(meas, exp_out, 0.05, f"Isense v={v:.3}")
        check.almost_equal(meas, exp_out, abs=0.05, rel=0.0, msg=f"Isense v={v:.3}")

    ch1_raw.hiZ()
    time.sleep(0.01)
    # hil.check_within(ch1_filt.state, 0.0, 0.05, f"Isense float pulled down")
    check.almost_equal(ch1_filt.state, 0.0, abs=0.05, rel=0.0, msg="Isense float pulled down")

    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
RLY_ON  = 0
RLY_OFF = 1
RLY_DLY = 0.01 # Mechanicl relay takes time to transition

def test_precharge(hil):
    # Begin the test
    # hil.start_test(test_precharge.__name__)

    # Outputs
    n_pchg_cmplt = hil.dout("a_box", "NotPrechargeComplete")
    sdc          = hil.dout("a_box", "SDC")
    bat_p        = hil.dout("a_box", "Batt+")

    # Inputs
    resistor = hil.din("a_box", "NetK1_4") # To precharge resistor

    bat_p.state = RLY_ON

    print("Combo 1")
    n_pchg_cmplt.state = 0 
    sdc.state   = RLY_OFF
    time.sleep(RLY_DLY)
    # hil.check(resistor.state == 0, "Resistor disconnected")
    check.equal(resistor.state, 0, "Combo 1, resistor disconnected")

    print("Combo 2")
    n_pchg_cmplt.state = 1
    sdc.state   = RLY_OFF
    time.sleep(RLY_DLY)
    # hil.check(resistor.state == 0, "Resistor disconnected")
    check.equal(resistor.state, 0, "Combo 2, resistor disconnected")

    print("Combo 3")
    n_pchg_cmplt.state = 1
    sdc.state   = RLY_ON
    time.sleep(RLY_DLY)
    # hil.check(resistor.state == 1, "Resistor connected")
    check.equal(resistor.state, 1, "Combo 3, resistor connected")

    print("Combo 4")
    n_pchg_cmplt.state = 0
    sdc.state   = RLY_ON
    time.sleep(RLY_DLY)
    # hil.check(resistor.state == 0, "Resistor disconnected")
    check.equal(resistor.state, 0, "Combo 4, resistor disconnected")

    # Duration test
    time.sleep(1)
    n_pchg_cmplt.state = 1
    sdc.state   = RLY_ON
    time.sleep(RLY_DLY)
    # hil.check(resistor.state == 1, "Duration init")
    check.equal(resistor.state, 1, "Duration init")

    time.sleep(9)
    # hil.check(resistor.state == 1, "Duration mid")
    check.equal(resistor.state, 1, "Duration mid")

    n_pchg_cmplt.state = 0
    time.sleep(RLY_DLY)
    # hil.check(resistor.state == 0, "Duration end")
    check.equal(resistor.state, 0, "Duration end")

    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
SUPPLY_VOLTAGE = 24.0
TIFF_DLY = 0.3

def test_tiffomy(hil):
    # Begin the test
    # hil.start_test(test_tiffomy.__name__)

    # Outputs
    bat_p = hil.dout("a_box", "Batt+")

    # Inputs
    vbat   = hil.ain("a_box", "VBatt")
    imd_hv = hil.din("a_box", "Batt+_Fused")

    # NOTE: the IMD test confirms that the relay closed
    # This is a bit redundant of the tiffomy voltage measurement

    utils.log_warning(f"Assuming supply = {SUPPLY_VOLTAGE} V")
    utils.log_warning(f"Do not reverse polarity Vbat, it will kill Arduino ADC")
    input("Click enter to acknowledge or ctrl+c to cancel")

    bat_p.state = RLY_OFF
    time.sleep(TIFF_DLY)
    # hil.check_within(vbat.state, 0.0, 0.1, "TIff off")
    # hil.check(imd_hv.state == 0, "IMD HV off")
    check.almost_equal(vbat.state, 0.0, abs=0.1, rel=0.0, msg="TIff off")
    check.equal(imd_hv.state, 0, "IMD HV off")

    bat_p.state = RLY_ON
    time.sleep(TIFF_DLY)
    exp = SUPPLY_VOLTAGE
    #input("press enter, tiff should be getting volts")
    meas = tiff_lv_to_hv(vbat.state)
    print(f"Tiff HV reading: {meas} V, expect: {SUPPLY_VOLTAGE} V")
    # hil.check_within(meas, exp, 2.5, "Tiff on")
    # hil.check(imd_hv.state == 1, "IMD HV on")
    check.almost_equal(meas, exp, abs=2.5, rel=0.0, msg="Tiff on")
    check.equal(imd_hv.state, 1, "IMD HV on")

    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_tmu(hil):
    # Begin the test
    # hil.start_test(test_tmu.__name__)

    # Outputs
    tmu_a_do = hil.dout("a_box", "TMU_1")
    tmu_b_do = hil.dout("a_box", "TMU_2")
    tmu_c_do = hil.dout("a_box", "TMU_3")
    tmu_d_do = hil.dout("a_box", "TMU_4")

    daq_override = hil.daq_var("a_box", "tmu_daq_override")
    daq_therm    = hil.daq_var("a_box", "tmu_daq_therm")

    # Inputs
    mux_a = hil.din("a_box", "MUX_A_NON_ISO")
    mux_b = hil.din("a_box", "MUX_B_NON_ISO")
    mux_c = hil.din("a_box", "MUX_C_NON_ISO")
    mux_d = hil.din("a_box", "MUX_D_NON_ISO")

    tmu_a_ai = hil.daq_var("a_box", "tmu_1")
    tmu_b_ai = hil.daq_var("a_box", "tmu_2")
    tmu_c_ai = hil.daq_var("a_box", "tmu_3")
    tmu_d_ai = hil.daq_var("a_box", "tmu_4")

    daq_therm.state = 0
    daq_override.state = 1

    # mux line test
    for i in range(0,16):
        daq_therm.state = i
        time.sleep(0.05)
        # hil.check(mux_a.state == bool(i & 0x1), f"Mux A test {i}")
        # hil.check(mux_b.state == bool(i & 0x2), f"Mux B test {i}")
        # hil.check(mux_c.state == bool(i & 0x4), f"Mux C test {i}")
        # hil.check(mux_d.state == bool(i & 0x8), f"Mux D test {i}")
        check.equal(mux_a.state, bool(i & 0x1), f"Mux A test {i}")
        check.equal(mux_b.state, bool(i & 0x2), f"Mux B test {i}")
        check.equal(mux_c.state, bool(i & 0x4), f"Mux C test {i}")
        check.equal(mux_d.state, bool(i & 0x8), f"Mux D test {i}")

    daq_override.state = 0

    TMU_TOLERANCE = 100
    TMU_HIGH_VALUE = 1970 #2148

    # thermistors
    for i in range(0,16):
        tmu_a_do.state = bool(i & 0x1)
        tmu_b_do.state = bool(i & 0x2)
        tmu_c_do.state = bool(i & 0x4)
        tmu_d_do.state = bool(i & 0x8)
        time.sleep(1.0)
        a = int(tmu_a_ai.state)
        b = int(tmu_b_ai.state)
        c = int(tmu_c_ai.state)
        d = int(tmu_d_ai.state)
        print(f"Readings at therm={i}: {a}, {b}, {c}, {d}")
        # hil.check_within(a, TMU_HIGH_VALUE if (i & 0x1) else 0, TMU_TOLERANCE, f"TMU 1 test {i}")
        # hil.check_within(b, TMU_HIGH_VALUE if (i & 0x2) else 0, TMU_TOLERANCE, f"TMU 2 test {i}")
        # hil.check_within(c, TMU_HIGH_VALUE if (i & 0x4) else 0, TMU_TOLERANCE, f"TMU 3 test {i}")
        # hil.check_within(d, TMU_HIGH_VALUE if (i & 0x8) else 0, TMU_TOLERANCE, f"TMU 4 test {i}")
        check.almost_equal(a, TMU_HIGH_VALUE if (i & 0x1) else 0, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU 1 test {i}")
        check.almost_equal(b, TMU_HIGH_VALUE if (i & 0x2) else 0, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU 2 test {i}")
        check.almost_equal(c, TMU_HIGH_VALUE if (i & 0x4) else 0, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU 3 test {i}")
        check.almost_equal(d, TMU_HIGH_VALUE if (i & 0x8) else 0, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU 4 test {i}")

    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_imd(hil):
    # hil.start_test(test_imd.__name__)

    # Outputs
    imd_out = hil.dout('a_box', 'IMD_Status')

    # Inputs
    imd_in = hil.din('a_box', 'IMD_STATUS_LV_COMP')
    imd_mcu = hil.mcu_pin('a_box', 'IMD_STATUS_LV_COMP')

    
    imd_out.state = RLY_OFF
    time.sleep(RLY_DLY)

    # hil.check(imd_in.state == 0, 'IMD LV OFF')
    # hil.check(imd_mcu.state == 0, 'IMD MCU OFF')
    check.equal(imd_in.state, 0, 'IMD LV OFF')
    check.equal(imd_mcu.state, 0, 'IMD MCU OFF')

    imd_out.state = RLY_ON
    time.sleep(RLY_DLY)

    # hil.check(imd_in.state == 1, 'IMD LV ON')
    # hil.check(imd_mcu.state == 1, 'IMD MCU ON')
    check.equal(imd_in.state, 1, 'IMD LV ON')
    check.equal(imd_mcu.state, 1, 'IMD MCU ON')

    imd_out.state = RLY_OFF
    time.sleep(RLY_DLY)

    # hil.check(imd_in.state == 0, 'IMD LV BACK OFF')
    # hil.check(imd_mcu.state == 0, 'IMD MCU BACK OFF')
    check.equal(imd_in.state, 0, 'IMD LV BACK OFF')
    check.equal(imd_mcu.state, 0, 'IMD MCU BACK OFF')

    # hil.end_test()
# ---------------------------------------------------------------------------- #