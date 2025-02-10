# NOTE: each constant in this file shall reference a rule

# IMD
R_IMD_RESISTANCE_RATIO = 500 # EV.7.6.3 Ohms / Volt
R_IMD_MAX_TRIP_TIME_S = 30.0 # IN.4.4.2
R_IMD_TRIP_TEST_RESISTANCE_PERCENT = 0.5 # IN.4.4.2 50% of response value

# BSPD EV.7.7
R_BSPD_MAX_TRIP_TIME_S = 0.5  # EV.7.7.2
R_BSPD_POWER_THRESH_W  = 5000 # EV.7.7.2

# Precharge and Discharge EV.5.6
R_PCHG_V_BAT_THRESH = 0.90 # EV.5.6.1.a

# TSAL EV.5.9
R_TSAL_HV_V = 60.0 # T.9.1.1
