#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from aChooser import aChooser
from .. import _

from PyQt4 import QtGui


class PresetManager(aChooser):

    def __init__(self, remObj, parent=None, context='Option',
                 preset_handle='preset', save_handle='save', 
                 remove_handle='remove', 
                 rename_handle='rename'):

        aChooser.__init__(
            self, remObj, remObj, remObj.gete(preset_handle), parent=parent)
        self.preset_handle = preset_handle
        self.save_handle = save_handle
        self.remove_handle = remove_handle
        self.rename_handle = rename_handle
        # TODO: make a menu, add Rename, View, etc
        self.presets_button = QtGui.QPushButton('...')
        self.presets_button.setMaximumWidth(40)
        self.presets_button.setMinimumWidth(35)
        self.preset_menu = QtGui.QMenu()
        self.presets_button.setMenu(self.preset_menu)
        self.act_save = self.preset_menu.addAction(_('Save'), self.save_current)
        self.act_del = self.preset_menu.addAction(_('Delete'), self.remove)
        self.act_rename = self.preset_menu.addAction(_('Rename'), self.rename)

        self.lay.addWidget(self.presets_button)
        self.prevIdx = 0

    def add(self, *args):
        name, ok = QtGui.QInputDialog.getText(self, _("Save as..."),
                                           _("Specify new preset name:"),
                                           QtGui.QLineEdit.Normal, 'default')
        if ok:
            r = self.remObj.call(self.save_handle, str(name))
        else:
            self.combo.setCurrentIndex(self.prevIdx)
            r = False
        self.redraw()
        return r

    def remove(self):
        if self.user_is_not_sure("Delete \"%s\" preset?" % self.combo.currentText()):
            return

        i = self.combo.currentIndex()
        self.combo.setCurrentIndex(0)
        self.remObj.call(self.remove_handle,
                         self.adapt2srv(i))
        self.redraw()

    def save_current(self):
        if self.user_is_not_sure("Overwrite \"%s\" preset?" % self.combo.currentText()):
            return False

        r = self.remObj.call(self.save_handle,
                         self.adapt2srv(self.combo.currentIndex()))
        return r
        
    def rename(self):
        if self.current =='factory_default':
            return self.add()
        new_name, st = self.user_renames()
        if not st:
            return False
        self.remObj.call(self.rename_handle, str(new_name))
        self.redraw()
        self.current = False
        self.get()
        return True

    def user_renames(self):
        new_name, st = QtGui.QInputDialog.getText(self, _('Rename'), _('Enter the new name:'), text=self.current)
        return new_name, st

    def user_is_not_sure(self, message):
        answer = QtGui.QMessageBox.warning(
            self, "Are you sure?", message, QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)

        return answer == QtGui.QMessageBox.No

    def redraw(self, *args, **kwargs):
        """Overload per introdurre la voce speciale +Add al termine della lista"""
        # First calls standard redraw
        aChooser.redraw(self, *args, **kwargs)
        # Then adds +Add special entry
        self.combo.blockSignals(True)
        self.combo.addItem('+Add')
        if self.combo.count() <= 1:
            self.connect(
                self.combo, QtCore.SIGNAL('highlighted(int)'), self.add)
        else:
            self.disconnect(
                self.combo, QtCore.SIGNAL('highlighted(int)'), self.add)
        self.combo.blockSignals(False)

    def set(self, *args):
        """Overload per filtrare la voce speciale +Add"""
        if self.combo.currentText() == '+Add':
            self.add()
        else:
            self.prevIdx = self.combo.currentIndex()
            aChooser.set(self, *args)
