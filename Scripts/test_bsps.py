# Include car

# Define required signals

# Uses brake1 - emulate
# Uses brake2 - emulate
# Uses brake_stat - measure

class TestResult:
    """ Hold checks performed during a test and their pass/fail info """

    def __init__(self, _test_name):
        self.test_name = _test_name 
        self.cnt = 0
    
    def check(self, stat, name):
        self.cnt = self.cnt + 1



def test_brake_stat() -> TestResult:

    res = TestResult("test_brake_stat")
    print("Testing")

    err_msg = ""
    err = False

    car.brake1 = 0.0
    car.brake2 = 0.0

    wait(1)
    if car.brake_stat == True:
        err_msg = "Brake stat high when not braking."

    car.brake1 = 0.5
    car.brake2 = 0.5

    if car.brake_stat == False:
        err_msg = "Brake stat low when braking."

    # TODO: test if only one or the other goes high

    return res

# class A(object):

#     def m(self, p_value):
#          print p_value

#     @property
#     def p(self):
#         return self._p 

#     @p.setter
#     def p(self, value):
#         self._p = value
#         self.m(value)

# def __eq__(self, other):

def test_brake_fail():

    car.brake1 = 0.0
    car.brake2 = 0.0

    if car.brake_err == True:
        err_msg = "Brake err high when no error."
    
    car.brake1.short_gnd()

    if car.brake_err == False:
        err_msg = "Brake err low when brake 1 shorted to ground."

    car.brake1.float()


if __name__ == "__main__":
    # Configure car
    # Run script


