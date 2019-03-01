#!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib
import platform
import select
import socket
from time import sleep, time
from exceptions import BaseException
from traceback import format_exc

import httplib
import xmlrpclib
from xmlrpclib import ServerProxy, ProtocolError, SafeTransport
import Cookie

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

from .mproxy import MisuraProxy, reconnect, urlauth, dataurl, remote_dbdir
from .wake_on_lan import wake_on_lan

import sip
API_NAMES = ["QDate", "QDateTime", "QString",
             "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)
from PyQt4 import QtCore


from .info import ServerInfo
from misura.client.network.network_manager import NetworkManager

from .transfer_thread import TransferThread

global ess
ess = ServerInfo()
ess.fromAddr('misura.expertsystemsolutions.it:80')
ess.name = 'Simulation Server'
ess.host = 'misura.expertsystemsolutions.it'
ess.serial = 'ESimulServ'


manager = NetworkManager()


def simpleConnection(addr, user='', password='', mac='', save=True):
    addr = str(addr)
    logging.debug('simpleConnection', addr, user, password, mac, save)
    if '@' in addr:
        usrpass, addr = addr.replace('https://', '').split('@')
        addr = addr.lower().replace('/rpc', '')
        if ':' in usrpass:
            user, password = usrpass.split(':')
        else:
            user = usrpass
    if not addr.startswith('https'):
        addr = 'https://' + addr
    if not addr.endswith('/RPC'):
        addr += '/RPC'
    logging.debug('simpleConnection2', addr, user, password, mac)

    try:
        obj = MisuraProxy(addr, user=user, password=password, mac=mac)
    except:
        logging.debug('FAILED simpleConnection at instantiation')
        logging.debug(format_exc())
        return False, None
    try:
        obj.remObj.echo('echo')
    except ProtocolError as err:
        logging.debug('FAILED simpleConnection at echo')
        logging.debug(format_exc())
        if err.errcode == 401:
            obj._error = 'Authorization Failed!'
        elif err.errcode == 409:
            obj._error = 'Another user is currently logged in.'
        return False, obj
    except socket.error as err:
        logging.debug('FAILED simpleConnection at echo - socket error')
        obj._error = 'Socket error [{}]: {}'.format(err.errno, err.strerror)
        logging.debug(format_exc())
        return False, obj
    except:
        logging.debug('FAILED simpleConnection at echo - unknown')
        obj._error = 'Unknown Error'
        logging.debug(format_exc())
        return False, obj
    
    manager.emit(QtCore.SIGNAL(
        'connected(QString,QString,QString,QString,QString,QString,bool)'), addr, user, password, obj['eq_mac'], obj['eq_sn'], obj['name'], save)
    return True, obj


def getConnection(addr, user='', password='', mac='', save=True, smart=False):
    """Connects to a remote address"""
    global manager
    st, obj = simpleConnection(addr, user, password, mac, save)
    setRemote(obj)
    if not st:
        logging.debug('Connection failed')
        return st, obj
    manager.remote.remObj.send_log(
        "Client connection: " + repr(platform.uname()))
    logging.debug('Connected to', addr)
    manager.connected = True
    manager.emit(QtCore.SIGNAL('connected()'))
    manager.remote._smartnaming = smart
    return True, manager.remote


def setRemote(obj):
    global manager
    logging.debug('Setting network.manager.remote', repr(obj))
    manager.addr = obj.addr
    manager.user = obj.user
    manager.password = obj.password
    manager.remote = obj
    manager.error = obj._error
    manager.connected = True
    manager.emit(QtCore.SIGNAL('connected()'))
    # Clear all registered widgets
    try:
        from ..live import registry
    except:
        from live import registry
    registry.clear()


def closeConnection():
    """Disconnette"""
    manager.emit(QtCore.SIGNAL('disconnected()'))
    manager.connected = False
    if manager.remote != None:
        manager.remote.users.logout()
    manager.remote = None
    logging.debug('Disconnected from', manager.addr)
    return True

if __name__ == '__main__':
    import sys
    from misura.client import iutils
    iutils.initApp()
    app = iutils.app
#	qb=ServerSelector()
#	qb.show()
    sys.exit(app.exec_())
