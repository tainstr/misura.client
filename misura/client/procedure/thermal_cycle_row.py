#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.csutil import next_point

colTIME = 0
colTEMP = 1
colRATE = 2
colDUR = 3
colMODE = 4

def is_row_an_event(row):
        temp_value = row[colTEMP]
        return isinstance(temp_value, basestring) and temp_value.startswith('>')

def previous_not_event_row_index(current_index, rows):
    index_to_take = current_index - 1
    while(is_row_an_event(rows[index_to_take])):
        index_to_take -= 1
    return index_to_take


class ThermalCycleRow():
    def update_row(self, rows, row_index, mode):
        current_row = rows[row_index]
        if isinstance(current_row[colTEMP], basestring):
            return current_row

        next_row_index, next_row = next_point(rows, row_index - 1, -1)

        if next_row is False:
            return current_row

        time, temperature, heating_rate, duration = current_row
        next_time, next_temperature, next_heating_rate, next_duration = next_row

        if mode == 'points':  # time/temperature (Time)
            duration = (time - next_time)
            if duration == 0:
                heating_rate = 0
            else:
                heating_rate = (temperature - next_temperature) / duration
        elif mode == 'ramp':  # rate/temperature (Rate)
            if heating_rate != 0:
                duration = (temperature - next_temperature) / heating_rate
            else:
                index_to_take = previous_not_event_row_index(row_index, rows)
                temperature = rows[index_to_take][colTEMP]
            time = next_time + duration
        elif mode == 'dwell':  # duration/temperature (Duration)
            if duration == 0:
                heating_rate = 0
            else:
                heating_rate = (temperature - next_temperature) / duration
            time = next_time + duration

        if duration < 0 or time < next_time:
            return [next_time + 1, next_temperature, 0, 1]
        else:
            return [time, temperature, heating_rate, duration]

