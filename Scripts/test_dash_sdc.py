import time

def test_dash_sdc(HIL) -> TestResult:
    #HIL.check_requirements(["FrontESTOP", "BOTS"]) # TODO: check in emulation mode as well, can't be like measure or sometihing
    
    # Get required devices
    fstp = HIL.get("FrontESTOP")
    bots = HIL.get("BOTS")

    fstp.state = 1
    bots.state = 1

    time.sleep(2)

    fstp.state = 0

    time.sleep(2)

    bots.state = 1

