from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import utils
import time

def test_abox_orion(hil):
    # Begin the test
    hil.start_test(test_abox_orion.__name__)

    # Outputs
    # Options: daq_var, din, ain
    den = hil.dout("Abox", "Discharge Enable")         # Digital output on HIL tester
    cen = hil.dout("Abox", "Charge Enable")
    csafe = hil.dout("Abox", "Charger Safety")

    # Inputs
    # Options: daq_var, can_var, dout, aout
    lv_24  = hil.daq_var('PDU', 'lv_24_v_sense')        # DAQ variable on DUT MCU
    rx_pin = hil.mcu_pin('PDU', 'LV_BMS_RX_C')          # GPIO pin on DUT MCU
    test_1 = hil.can_var('PDU', 'pdu_test', 'test_1')   # CAN signal on DUT MCU

    # Check voltage within range
    hil.check_within(lv_24.state, 100, 5000, "Check LV Voltage")

    # Write digital pins to high
    den.state = 1
    cen.state = 1
    csafe.state = 1

    hil.check(test_1.state > 1, "Check test")

    print("")
    for _ in range (10):
        t= time.time()
        utils.clear_term_line()
        # Read MCU pin state
        s = rx_pin.state
        t = time.time() - t
        print(f"{s}, {t}")

        time.sleep(0.1)

    # End the test
    hil.end_test()

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_abox_bench.json")
    hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")
    # If you don't need CAN, comment out
    hil.init_can()

    test_abox_orion(hil)

    hil.shutdown()
