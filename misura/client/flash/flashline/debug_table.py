#!/usr/bin/python
# -*- coding: utf-8 -*-
"""FlashLine Debug Table parser (.d_t)"""
import collections
import numpy as np
from misura.canon.csutil import decode_datetime
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

f_time = 0  # Absolute time in seconds
f_log = 1   # Event codes
f_Tk = 2    # Furnace temperature
f_Ts = 3    # Sample temperature
f_P = 4     # Power Percentage of Fuji Controller ( *Note-1 )
f_S = 5     # Setpoint
f_goal_setpoint = 6  # Goal Setpoint (Furnace Fuji Setpoint)
f_laser_voltage =7  # Flash voltage readback ( *Note-1 )
f_laser_setpoint = 8 # Flash voltage segment setpoint
f_laser_adj_setpoint = 9 # Flash adjusted setpoint
f_carousel = 10 # Carousel position
f_misc = 11

# Ditital readbacks: 1=On, 0=Off
b_furnace_enable = 12
b_system_enable = 13
b_water_sense = 14
b_thermal_switch = 15

c_time_human = 16
# Ditital readbacks: 1=On, 0=Off
b_actuator_pressure = 17
b_gas_pressure = 18
b_detector_in_place = 19
b_closed = 20

f_signal = 21   # The value of the detector channel. Usually from the HSO procedure. ( *Note-1 )
f_offset = 22   # The DA voltage that was used to offset the detector. ( *Note-1 )
f_fuji_Tk = 23  # Fuji 1: This is the Furnace Fuji Controller.
f_fuji_Ts = 24  # Fuji 2: This is the Sample Fuji Controller.  If there is no sample Fuji Controller this value should be 0.0.
f_fuji_setpoint_goal = 25        # Goal:  This value is not used at this time.  It may be used in adaptation.
f_fuji_setpoint_display = 26     # Control:  This may be the Setpoint the Fuji will display.  But this may be used in conjunction with the SVO.
f_fuji_setpoint_offset = 27     # This is the setpoint Offset sent to the Fuji.
f_fuji_power = 28   # Out1:  This is the power percentage read back from the Fuji.  A duplicate. ( *Note-1 )
f_vacuum = 29   # A reading from the vacuum gauge if it is available.

# MCC-Orig readouts
# 1: Sys 2: Window 3: OT 4: Wand 5: Alm-NA 6: Water 7: MI 8: NA
foo_mcc = 30 # MCC-Orig: label
b_mcc_sys = 31      # System enable
b_mcc_window = 32   # 
b_mcc_over_temp = 33
b_mcc_wand = 34
b_mcc_alarm = 35
b_mcc_water = 36
b_mcc_mi = 37
b_mcc_na8 = 38

#MCC  2nd A: TS  B: Act Pressure C: Shutter D: Detector E: Head Closed F: NA G: NA H: Fan
foo_mcc2 = 39 # MCC: label
b_mcc_ts = 40
b_mcc_act_pressure = 41
b_mcc_shutter = 42
b_mcc_detector = 43
b_mcc_head_closed = 44
b_mcc_naF = 45
b_mcc_naG = 46
b_mcc_fan = 47

required_columns = 44

# TM, Undefined, Code
debug_columns = collections.OrderedDict()
for var, val in locals().copy().items():
    if var[:2] in ('f_','b_','c_'):
        debug_columns[var] = val
        
        
debug_codes = {
    'A': ' At temperature:  sample temperature is "close" to setpoint temperature, this difference can be from 5 to 100 degrees',
    'a': ' Over temperature abort',
    'B': ' Baseline type 10',
    'b': ' Flash modules error, no flash or no reading of signal, carousel mover error',
    'C': ' Coarse equilibrium',
    'd': ' Furnace adaptation, or too many bad shots',
    'E': ' Equilibrium',
    'F': ' Finished',
    'g': ' Pyrometer reading error:  older system',
    'H': ' Heating',
    'I': ' Furnace Enable (Manual Interlock) failure',
    'J': ' DAQ MCC Read Error',
    'j': ' Hardware error ; laser interlocks, furnace head up,  general flash safety error',
    'K': ' Unfreeze temperature control',
    'k': ' Freeze temperature control',
    'L': ' Error segment heating too long',
    'l': ' Paused for LN2 but waiter too long',
    'M': ' Switch detector on multiple channels',
    'n': ' Next segment by user',
    'O': ' Filter 1 In    ( 10-25-2013 V 15.0 )',
    'o': ' Filter 2 Out',
    'R': ' Filter 2 In',
    'r': ' Filter 2 Out',
    'S': ' Start of test',
    's': ' Start of test ( in sequence of starting )',
    'T': ' Testing for segment start',
    't': ' Tune segments',
    'u': ' User stopped',
    'v': ' Start of HSO to BaseLine drift wait  ( 10-24-2013 )',
    'W': ' Water switch off device error',
    'w': ' No response from flash module or waiting in special cp test',
    'x': ' Error reading temperature controllers or Laser Pump',
    'y': ' Wait longer for HSO to BaseLine drift wait  ( 10-24-2013 )',
    'Z': ' Testing status error',
    'z': ' Device error',
    '[': ' This code will be for samples > 6',
    '7': ' Baseline type 10',
    '8': ' Stop Hardware',
    '{': ' Read laser voltage before shot',
    '`': ' Incremental Charge Capacitor start',
    '<': ' Incremental – Partial Capacitor Charge',
    '?': ' Incremental – Partial Capacitor Charge Check ',
    '!': ' Incremental – Partial Capacitor Charge OK ',
    '*': ' Start fire flash cycle',
    '-': ' End flash fire cycle',
    '#': ' Diagnostic Mode',
    '>': ' Diagnostic read temperature controller',
    '^': ' DTL  error',
    '~': ' Device error',
    '(': ' Furnace Enable (Manual interlock) off during test',
    ')': ' Furnace Enable (Manual interlock) off during test after retry read',
}

for i in range(1, 7):
    debug_codes[str(i)] = 'Moving carousel to ' + str(i)

    
def debug_table(filename):
    """Import a .d_t debug table"""
    data = open(filename, 'r').read()
    table = []
    # Convert all multi-spaces to single-spaces separators
    while '  ' in data:
        data = data.replace('  ', ' ')
    data = data.replace('\r\n', '\n').split('\n')
    zerodatetime = False
    # Append uniform 59-length lines
    for i, line in enumerate(data):
        # Parse the date info
        if line.startswith('Version='):
            #Wed Nov 11 16:45:47 2015
            zerodatetime = decode_datetime(line[-24:].strip(), 
                format='%a %b %d %H:%M:%S %Y')
            continue
        line = line[:-1]
        line = line.split(' ')
        n = len(line)
        if n < required_columns:
            logging.debug('skipping', i, n, required_columns)
            continue
        # No log code found
        if '.' in line[f_log]:
            line.insert(f_log, 'NoLog')
        elif line[f_log] in debug_codes:
            line[f_log] = debug_codes[line[f_log]]
    
        table.append(np.array(line))
    
    table0 = np.array(table).transpose()
    return table0, zerodatetime
    
def fake_debug_table(t=10000, z=0):
    d = np.zeros((required_columns, t))
    d[f_time] += np.linspace(z, z+t, t)
    d[f_goal_setpoint] += 25
    #d[f_P] = 0
    d[f_Ts] += 25
    
    return d
    
    
    
    
    
    