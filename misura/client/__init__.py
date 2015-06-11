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

def configure_logger():
	import os
	import logging
	from misura.client.clientconf import confdb
	from misura.client import units

	logging.basicConfig(level=confdb['loglevel'])
	logdir = os.path.dirname(confdb['logfile'])
	if not os.path.exists(logdir):
		os.makedirs(logdir)
	logsize = units.Converter.convert('kilobyte','byte', confdb['logsize'])
	rotating_file_handler = logging.handlers.RotatingFileHandler(confdb['logfile'], maxBytes=logsize, backupCount=confdb['lognumber'])
	rotating_file_handler.setFormatter(logging.Formatter("%(levelname)s: %(asctime)s %(message)s"))
	logging.getLogger().addHandler(rotating_file_handler)

configure_logger()
