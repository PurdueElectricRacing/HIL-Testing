from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
from hil import HIL
import time

def test_brake_fail(hil):
    hil.start_test(test_brake_fail.__name__)

    fstp = hil.get_component("FrontESTOP")
    bots = hil.get_component("BOTS")
    btn  = hil.get_component("StartButton")
    do   = hil.get_component("DigiOut")
    di   = hil.get_component("DigiIn")
    ai   = hil.get_component("AnalogIn")

    for i in range(10):
        btn.state = 0
        time.sleep(0.01)
        btn.state = 1
        time.sleep(0.01)

    ct = 100

    a = time.perf_counter()
    for i in range(ct):
        do.state = 1
    b = time.perf_counter()
    for i in range(ct):
        l = di.state
    c = time.perf_counter()
    for i in range(ct):
        l = ai.state
    d = time.perf_counter()
    print(f"Avg Write time: {1000 * (b-a) / ct} ms")
    print(f"Avg Read time: {1000 * (c-b)/ct} ms")
    print(f"Avg Analog Read time: {1000 *(d-c)/ct} ms")

    print(f"State: {ai.state}, Set: {do.state}")
    do.state = 0
    print(f"State: {ai.state}, Set: {do.state}")

    fstp.state = 1
    bots.state = 1

    time.sleep(0.1)
    hil.check(False, "First")
    hil.check(True, "Second")

    fstp.state = 0

    time.sleep(0.1)

    bots.state = 0

    hil.end_test()


if __name__ == "__main__":
    hil = HIL()
    hil.load_config("config_test.json")
    test_brake_fail(hil)
    hil.shutdown()
