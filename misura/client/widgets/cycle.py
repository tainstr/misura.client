#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from .. import _
from presets import PresetManager
from aChooser import aChooser


class ThermalCycleChooser(PresetManager):

    def __init__(self, remObj, parent=None, context='Option', table=False):
        self.table = table
        PresetManager.__init__(self,  remObj, parent=parent, context='Option',
                               preset_handle='thermalCycle', 
                               save_handle='save_cycle', 
                               remove_handle='delete_cycle',
                               rename_handle='rename_cycle')

    def changed_option(self, *args, **kwargs):
        """Overload to introduce special item +Add at the end of the list."""
        # First calls standard redraw
        r = aChooser.changed_option(self, *args, **kwargs)
        if not self.table:
            return r
        # Then adds +Add special entry
        self.combo.blockSignals(True)
        if r:
            self.combo.addItem('+Add')
        if self.combo.count() <= 1:
            self.connect(
                self.combo, QtCore.SIGNAL('highlighted(int)'), self.add)
        else:
            self.disconnect(
                self.combo, QtCore.SIGNAL('highlighted(int)'), self.add)
        self.combo.blockSignals(False)

    def add(self, *args):
        name, ok = QtGui.QInputDialog.getText(self, _("Save as..."),
                                           _("Specify new preset name:"),
                                           QtGui.QLineEdit.Normal, 'default')

        if ok:
            self.remObj['curve'] = self.table.curve()
            r = self.remObj.call(self.save_handle, str(name))
            self.remObj['thermalCycle'] = str(name)
        else:
            self.combo.setCurrentIndex(self.prevIdx)
        self.changed_option()
