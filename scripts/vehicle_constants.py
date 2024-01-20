from os import sys, path 
sys.path.append(path.join(path.dirname(path.dirname(path.abspath(__file__))), 'hil'))
import utils

# NOTE: each value in this file should be a physical or electrical property of the vehicle

# Accumulator Constants
ACCUM_MAX_V     = 317.3
ACCUM_NOMINAL_V = 273.6
ACCUM_FUSE_A    = 140.0

ABOX_DHAB_CH1_DIV = utils.VoltageDivider(1000, 2000)

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