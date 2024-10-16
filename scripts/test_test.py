from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil.hil import HIL
# import hil.utils as utils
import time
import can
from rules_constants import *
from vehicle_constants import *

import pytest_check as check
import pytest


# ---------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def hil():
    hil_instance = HIL()

    # hil.load_config("config_testing.json")
    hil_instance.load_pin_map("per_24_net_map.csv", "stm32f407_pin_map.csv")
    
    # hil_instance.init_can()
    
    yield hil_instance
    
    hil_instance.shutdown() 
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_bspd(hil):
    # Begin the test
    # hil.start_test(test_bspd.__name__)

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

    check.is_true(True, "TODO")

    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_dac(hil):
    # hil.start_test(test_dac.__name__)
    
    dac1 = hil.aout("Test_HIL", "DAC1")
    dac2 = hil.aout("Test_HIL", "DAC2")

    dac1.state = 2.5
    dac2.state = 5.0
    input("5, 2")
    dac1.hiZ()
    dac2.hiZ()
    input("hi-z")
    dac1.state = 0.25
    dac2.state = 0.25
    input(".25")

    check.is_true(True, "TODO")

    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_pot(hil):

    pot1 = hil.pot("Test_HIL", "POT1")
    pot2 = hil.pot("Test_HIL", "POT2")
    
    print("initial")
    input(" - ")
    print("0.5, 1")
    pot1.state = 0.5
    pot2.state = 0.5
    input(" - ")

    print("1, 0.5")
    pot1.state = 1.0
    pot2.state = 1.0
    input(" - ")

    print("0, 0")
    pot1.state = 0.0
    pot2.state = 0.0
    input(" - ")

    for i in range(1000):
        pot1.state = 0.25
        pot2.state = 0.25
        time.sleep(0.01)
        pot1.state = 0.75
        pot2.state = 0.75
        time.sleep(0.01)

    pot1.state = 0.5
    pot2.state = 0.5
    input("-------")

    check.is_true(True, "TODO")
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_mcu_pin(hil):
    # hil.start_test(test_mcu_pin.__name__)

    brk_stat_tap = hil.mcu_pin("Dashboard", "BRK_STAT_TAP")

    delta_avg = 0
    delta_cnt = 0
    for i in range(100):
        t_start = time.time()
        #time.sleep(0.01)
        print(brk_stat_tap.state)
        t_start = time.time() - t_start
        delta_avg += t_start
        delta_cnt = delta_cnt + 1
    
    print(f"Average: {delta_avg/delta_cnt}")

    check.is_true(True, "TODO")
    
    # hil.end_test()
# ---------------------------------------------------------------------------- #


# ---------------------------------------------------------------------------- #
def test_daq(hil):
    # hil.start_test(test_daq.__name__)

    counter = 0
    start_time = time.time()

    LOOP_TIME_S = 0.001

    # while(1):
    #     time.sleep(3)

    print("Sending")

    #while (time.time() - start_time < 15*60):
    while (counter < 4000):
        last_tx = time.perf_counter()
        #msg = can.Message(arbitration_id=0x14000072, data=counter.to_bytes(4, 'little'))
        #msg = can.Message(arbitration_id=0x80080c4, data=counter.to_bytes(4, 'little'))
        msg = can.Message(arbitration_id=0x400193e, data=counter.to_bytes(8, 'little'))
        #print(msg)
        hil.can_bus.sendMsg(msg)
        counter = counter + 1
        delta = LOOP_TIME_S - (time.perf_counter() - last_tx)
        if (delta < 0): delta = 0
        time.sleep(delta)

    check.is_true(True, "TODO")

    print("Done")
    print(f"Last count sent: {counter - 1}")
# ---------------------------------------------------------------------------- #