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

IMD_STAT_OKAY = 1
IMD_STAT_TRIP = 0

CYCLE_POWER_OFF_DELAY = 2.0
CYCLE_POWER_ON_DELAY = 3.0

def reset_imd(imd_stat):
    imd_stat.state = IMD_STAT_OKAY

def reset_ams(ams_stat):
    ams_stat.state = AMS_STAT_OKAY

def cycle_power(power):
    power.state = 1
    time.sleep(CYCLE_POWER_OFF_DELAY)
    power.state = 0
    time.sleep(CYCLE_POWER_ON_DELAY)


IMD_RC_MIN_TRIP_TIME_S = IMD_STARTUP_TIME_S
IMD_RC_MAX_TRIP_TIME_S = R_IMD_MAX_TRIP_TIME_S - IMD_MEASURE_TIME_S
IMD_CTRL_OKAY = 1
IMD_CTRL_TRIP = 0
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    global power

    hil_instance = HIL()

    hil_instance.load_config("config_charger.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    # hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown()

@pytest.fixture(scope="session")
def power(hil):
    power = hil.dout("RearTester", "RLY1")
    return power
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_imd(hil, power):
    # HIL outputs (hil writes)
    imd_stat  = hil.dout("Charger", "IMD_STATUS")
    ams_stat  = hil.dout("Charger", "BMS_STATUS") # To set SDC status to okay

    # HIL inputs (hil reads)
    imd_ctrl  = hil.din("Main_Module", "SDC_FINAL") # assuming AMS closed

    # Set other SDC nodes to okay
    reset_ams(ams_stat)

    # IMD Fault
    reset_imd(imd_stat)
    cycle_power(power)
    check.equal(imd_ctrl.state, IMD_CTRL_OKAY, "Power On")

    time.sleep(1)
    imd_stat.state = IMD_STAT_TRIP
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    check.between(t, IMD_RC_MIN_TRIP_TIME_S, IMD_RC_MAX_TRIP_TIME_S, "IMD Trip Time")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Trip")

    imd_stat.state = IMD_STAT_OKAY
    time.sleep(IMD_RC_MAX_TRIP_TIME_S * 1.1)
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Fault Stays Latched")

    # IMD Fault on Power On
    reset_imd(imd_stat)
    imd_stat.state = IMD_STAT_TRIP
    cycle_power(power)
    time.sleep(IMD_RC_MAX_TRIP_TIME_S)
    # hil.check(imd_ctrl.state == IMD_CTRL_TRIP, "IMD Fault Power On")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Fault Power On")

    # IMD Floating
    reset_imd(imd_stat)
    imd_stat.hiZ()
    cycle_power(power)
    t = utils.measure_trip_time(imd_ctrl, R_IMD_MAX_TRIP_TIME_S, is_falling=True)
    check.less(t, R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Floating Trip")
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_ams(hil, power):
    # HIL outputs (hil writes)
    ams_stat  = hil.dout("Charger", "BMS_STATUS")
    imd_stat  = hil.dout("Charger", "IMD_STATUS") # To set SDC status to okay

    # HIL inputs (hil reads)
    ams_ctrl  = hil.din("Main_Module", "SDC_FINAL") # assuming AMS closed

    # Set other SDC nodes to okay
    reset_imd(imd_stat)

    # AMS Fault
    reset_ams(ams_stat)
    cycle_power(power)
    # hil.check(ams_ctrl.state == AMS_CTRL_OKAY, "Power On")
    check.equal(ams_ctrl.state, AMS_CTRL_OKAY, "Power On")

    time.sleep(1)
    ams_stat.state = AMS_STAT_TRIP
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    check.between(t, 0, AMS_MAX_TRIP_DELAY_S, "AMS Trip Time")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Trip")

    ams_stat.state = AMS_STAT_OKAY
    time.sleep(AMS_MAX_TRIP_DELAY_S * 1.1)
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Fault Stays Latched")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Fault Stays Latched")

    # AMS Fault on Power On
    reset_ams(ams_stat)
    ams_stat.state = AMS_STAT_TRIP
    cycle_power(power)
    time.sleep(AMS_MAX_TRIP_DELAY_S)
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Fault Power On")

    # AMS Floating
    reset_ams(ams_stat)
    ams_stat.hiZ()
    cycle_power(power)
    t = utils.measure_trip_time(ams_ctrl, AMS_MAX_TRIP_DELAY_S * 2, is_falling=True)
    check.between(t, 0, AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time", ge=True)
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Floating Trip")
# ---------------------------------------------------------------------------- #
