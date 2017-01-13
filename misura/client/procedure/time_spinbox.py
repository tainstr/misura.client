#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui

class TimeSpinBox(QtGui.QDoubleSpinBox):

    """SpinBox for time values editing (hours, minutes, seconds)"""

    def __init__(self, parent=None):
        QtGui.QDoubleSpinBox.__init__(self, parent)
        self.setRange(0, 10 ** 7)

    def textFromValue(self, s):
        logging.debug('%s %s', 'textFromValue', s)
        s = s * 60
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return '%i : %i : %.2f' % (h, m, s)

    def valueFromText(self, qstr):
        qstr = str(qstr).replace(' ', '')
        logging.debug('%s %s', 'valueFromText', qstr)
        if len(qstr) == 0:
            logging.debug('%s %s', 'valueFromText: empty', qstr)
            return 0.
        if ':' in qstr:
            h, m, s = qstr.split(':')
            r = int(h) * 3600 + int(m) * 60 + float(s)
        else:
            return float(qstr)
        return r / 60

    def setTime(self, t):
        logging.debug('%s %s', 'setTime', t)
        self.setValue(t)

    def setText(self, txt):
        logging.debug('%s %s', 'setText', txt)
        val = self.valueFromText(txt)
        self.setValue(val)

    def validate(self, inp, pos):
        logging.debug('%s %s %s', 'validate', inp, pos)
        try:
            self.valueFromText(inp)
            return (QtGui.QValidator.Acceptable, inp, pos)
        except:
            logging.debug('%s %s %s', 'invalid', inp, pos)
            return (QtGui.QValidator.Intermediate, inp, pos)