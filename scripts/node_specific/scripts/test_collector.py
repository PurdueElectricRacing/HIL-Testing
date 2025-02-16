from os import sys, path

# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__))))))

from hil.hil import HIL
import hil.utils as utils
import time

import pytest_check as check
import pytest

# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    hil_instance.load_config("config_collector_bench.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    # hil_instance.init_can()

    yield hil_instance

    hil_instance.shutdown()
# ---------------------------------------------------------------------------- #

# Constants
TOP_RES = 30000 # Top resistor of thermistor voltage divider
INPUT_RES = 10000 # Simulated Thermistor resistance
TEST_VOLTAGE = 3.3 # Voltage of measurement on collector plate
THERMISTOR_CONNECTED_VOLTAGE = (TEST_VOLTAGE / (TOP_RES + INPUT_RES)) *  INPUT_RES # Expected voltage when thermistor is connected
# THERMISTOR_CONNECTED_VOLTAGE = 0.85
THERMISTOR_DISCONNECTED_VOLTAGE = 3.0 # Expected voltage when thermistor is disconnected
TOLERANCE_V = 0.15 # Tolerance to account for resistors, measurement inaccuracy, etc
DISCONNECTED_TOLERANC_V = 1.1
CURRENT_THERMISTOR_NUMBER = 2 # Current Thermistor being simulated
TOTAL_NUM_THERMISTORS = 10

# Time delays
ARBITRARY_MUX_READ_WAIT_TIME_S = 0.01

@pytest.mark.parametrize("thermistor_number", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_collector(hil, thermistor_number):
    # Set up Outputs

    # Digital outputs controlling mux
    mux0 = hil.dout("firstCollTester", "D2")
    mux1 = hil.dout("firstCollTester", "D3")
    mux2 = hil.dout("firstCollTester", "D4")
    mux3 = hil.dout("firstCollTester", "D5")

    vIn = hil.ain("firstCollTester", "A1")

    # for idx in range(TOTAL_NUM_THERMISTORS):
      # Select a thermistor
    mux0.state = int(thermistor_number) & 0x1
    mux1.state = int(thermistor_number) & 0x2
    mux2.state = int(thermistor_number) & 0x4
    mux3.state = int(thermistor_number) & 0x8

    # Wait for mux to select proper signal
    time.sleep(ARBITRARY_MUX_READ_WAIT_TIME_S)

    expected_voltage = THERMISTOR_CONNECTED_VOLTAGE if thermistor_number == CURRENT_THERMISTOR_NUMBER else THERMISTOR_DISCONNECTED_VOLTAGE

    read_voltage = vIn.state

    print(f"Expected {expected_voltage}, real {read_voltage}", flush = True, )

    msg = f"Applying input to thermistor {CURRENT_THERMISTOR_NUMBER}. Reading value of thermistor {thermistor_number}. \
            Expected voltage: {expected_voltage}. Actual voltage: {read_voltage}."

    check.almost_equal(read_voltage, expected_voltage, abs=TOLERANCE_V if CURRENT_THERMISTOR_NUMBER == thermistor_number else DISCONNECTED_TOLERANC_V, rel=0.0, msg=msg)
