import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import sys
import time

def initGlobals():
    global debug_mode
    debug_mode = True

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
    """ recursively calls clear on items in multidimensional dict"""
    for key, value in dictionary.items():
        if type(value) is dict:
            clearDictItems(value)
        else:
            value.clear()

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
