#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.csutil import next_point, find_nearest_val

colTIME = 0
colTEMP = 1
colRATE = 2
colDUR = 3
colMODE = 4

def is_row_an_event(row_entry):
        temp_value = row_entry[colTEMP]
        return isinstance(temp_value, basestring) and temp_value.startswith('>')

def previous_not_event_row_index(current_index, rows):
    index_to_take = current_index - 1
    while(is_row_an_event(rows[index_to_take])):
        index_to_take -= 1
    return index_to_take


def find_max_heating_rate(T, rateLimit, maxHeatingRate=80):
    """Find maximum heating rate for temperature `T` using `rateLimit` table and a default of `maxHeatingRate`"""
    if not len(rateLimit):
        return maxHeatingRate
    i = find_nearest_val(rateLimit, T, lambda i: rateLimit[i][0])
    rT, rR = rateLimit[i]
    # If returning a lower T entry, take next limit
    if rT < T:
        if len(rateLimit) > i + 1:
            rT, maxHeatingRate = rateLimit[i + 1]
    elif rT >= T:
        maxHeatingRate = rR
    return maxHeatingRate
    
    
def update_row(rows, row_index, mode, time_correction=0, maxRate=80, rateLimit=[]):
    """Adjust `row_index` of `rows` model, following ajusting `mode` rules 
    and enforcing rate limit `maxRate` and rate limiting curve `rateLimit`.
    Returns the adjusted row entry and the time correction to be applied to all subsequent entries."""
    current_row = rows[row_index]
    if isinstance(current_row[colTEMP], basestring):
        current_row[0] += time_correction
        return current_row, time_correction
    
    # Apply time_correction from previous rows
    current_row[0] += time_correction
    
    
    # Previous point: search backwards
    prev_row_index, prev_row = next_point(rows, row_index - 1, -1)
    
    if prev_row is False:
        return current_row, time_correction

    time, temperature, heating_rate, duration = current_row
    prev_time, prev_temperature, prev_heating_rate, prev_duration = prev_row
    
    if temperature != 0:
        maxRate = find_max_heating_rate(temperature, rateLimit, maxRate)

    if mode == 'points':  # time/temperature (Time)
        duration = (time - prev_time)
        if duration == 0:
            heating_rate = 0
        else:
            heating_rate = (temperature - prev_temperature) / duration
            
    elif mode == 'ramp':  # rate/temperature (Rate)
        if heating_rate != 0:
            duration = (temperature - prev_temperature) / heating_rate
        else:
            index_to_take = previous_not_event_row_index(row_index, rows)
            temperature = rows[index_to_take][colTEMP]
        time = prev_time + duration
        
    elif mode == 'dwell':  # duration/temperature (Duration)
        if duration == 0:
            heating_rate = 0
        else:
            heating_rate = (temperature - prev_temperature) / duration
        time = prev_time + duration

    if duration < 0 or time < prev_time:
        ret = [prev_time + 1, prev_temperature, 0, 1]
    else:
        ret = [time, temperature, heating_rate, duration]
        
    # Limit heating rate
    if ret[2] > maxRate:
        delay = ret[3] * ((ret[2] / maxRate) - 1) 
        print temperature, prev_temperature, ret[3], ret[2], maxRate
        # Fix heating rate
        ret[2] = maxRate
        # Increase time target
        ret[0] += delay
        # Increase duration to accommodate delay
        ret[3] += delay
        # Increase time_correction so next point is delayed according to the lower heating rate
        time_correction += delay
        
    
    return ret, time_correction
    
