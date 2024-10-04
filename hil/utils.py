import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import sys
import time
import numpy as np

def initGlobals():
    global signals
    signals = {}
    
    global plot_x_range_sec
    plot_x_range_sec = 10
    
    global events
    events = []
    
    global b_str
    b_str = "Main"
    
    global data_types
    data_types = {
        'uint8_t':  np.dtype('<u1'),
        'uint16_t': np.dtype('<u2'),
        'uint32_t': np.dtype('<u4'),
        'uint64_t': np.dtype('<u8'),
        'int8_t':   np.dtype('<i1'),
        'int16_t':  np.dtype('<i2'),
        'int32_t':  np.dtype('<i4'),
        'int64_t':  np.dtype('<i8'),
        'float':    np.dtype('<f4') # 32 bit
    }
    
    global data_type_length
    data_type_length = {
        'uint8_t':  8,
        'uint16_t': 16,
        'uint32_t': 32,
        'uint64_t': 64,
        'int8_t':   8,
        'int16_t':  16,
        'int32_t':  32,
        'int64_t':  64,
        'float':    32
    }
    
    global debug_mode
    debug_mode = True
    
    global daqProt
    daqProt = None
    
    global hilProt
    hilProt = None

# Logging helper functions
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_error(phrase):
    print(f"{bcolors.FAIL}ERROR: {phrase}{bcolors.ENDC}")

def log_warning(phrase):
    log(f"{bcolors.WARNING}WARNING: {phrase}{bcolors.ENDC}")

def log_success(phrase):
    log(f"{bcolors.OKGREEN}{phrase}{bcolors.ENDC}")

def log(phrase):
    global debug_mode
    if debug_mode: print(phrase)

def load_json_config(config_path, schema_path=None):
    """ loads config from json and validates with schema """
    config = json.load(open(config_path))
    if (schema_path == None): return config # Bypass schema check
    schema = json.load(open(schema_path))

    # compare with schema
    try:
        validate(config, schema)
    except ValidationError as e:
        log_error("Invalid JSON!")
        print(e)
        sys.exit(1)

    return config

def clearDictItems(dictionary:dict):
    """Recursively calls clear on items in multidimensional dict"""
    for key, value in dictionary.items():
        if type(value) is dict:
            clearDictItems(value)
        else:
            value.clear()

def clear_term_line():
    sys.stdout.write('\033[F\033[K')
    #sys.stdout.flush()

# Credit: https://stackoverflow.com/questions/1133857/how-accurate-is-pythons-time-sleep/76554895#76554895
def high_precision_sleep(duration):
    start_time = time.perf_counter()
    while True:
        elapsed_time = time.perf_counter() - start_time
        remaining_time = duration - elapsed_time
        if remaining_time <= 0:
            break
        if remaining_time > 0.02:  # Sleep for 5ms if remaining time is greater
            time.sleep(max(remaining_time/2, 0.0001))  # Sleep for the remaining time or minimum sleep interval
        else:
            pass


class VoltageDivider():
    def __init__(self, r1, r2):
        self.r1 = float(r1)
        self.r2 = float(r2)
        self.ratio = (self.r2 / (self.r1 + self.r2))

    def div(self, input):
        return input * self.ratio
    
    def reverse(self, output):
        return output / self.ratio


def measure_trip_time(trip_sig, timeout, is_falling=False):
    t_start = time.time()
    while(trip_sig.state == is_falling):
        time.sleep(0.015)
        if (t_start + timeout <= time.time()):
            log_warning(f"Trip for {trip_sig.name} timed out")
            return timeout
    t_delt = time.time() - t_start
    print(f"Trip time for {trip_sig.name} = {t_delt}s")
    return t_delt


def measure_trip_thresh(thresh_sig, start, stop, step, period_s, trip_sig, is_falling=False):
    gain = 1000
    thresh = start
    _start = int(start * gain)
    _stop = int(stop * gain)
    _step = int(step * gain)
    thresh_sig.state = start
    tripped = False
    print(f"Start: {_start} Stop: {_stop} Step: {_step} Gain: {gain}")
    for v in range(_start, _stop+_step, _step):
        thresh_sig.state = v / gain
        time.sleep(period_s)
        if (trip_sig.state == (not is_falling)):
            thresh = v / gain
            tripped = True
            break
    if (not tripped):
        log_warning(f"{trip_sig.name} did not trip at stop of {stop}.")
        return stop
    else:
        return thresh
    