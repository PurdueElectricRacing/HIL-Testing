from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import utils
import time
from rules_constants import *
from vehicle_constants import *

def test_bspd(hil):
    # Begin the test
    hil.start_test(test_bspd.__name__)

    # Inputs
    d2 = hil.din("Test_HIL", "AI2")
    d3 = hil.din("Test_HIL", "AI3")
    d4 = hil.din("Test_HIL", "AI4")
    # d5 = hil.din("Test_HIL", "DI5")
    # d6 = hil.din("Test_HIL", "DI6")
    # d7 = hil.din("Test_HIL", "DI7")
    r1 = hil.dout("Test_HIL", "RLY1")
    r2 = hil.dout("Test_HIL", "RLY2")
    r3 = hil.dout("Test_HIL", "RLY3")
    r4 = hil.dout("Test_HIL", "RLY4")

    a1 = hil.dout("Test_HIL", "AI1")

    a1.state = 1


    r1.state = 1
    r2.state = 1
    r3.state = 1
    r4.state = 1

    r1.state = 0
    input("")
    r2.state = 0
    input("")
    r3.state = 0
    input("")
    r4.state = 0
    input("")

    for _ in range(100):

        #print(f"{d2.state}, {d3.state}, {d4.state}")
        for i in range(4):
            r1.state = not ((i % 4) == 0)
            r2.state = not ((i % 4) == 1)
            r3.state = not ((i % 4) == 2)
            r4.state = not ((i % 4) == 3)
            time.sleep(1)
        time.sleep(2)

    hil.end_test()

def test_dac(hil):
    hil.start_test(test_dac.__name__)
    
    dac1 = hil.aout("Test_HIL", "DAC1")
    dac2 = hil.aout("Test_HIL", "DAC2")

    dac1.state = 5.0
    dac2.state = 2.5
    input("")
    dac1.hiZ()
    dac2.hiZ()
    input("")
    dac1.state = 0.25
    dac2.state = 0.25
    input("")

    hil.end_test()

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_testing.json")
    hil.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")

    #test_bspd(hil)
    test_dac(hil)

    hil.shutdown()
