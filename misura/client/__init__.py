#!/usr/bin/python
# -*- coding: utf-8 -*-
import sip
API_NAMES = ["QDate", "QDateTime", "QString",
             "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)
from parameters import determine_path

from PyQt4 import QtCore
import network, os


def _(text, disambiguation=None, context='misura'):
    """Veusz-based translatable messages tagging."""
    return QtCore.QCoreApplication.translate(context, text,
                                             disambiguation=disambiguation)

# CONNECTION SHORTCUTS


def default(host='localhost', port=3880, user='admin', password='admin', mac=''):
    addr = 'https://{}:{}/RPC'.format(host, port)
    network.getConnection(addr, user, password, mac=mac, smart=True)
    return network.manager.remote


def from_argv():
    """Get connection from command line arguments"""
    import sys
    import getopt
    import logging
    logging.debug('%s %s', 'from argv', sys.argv)
    opts, args = getopt.getopt(sys.argv[1:], 'h:p:u:w:')
    r = {'-h': 'localhost', '-p': 3880,
         '-u': 'admin', '-w': 'admin'}
    for opt, val in opts:
        r[opt] = val
    return default(host=r['-h'], port=r['-p'], user=r['-u'], password=r['-w'])


def configure_logger(log_file_name):
    import os
    import logging
    import logging.handlers
    from misura.client.clientconf import confdb
    from misura.client.units import Converter

    logdir = confdb['logdir']
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    logsize = Converter.convert('kilobyte', 'byte', confdb['logsize'])
    log_file = os.path.join(confdb['logdir'], log_file_name)
    rotating_file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=logsize, backupCount=confdb['lognumber'])
    rotating_file_handler.setFormatter(
        logging.Formatter("%(levelname)s: %(asctime)s %(message)s"))
    logging.getLogger().addHandler(rotating_file_handler)
    level = confdb['loglevel']
#     level = 0
    logging.getLogger().setLevel(level)
