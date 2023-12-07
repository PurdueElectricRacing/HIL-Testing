from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import time

def test_dash_sdc_nodes(hil):
    hil.start_test(test_dash_sdc_nodes.__name__)

    # SDC Devices
    bots    = hil.get_component("BOTS")
    inertia = hil.get_component("InertiaSwitch")
    f_estop = hil.get_component("FrontESTOP")

    # SDC Measurement Taps
    f_estop = hil.get_component("FrontESTOP")

    bots.state    = 0
    inertia.state = 0
    f_estop.state = 0

    hil.end_test()

def test_dash_bspd(hil):
    hil.start_test(test_dash_bspd.__name__)

    brk1 = hil.get_component("Brake1")
    brk2 = hil.get_component("Brake2")
    brk_stat = hil.get_component("BrakeStat")
    brk_fail = hil.get_component("BrakeFail")

    brk1.set_percent(0)
    brk2.set_percent(0)

    """ Sweep to check brake status under braking """
    thresh = 0.5
    for a in range(0, 101, 20):
        p = a / 100.0
        brk1.set_percent(p)
        hil.check(brk_stat.state == (p > thresh), f"brk stat {p} brk 1")
        hil.check(brk_fail.state == 0, f"brk fail {p} brk")
    
    brk1.set_percent(0)
    for a in range(0, 101, 20):
        p = a / 100.0
        brk2.set_percent(p)
        hil.check(brk_stat.state == (p > thresh), f"brk stat {p} brk 2")
        hil.check(brk_fail.state == 0, f"brk fail {p} brk")

    """ Test brake fail """
    brk1.set_percent(0)
    brk2.set_percent(0)

    brk1.set_short_gnd()
    hil.check(brk_fail.state == 1, "brk fail brk1 short gnd")

    brk1.set_short_vcc()
    hil.check(brk_fail.state == 1, "brk fail brk1 short vcc")

    brk1.set_percent(0)

    brk2.set_short_gnd()
    hil.check(brk_fail.state == 1, "brk fail brk2 short gnd")

    brk2.set_short_vcc()
    hil.check(brk_fail.state == 1, "brk fail brk1 short vcc")

    brk1.set_percent(0)
    brk2.set_percent(0)
    hil.check(brk_fail.state == 0, "brk fail okay")
    
    hil.end_test()

if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_dash_bench.json")
    test_dash_bspd(hil)
    hil.shutdown()
