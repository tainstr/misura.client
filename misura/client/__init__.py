#!/usr/bin/python
import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
	sip.setapi(name, API_VERSION)
from parameters import determine_path

from PyQt4 import QtCore



def _(text, disambiguation=None, context='misura'):
	"""Veusz-based translatable messages tagging."""
	return QtCore.QCoreApplication.translate(context, text,
                                     disambiguation=disambiguation)