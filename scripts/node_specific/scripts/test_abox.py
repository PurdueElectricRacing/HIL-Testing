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
@pytest.mark.parametrize("combo", [0, 1, 2, 3, 4, 5, 6, 7])
def test_abox_ams(hil, combo):
    """Accumulator Management System"""

    # HIL outputs (hil writes)
    discharge_en = hil.dout("a_box", "Discharge Enable")
    charge_safe  = hil.dout("a_box", "Charger Safety")
    bms_override = hil.daq_var("a_box", "bms_daq_override")
    bms_stat     = hil.daq_var("a_box", "bms_daq_stat")

    # HIL inputs (hil reads)
    charge_stat = hil.din("a_box", "BMS Status Charger")
    main_stat   = hil.din("a_box", "BMS Status PDU") # Main power status = discharge

    # Force manual overridec
    bms_override.state = 1

    discharge_set = bool(combo & 0x1)
    charge_set    = bool(combo & 0x2)
    bms_set       = bool(combo & 0x4)
    
    expected_charge    = not (charge_set or bms_set)
    expected_discharge = not (discharge_set or bms_set)

    discharge_en.state = discharge_set
    charge_safe.state  = charge_set
    bms_stat.state     = bms_set
    time.sleep(0.1)

    check.equal(charge_stat.state, expected_charge, f"Charge stat ({combo:b}) {expected_charge}")
    check.equal(main_stat.state, expected_discharge, f"Main stat ({combo:b}) {expected_discharge}")

    # Reset the override
    bms_override.state = 0
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("voltage", [0.0, DHAB_S124_MIN_OUT_V, DHAB_S124_OFFSET_V, 3.2, DHAB_S124_MAX_OUT_V, 5.0])
def test_isense(hil, voltage):
    """Current sensor voltage divider transfer function"""

    # HIL outputs (hil writes)
    ch1_raw = hil.aout("a_box", "Isense_Ch1_raw")

    # HIL inputs (hil reads)
    ch1_filt = hil.ain("a_box", "ISense Ch1")

    ch1_raw.state = voltage
    time.sleep(1)
    expected_out = ABOX_DHAB_CH1_DIV.div(voltage)
    # input(f"enter to meas, set to {v}, expected {exp_out}")
    check.almost_equal(ch1_filt.state, expected_out, abs=0.05, rel=0.0, msg=f"Isense v={voltage:.3}")

    # Test float (hi-Z) is pulled down
    ch1_raw.hiZ()
    time.sleep(0.01)

    check.almost_equal(ch1_filt.state, 0.0, abs=0.05, rel=0.0, msg="Isense float (hi-Z) pulled down")
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
RLY_OFF = 1
RLY_ON  = 0

@pytest.mark.parametrize("n_pchg_cmplt_set, sdc_set, expected_resistor", [
    (0, RLY_OFF, 0),  # Precharge complete, SDC off -> resistor disconnected
    (1, RLY_OFF, 0),  # Precharge active, SDC off -> resistor disconnected
    (1, RLY_ON,  1),  # Precharge active, SDC on  -> resistor connected
    (0, RLY_ON,  0),  # Precharge complete, SDC on -> resistor disconnected
])
def test_not_precharge_complete(hil, n_pchg_cmplt_set, sdc_set, expected_resistor):
    """Not precharge complete"""

    # HIL outputs (hil writes)
    n_pchg_cmplt = hil.dout("a_box", "NotPrechargeComplete")
    sdc          = hil.dout("a_box", "SDC")
    bat_p        = hil.dout("a_box", "Batt+")

    # HIL inputs (hil reads)
    resistor = hil.din("a_box", "NetK1_4") # To precharge resistor

    bat_p.state = RLY_ON

    n_pchg_cmplt.state = n_pchg_cmplt_set
    sdc.state = sdc_set
    time.sleep(0.1)

    message = f"not precharge: {n_pchg_cmplt_set}, sdc: {sdc_set} -> resistor: {expected_resistor}"
    check.equal(resistor.state, expected_resistor, message)

def test_precharge_duration(hil):
    """Precharge duration"""

    # HIL outputs (hil writes)
    n_pchg_cmplt = hil.dout("a_box", "NotPrechargeComplete")
    sdc          = hil.dout("a_box", "SDC")

    # HIL inputs (hil reads)
    resistor = hil.din("a_box", "NetK1_4") # To precharge resistor

    time.sleep(1)
    n_pchg_cmplt.state = 1
    sdc.state = RLY_ON
    time.sleep(0.1)
    check.equal(resistor.state, 1, "Duration start")

    time.sleep(9)
    check.equal(resistor.state, 1, "Duration middle")

    n_pchg_cmplt.state = 0
    time.sleep(0.1)
    check.equal(resistor.state, 0, "Duration end")
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
SUPPLY_VOLTAGE = 24.0
TIFF_DLY = 0.3

def test_tiffomy(hil):
    """Tractive Isolation Fault Detection"""

    # HIL outputs (hil writes)
    bat_p = hil.dout("a_box", "Batt+")

    # HIL inputs (hil reads)
    vbat   = hil.ain("a_box", "VBatt")
    imd_hv = hil.din("a_box", "Batt+_Fused")

    # NOTE: the IMD test confirms that the relay closed
    # This is a bit redundant of the tiffomy voltage measurement

    utils.log_warning(f"Assuming supply = {SUPPLY_VOLTAGE} V")
    utils.log_warning(f"Do not reverse polarity Vbat, it will kill Arduino ADC")
    # input("Click enter to acknowledge or ctrl+c to cancel")

    bat_p.state = RLY_OFF
    time.sleep(TIFF_DLY)

    check.almost_equal(vbat.state, 0.0, abs=0.1, rel=0.0, msg="Tiff off")
    check.equal(imd_hv.state, 0, "IMD HV off")

    bat_p.state = RLY_ON
    time.sleep(TIFF_DLY)
    exp = SUPPLY_VOLTAGE
    #input("press enter, tiff should be getting volts")
    meas = tiff_lv_to_hv(vbat.state)
    check.almost_equal(meas, exp, abs=2.5, rel=0.0, msg="Tiff on")
    check.equal(imd_hv.state, 1, "IMD HV on")
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
TMU_TOLERANCE = 100
TMU_HIGH_VALUE = 1970 #2148

@pytest.mark.parametrize("mux_value", list(range(16)))
def test_tmu_mux(hil, mux_value):
    """Thermal Management Unit MUX"""

    # HIL outputs (hil writes)
    daq_override = hil.daq_var("a_box", "tmu_daq_override")
    daq_therm    = hil.daq_var("a_box", "tmu_daq_therm")

    # HIL inputs (hil reads)
    mux_a = hil.din("a_box", "MUX_A_NON_BOOST")
    mux_b = hil.din("a_box", "MUX_B_NON_BOOST")
    mux_c = hil.din("a_box", "MUX_C_NON_BOOST")
    mux_d = hil.din("a_box", "MUX_D_NON_BOOST")

    daq_therm.state = 0
    daq_override.state = 1

    daq_therm.state = mux_value
    time.sleep(0.05)

    expected_a = bool(mux_value & 0x1)
    expected_b = bool(mux_value & 0x2)
    expected_c = bool(mux_value & 0x4)
    expected_d = bool(mux_value & 0x8)

    check.equal(mux_a.state, expected_a, f"Mux A test ({mux_value})")
    check.equal(mux_b.state, expected_b, f"Mux B test ({mux_value})")
    check.equal(mux_c.state, expected_c, f"Mux C test ({mux_value})")
    check.equal(mux_d.state, expected_d, f"Mux D test ({mux_value})")

    daq_override.state = 0

@pytest.mark.parametrize("combo", list(range(16)))
def test_tmu(hil, combo):
    """Thermal Management Unit temperature sensors"""

    # HIL outputs (hil writes)
    tmu_11_do = hil.dout("a_box", "TMU_1_1")
    tmu_12_do = hil.dout("a_box", "TMU_1_2")
    tmu_21_do = hil.dout("a_box", "TMU_2_1")
    tmu_22_do = hil.dout("a_box", "TMU_2_2")
    tmu_31_do = hil.dout("a_box", "TMU_3_1")
    tmu_32_do = hil.dout("a_box", "TMU_3_2")
    tmu_41_do = hil.dout("a_box", "TMU_4_1")
    tmu_42_do = hil.dout("a_box", "TMU_4_2")

    # HIL inputs (hil reads)
    daq_override = hil.daq_var("a_box", "tmu_daq_override")
    daq_therm    = hil.daq_var("a_box", "tmu_daq_therm")

    tmu_11_ai = hil.daq_var("a_box", "tmu_1_1")
    tmu_12_ai = hil.daq_var("a_box", "tmu_1_2")
    tmu_21_ai = hil.daq_var("a_box", "tmu_2_1")
    tmu_22_ai = hil.daq_var("a_box", "tmu_2_2")
    tmu_31_ai = hil.daq_var("a_box", "tmu_3_1")
    tmu_32_ai = hil.daq_var("a_box", "tmu_3_2")
    tmu_41_ai = hil.daq_var("a_box", "tmu_4_1")
    tmu_42_ai = hil.daq_var("a_box", "tmu_4_2")

    daq_therm.state = 0
    daq_override.state = 0

    a_set = bool(combo & 0x1)
    b_set = bool(combo & 0x2)
    c_set = bool(combo & 0x4)
    d_set = bool(combo & 0x8)

    tmu_11_do.state = a_set
    tmu_12_do.state = a_set
    tmu_21_do.state = b_set
    tmu_22_do.state = b_set
    tmu_31_do.state = c_set
    tmu_32_do.state = c_set
    tmu_41_do.state = d_set
    tmu_42_do.state = d_set
    time.sleep(1.0)

    a1 = int(tmu_11_ai.state)
    a2 = int(tmu_12_ai.state)
    b1 = int(tmu_21_ai.state)
    b2 = int(tmu_22_ai.state)
    c1 = int(tmu_31_ai.state)
    c2 = int(tmu_32_ai.state)
    d1 = int(tmu_41_ai.state)
    d2 = int(tmu_42_ai.state)

    expected_a = TMU_HIGH_VALUE if a_set else 0
    expected_b = TMU_HIGH_VALUE if b_set else 0
    expected_c = TMU_HIGH_VALUE if c_set else 0
    expected_d = TMU_HIGH_VALUE if d_set else 0
    
    check.almost_equal(a1, expected_a, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_1_1 test ({combo})")
    check.almost_equal(a2, expected_a, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_1_2 test ({combo})")
    check.almost_equal(b1, expected_b, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_2_1 test ({combo})")
    check.almost_equal(b2, expected_b, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_2_2 test ({combo})")
    check.almost_equal(c1, expected_c, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_3_1 test ({combo})")
    check.almost_equal(c2, expected_c, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_3_2 test ({combo})")
    check.almost_equal(d1, expected_d, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_4_1 test ({combo})")
    check.almost_equal(d2, expected_d, abs=TMU_TOLERANCE, rel=0.0, msg=f"TMU_4_2 test ({combo})")
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_imd(hil):
    """Insulation Monitoring Device"""

    # HIL outputs (hil writes)
    imd_out = hil.dout('a_box', 'IMD_Status')

    # HIL inputs (hil reads)
    imd_in  = hil.din('a_box', 'IMD_STATUS_LV_COMP')
    imd_mcu = hil.mcu_pin('a_box', 'IMD_STATUS_LV_COMP')

    imd_out.state = RLY_OFF
    time.sleep(0.1)

    check.equal(imd_in.state, 0, 'IMD LV off')
    check.equal(imd_mcu.state, 0, 'IMD MCU off')

    imd_out.state = RLY_ON
    time.sleep(0.1)

    check.equal(imd_in.state, 1, 'IMD LV on')
    check.equal(imd_mcu.state, 1, 'IMD MCU on')

    imd_out.state = RLY_OFF
    time.sleep(0.1)

    check.equal(imd_in.state, 0, 'IMD LV BACK off')
    check.equal(imd_mcu.state, 0, 'IMD MCU BACK off')
# ---------------------------------------------------------------------------- #
