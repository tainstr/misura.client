#!/usr/bin/python
# -*- coding: utf-8 -*-

def arrange(parent_widget, instrument_name):
    arrange_functions = {
        'horizontal': arrange_dilatometer,
        'vertical': arrange_dilatometer,
        'flex': arrange_flex,
        'hsm': arrange_hsm
    }

    arrange_function = arrange_functions.get(instrument_name, arrange_default)
    arrange_function(parent_widget)



def arrange_default(parent_widget):
    parent_widget.tileSubWindows()

def arrange_dilatometer(parent_widget):
    visible_windows = visible_windows_of(parent_widget)
    number_of_visible_windows = len(visible_windows)
    has_cameras = reduce(lambda  acc, cur: acc or 'Camera' in cur.windowTitle(),
                         visible_windows,
                         False)

    if number_of_visible_windows  > 3 or not has_cameras:
        arrange_default(parent_widget)
        return

    parent_geometry = parent_widget.geometry()
    width = parent_geometry.width()
    heigth = parent_geometry.height()

    subwindows_width = width / 2
    subwindows_heigth = heigth / 2

    sizes = {
        'Camera (Left)': [0, 0, subwindows_width, subwindows_heigth],
        'Camera (Right)': [subwindows_width, 0, subwindows_width, subwindows_heigth],
        'Camera (Height)': [0, 0, subwindows_width, subwindows_heigth],
        'Camera (Base)': [subwindows_width, 0, subwindows_width, subwindows_heigth],
    }

    for win in visible_windows:
        size = sizes.get(win.windowTitle(), [0, subwindows_heigth, width, subwindows_heigth])
        win.setGeometry(*size)

def arrange_flex(parent_widget):
    parent_widget.tileSubWindows()

def arrange_hsm(parent_widget):
    parent_widget.tileSubWindows()





def visible_windows_of(widget):
    return [win for win in widget.subWindowList() if win.isVisible()]
