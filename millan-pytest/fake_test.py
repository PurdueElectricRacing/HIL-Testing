# import pytest

# @pytest.mark.section("FAKE 1")
# def test_fake():
# 	assert 1 == 1, "Power"
# 	assert 2 == 3, "Fire"
# 	assert 3 == 3, "Cooling"
# 	assert 4 == 5, "Brakes"
# 	assert 5 == 5, "Steering"
# 	assert 6 == 6, "Suspension"

# @pytest.mark.section("FAKE 2")
# def test_fake2():
# 	assert False
# 	assert True
# 	assert False
# 	assert True

# @pytest.mark.section("FAKE 3")
# def test_fake3():
# 	assert True
# 	assert True
# 	assert True
# 	assert True


import pytest
import pytest_check as check

@pytest.fixture(scope="session")
def param():
    param_instance = None
    yield param_instance
    

def test_fake(param):
    check.equal(1, 1, "Power")
    check.equal(2, 3, "Fire")
    check.equal(3, 3, "Cooling")
    check.equal(4, 5, "Brakes")
    check.equal(5, 5, "Steering")
    check.equal(6, 6, "Suspension")
    check.between_equal(5, 1, 10, "Speed")
    check.between_equal(11, 1, 10, "Speed 2")

def test_fake2(param):
    check.is_true(False, "A")
    check.is_true(True, "B")
    check.is_true(False, "C")
    check.is_true(True, "D")

def test_fake3(param):
    check.is_true(True, "True 1")
    check.is_true(True, "True 2")
    check.is_true(True, "True 3")
    check.is_true(True, "True 4")

