from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))

from hil import HIL
# import hil.utils as utils
import utils
import time
from rules_constants import *
from vehicle_constants import *

import pytest_check as check
import pytest


# ---------------------------------------------------------------------------- #
AMS_STAT_OKAY = 1
AMS_STAT_TRIP = 0
AMS_CTRL_OKAY = 1
AMS_CTRL_TRIP = 0

def reset_ams(ams_stat):
    ams_stat.state = AMS_STAT_OKAY

IMD_STAT_OKAY = 1
IMD_STAT_TRIP = 0
def reset_imd(imd_stat):
    imd_stat.state = IMD_STAT_OKAY

power = None

CYCLE_POWER_OFF_DELAY = 2.0
CYCLE_POWER_ON_DELAY = 3.0

def cycle_power():
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
    
    power = hil_instance.dout("RearTester", "RLY1")
    
    yield hil_instance
    
    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_imd(hil):
    # Begin the test
    # hil.start_test(test_imd.__name__)

    # Outputs
    imd_stat  = hil.dout("Charger", "IMD_STATUS")

    # Outputs to set SDC status to okay
    ams_stat  = hil.dout("Charger", "BMS_STATUS")

    # Inputs
    imd_ctrl  = hil.din("Main_Module", "SDC_FINAL") # assuming AMS closed

    # Set other SDC nodes to okay
    reset_ams(ams_stat)

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
    check.less(t, R_IMD_MAX_TRIP_TIME_S, "IMD Floating Trip Time")
    check.equal(imd_ctrl.state, IMD_CTRL_TRIP, "IMD Floating Trip") 
    
    # hil.end_test()
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def test_ams(hil):
    # Begin the test
    hil.start_test(test_ams.__name__)

    # Outputs
    ams_stat  = hil.dout("Charger", "BMS_STATUS")


    # Outputs to set SDC status to okay
    imd_stat  = hil.dout("Charger", "IMD_STATUS")

    # Inputs
    ams_ctrl  = hil.din("Main_Module", "SDC_FINAL") # assuming AMS closed

    # Set other SDC nodes to okay
    reset_imd(imd_stat)

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
    # hil.check(0 <= t < AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time")
    # hil.check(ams_ctrl.state == AMS_CTRL_TRIP, "AMS Floating Trip")
    check.between(t, 0, AMS_MAX_TRIP_DELAY_S, "AMS Floating Trip Time")
    check.equal(ams_ctrl.state, AMS_CTRL_TRIP, "AMS Floating Trip")
    
    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
    # hil = HIL()

    # hil.load_config("config_charger.json")
    # hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    #hil.init_can()

    # power = hil.dout("RearTester", "RLY1")

    test_imd()
    test_ams()

    # hil.shutdown()
# ---------------------------------------------------------------------------- #