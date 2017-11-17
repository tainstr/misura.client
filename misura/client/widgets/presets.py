#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.client.widgets.active import *
from aChooser import aChooser
from .. import _

from PyQt4 import QtGui


class PresetManager(aChooser):
    
    saved = QtCore.pyqtSignal(str)
    savedAs = QtCore.pyqtSignal(str)
    renamed = QtCore.pyqtSignal(str, str)
    removed = QtCore.pyqtSignal(str)
    

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
        
    def redraw(self):
        super(PresetManager, self).redraw()
        # TODO: make a menu, add Rename, View, etc
        self.presets_button = QtGui.QPushButton('...')
        self.presets_button.setMaximumWidth(40)
        self.presets_button.setMinimumWidth(35)
        self.preset_menu = QtGui.QMenu()
        self.presets_button.setMenu(self.preset_menu)
        self.act_save = self.preset_menu.addAction(_('Save'), self.save_current)
        self.act_saveAs = self.preset_menu.addAction(_('Save as...'), self.save_as)
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
        self.changed_option()
        return r

    def remove(self):
        if self.user_is_not_sure("Delete \"%s\" preset?" % self.combo.currentText()):
            return

        i = self.combo.currentIndex()
        self.combo.setCurrentIndex(0)
        name= self.adapt2srv(i)
        self.remObj.call(self.remove_handle, name)
        self.changed_option()
        self.removed.emit(str(name))

    def save_current(self):
        if self.user_is_not_sure("Overwrite \"%s\" preset?" % self.combo.currentText()):
            return False
        name = self.adapt2srv(self.combo.currentIndex())
        r = self.remObj.call(self.save_handle, name)
        self.saved.emit(str(name))
        return r
    
    def save_as(self):
        new_name, st = self.user_renames(title='Choose a new name')
        if not st:
            return False
        if new_name in self.prop['options']:
            if self.user_is_not_sure("Overwrite \"%s\" preset?" % new_name):
                return False
        r = self.remObj.call(self.save_handle, new_name)
        self.remObj[self.handle] = new_name
        self.changed_option()
        self.savedAs.emit(str(new_name))
        return r
        
        
    def rename(self):
        if self.current =='factory_default':
            return self.add()
        new_name, st = self.user_renames()
        if not st:
            return False
        self.remObj.call(self.rename_handle, str(new_name))
        self.changed_option()
        self.current = False
        self.get()
        self.renamed.emit(self.current, str(new_name))
        return True

    def user_renames(self, title='Rename'):
        new_name, st = QtGui.QInputDialog.getText(self, _(title), _('Enter the new name:'), text=self.current)
        return new_name, st

    def user_is_not_sure(self, message):
        answer = QtGui.QMessageBox.warning(
            self, _("Are you sure?"), message, QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)

        return answer == QtGui.QMessageBox.No

    def changed_option(self, *args, **kwargs):
        """Append +Add at the end of choices"""
        # First calls standard redraw
        r = aChooser.changed_option(self, *args, **kwargs)
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

    def set(self, *args):
        """Overload to filter special entry +Add"""
        if self.combo.currentText() == '+Add':
            self.add()
        else:
            self.prevIdx = self.combo.currentIndex()
            aChooser.set(self, *args)
