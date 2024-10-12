# import pytest

# def test_fake():
# 	assert 1 == 1, "Power"
# 	assert 2 == 3, "Fire"
# 	assert 3 == 3, "Cooling"
# 	assert 4 == 5, "Brakes"
# 	assert 5 == 5, "Steering"
# 	assert 6 == 6, "Suspension"

# def test_fake2():
# 	assert False
# 	assert True
# 	assert False
# 	assert True

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
    

def log_function_start_end(func):
    def wrapper_function(*args, **kwargs): 
        print(f"START: {func.__name__}")
        func(*args,  **kwargs) 
        print(f"END:   {func.__name__}")
    return wrapper_function 


@log_function_start_end
def do_something():
    print("Doing something")

@log_function_start_end
def do_something_with_args(arg1, arg2):
    print(f"Arg1: {arg1}, Arg2: {arg2}")

def test_fake(param):
    check.equal(1, 1, "Power")
    do_something()
    check.equal(2, 3, "Fire")
    check.equal(3, 3, "Cooling")
    do_something_with_args(1, 2)
    check.equal(4, 5, "Brakes")
    do_something()
    check.equal(5, 5, "Steering")
    check.equal(6, 6, "Suspension")
    do_something_with_args(3, 4)
    check.between_equal(5, 1, 10, "Speed")
    check.between_equal(11, 1, 10, "Speed 2")

def test_fake2(param):
    check.is_true(False, "A")
    check.is_true(True, "B")
    check.is_true(False, "C")
    do_something_with_args(5, 6)
    check.is_true(True, "D")

def test_fake3(param):
    check.is_true(True, "True 1")
    check.is_true(True, "True 2")
    check.is_true(True, "True 3")
    do_something_with_args(7, 8)
    check.is_true(True, "True 4")

def test_fake4(param):
    check.almost_equal(0.2, 0.23, abs=0.1, rel=0.0,  msg="Almost 1")

