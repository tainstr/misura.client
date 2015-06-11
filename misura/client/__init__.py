#!/usr/bin/python
# -*- coding: utf-8 -*-
import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
	sip.setapi(name, API_VERSION)
from parameters import determine_path

from PyQt4 import QtCore
import network
import logging

logging.basicConfig(level=logging.DEBUG)

def _(text, disambiguation=None, context='misura'):
	"""Veusz-based translatable messages tagging."""
	return QtCore.QCoreApplication.translate(context, text,
                                     disambiguation=disambiguation)

# CONNECTION SHORTCUTS
def default(host='localhost', port=3880, user='admin', password='admin'):
	addr='https://{}:{}/RPC'.format(host,port)
	network.getConnection(addr,user,password,smart=True)
	return network.manager.remote

def from_argv():
	"""Get connection from command line arguments"""
	import sys, getopt
	logging.debug('%s %s', 'from argv', sys.argv)
	opts, args=getopt.getopt(sys.argv[1:], 'h:p:u:w:')
	r={'-h':'localhost', '-p':3880,
		'-u':'admin','-w':'admin'}
	for opt, val in opts:
		r[opt]=val
	return default(host=r['-h'],port=r['-p'],user=r['-u'],password=r['-w'])