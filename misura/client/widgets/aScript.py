#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from misura.client.widgets.active import *
from .. import _
import highlighter


class ScriptEditor(QtGui.QDialog):

    """A simple script editing dialog"""

    def __init__(self, active):
        QtGui.QDialog.__init__(self, active)
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)

        self.active = active
        self.setWindowTitle(_("Script Editor"))
        self.menu = QtGui.QMenuBar(self)
        self.menu.setMinimumHeight(25)
        self.menu.addAction(_('Validate'), self.validate)
        act = self.menu.addAction(_('Save'), self.save)
        if self.active.readonly:
            act.setEnabled(False)
        self.area = QtGui.QTextEdit()
        self.area.setReadOnly(False)
        self.area.setPlainText(self.active.adapt2gui(self.active.current))
        highlighter.PygmentsHighlighter(self.area)

        self.lay.addWidget(self.menu)
        self.lay.addWidget(self.area)

        self.connect(self, QtCore.SIGNAL('accepted()'), self.save)

    @property
    def current(self):
        """Returns the last value got from remote"""
        return self.area.toPlainText()

    def validate(self):
        """Just validate the script, without saving it remotely. Highlight errors."""
        val = unicode(self.current)
        err, line, col = self.active.remObj.validate_script_text(val)
        if line < 0:
            return True
        msg = "%s\n%s\n%s %i, col: %i" % (_("Validation failed for the following reason:"),
                                          err, _("Found at line:"), line, col)
        QtGui.QMessageBox.warning(self, _("Validation error"), msg)
        pos = 0
        line -= 1
        for i, ent in enumerate(val.splitlines()):
            if i == line:
                pos += col
                break
            pos += len(ent) + 1
        cur = self.area.textCursor()
        cur.setPosition(pos)
        self.area.setTextCursor(cur)
        return False

    def save(self):
        """Saves the current version of the script remotely."""
        if self.active.readonly:
            logging.error('Script is readonly. Cannot save.', self.active.handle)
            return False
        self.active.set(self.current)
        self.area.setPlainText(self.active.adapt2gui(self.active.current))
        return True


class aScript(ActiveWidget):

    """Elemento grafico per una proprietà stringa di testo"""

    def redraw(self):
        super(aScript, self).redraw()
        txt = _('View') if self.readonly else _('Edit')
        self.button = QtGui.QPushButton(txt, self)
        self.connect(self.button, QtCore.SIGNAL('clicked()'), self.show_editor)
        self.lay.addWidget(self.button)
        self.set_enabled()

    def show_editor(self):
        e = ScriptEditor(self)
        e.exec_()

    def adapt(self, val):
        """I valori in ingresso ed in uscita devono sempre essere unicode"""
        return unicode(val)

    def adapt2gui(self, val):
        return unicode(val)

    def emitOptional(self):
        self.emit(QtCore.SIGNAL('textEdited(QString)'), self.current)
