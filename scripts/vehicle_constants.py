from os import sys, path
# adds "./HIL-Testing" to the path, basically making it so these scripts were run one folder level higher
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import hil.utils as utils

# NOTE: each value in this file should be a physical or electrical property of the vehicle

# Accumulator Constants
ACCUM_MAX_V  = 317.3
ACCUM_MIN_V  = 190.0 
ACCUM_NOM_V  = 273.6
ACCUM_FUSE_A = 140.0

ABOX_DHAB_CH1_DIV = utils.VoltageDivider(1000, 2000)

# IMD Constants
IMD_MEASURE_TIME_S = 20.0
IMD_STARTUP_TIME_S = 2.0

# AMS Constants
AMS_MAX_TRIP_DELAY_S = 3.0

# Precharge Constants   
PCHG_COMPLETE_DELAY_S = 0.5

# Tiffomy Constants
TIFF_LV_MAX = 5.0
TIFF_LV_MIN = -5.0
TIFF_SCALE  = 100.0
def tiff_hv_to_lv(hv_voltage):
    return min(max(hv_voltage / TIFF_SCALE, TIFF_LV_MIN), TIFF_LV_MAX)
def tiff_lv_to_hv(lv_voltage):
    return lv_voltage * TIFF_SCALE

# DHAB S124 Current Sensor
DHAB_S124_MAX_OUT_V = 4.8
DHAB_S124_MIN_OUT_V = 0.2
DHAB_S124_OFFSET_V  = 2.5
DHAB_S124_CH1_SENSITIVITY = 26.7 / 1000.0 # V / A
DHAB_S124_CH2_SENSITIVITY = 4.9  / 1000.0 # V / A
DHAB_S124_CH1_MAX_A = 75.0
DHAB_S124_CH1_MIN_A = -75.0
DHAB_S124_CH2_MAX_A = 500.0
DHAB_S124_CH2_MIN_A = -500.0

def dhab_ch1_v_to_a(signal_v):
    return (signal_v - DHAB_S124_OFFSET_V) / DHAB_S124_CH1_SENSITIVITY

def dhab_ch2_v_to_a(signal_v):
    return (signal_v - DHAB_S124_OFFSET_V) / DHAB_S124_CH2_SENSITIVITY

def dhab_ch1_a_to_v(amps):
    amps = min(max(amps, DHAB_S124_CH1_MIN_A), DHAB_S124_CH1_MAX_A)
    return (amps * DHAB_S124_CH1_SENSITIVITY) + DHAB_S124_OFFSET_V

def dhab_ch2_a_to_v(amps):
    amps = min(max(amps, DHAB_S124_CH2_MIN_A), DHAB_S124_CH2_MAX_A)
    return (amps * DHAB_S124_CH2_SENSITIVITY) + DHAB_S124_OFFSET_V

def dhab_v_valid(signal_v):
    return (DHAB_S124_MIN_OUT_V <= signal_v <= DHAB_S124_MAX_OUT_V)

# Brake Pressure Transducer
BRK_MAX_OUT_V  = 4.8
BRK_MIN_OUT_V  = 0.2
BRK_1_REST_V   = 0.5 # Resting line voltage of brake 1
BRK_2_REST_V   = 0.5 # Resting line voltage of brake 2
BRK_1_DIV = utils.VoltageDivider(5600, 10000)
BRK_2_DIV = utils.VoltageDivider(5600, 10000)
BRK_1_THRESH_V = 0.68 # Threshold that is considered braking for brake 1
BRK_2_THRESH_V = 0.68 # Threshold that is considered braking for brake 2

# Throttle
THTL_MAX_P = 0.9 # Maximum pedal press percent
THTL_MIN_P = 0.1 # Minimum pedal press percent
THTL_THRESH = 0.2 # Throttle pressed percent
