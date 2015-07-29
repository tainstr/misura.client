#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from .. import _
from presets import PresetManager


class ThermalCycleChooser(PresetManager):

    def __init__(self, remObj, parent=None, context='Option'):
        PresetManager.__init__(self,  remObj, parent=parent, context='Option',
                               preset_handle='thermalCycle', save_handle='save_cycle', remove_handle='delete_cycle')
