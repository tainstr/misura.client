 #!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib, platform
import select
import socket
from time import sleep, time
from exceptions import BaseException
from traceback import format_exc

import httplib
import xmlrpclib
from xmlrpclib import ServerProxy, ProtocolError, SafeTransport
import Cookie

from misura.canon.logger import Log as logging
from mproxy import MisuraProxy, reconnect, urlauth, dataurl, remote_dbdir

import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
	sip.setapi(name, API_VERSION)
from PyQt4 import QtCore



from info import ServerInfo
from manager import NetworkManager

from transfer_thread import TransferThread

global ess
ess=ServerInfo()
ess.fromAddr('misura.expertsystemsolutions.it:80')
ess.name='Simulation Server'
ess.host='misura.expertsystemsolutions.it'
ess.serial='ESimulServ'



manager=NetworkManager()





def simpleConnection(addr,user='',password='',save=True):
	addr=str(addr)
	logging.debug('%s %s %s %s', 'simpleConnection', addr, user, password)
	if '@' in addr:
		usrpass,addr=addr.replace('https://','').split('@')
		addr=addr.lower().replace('/rpc','')
		if ':' in usrpass:
			user,password=usrpass.split(':')
		else: user=usrpass
	if not addr.startswith('https'):
		addr='https://'+addr
	if not addr.endswith('/RPC'):
		addr+='/RPC'
	logging.debug('%s %s %s %s', 'simpleConnection2', addr, user, password)
	
	try:
		obj=MisuraProxy(addr,user=user,password=password)
	except:
		logging.debug('FAILED simpleConnection at instantiation')
		logging.debug(format_exc())
		return False, None
	try:
		obj.remObj.echo('echo')
	except ProtocolError as err:
		logging.debug('%s', 'FAILED simpleConnection at echo')
		logging.debug(format_exc())
		if err.errcode==401:
			obj._error='Authorization Failed!'
		elif err.errcode==409:
			obj._error='Another user is currently logged in.'
		return False, obj
	except socket.error as err:
		logging.debug('FAILED simpleConnection at echo - socket error')
		obj._error='Socket error [{}]: {}'.format(err.errno,err.strerror)
		logging.debug(format_exc())
		return False, obj
	except:
		logging.debug('FAILED simpleConnection at echo - unknown')
		obj._error='Unknown Error'
		logging.debug(format_exc())
		return False, obj
	#TODO: prendere serial e name ed emetterli!
	manager.emit(QtCore.SIGNAL('connected(QString,QString,QString,bool)'),addr,user,password,save)
	return True, obj

def getConnection(addr, user='', password='',save=True,smart=False):
	"""Connects to a remote address"""
	global manager
	st,obj=simpleConnection(addr,user,password,save)
	setRemote(obj)
	if not st:
		logging.debug('%s', 'Connection failed')
		return st,obj
	manager.remote.remObj.send_log("Client connection: " +repr(platform.uname()))
	logging.debug('%s %s', 'Connected to', addr)
	manager.connected=True
	manager.emit(QtCore.SIGNAL('connected()'))
	manager.remote._smartnaming=smart
	return True, manager.remote

def setRemote(obj):
	global manager
	logging.debug('%s %s', 'Setting network.manager.remote', repr(obj))
	manager.addr=obj.addr
	manager.user=obj.user
	manager.password=obj.password
	manager.remote=obj
	manager.error=obj._error
	manager.connected=True
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
	manager.connected=False
	if manager.remote!=None:
		manager.remote.users.logout()
	manager.remote=None
	logging.debug('%s %s', 'Disconnected from', manager.addr)
	return True

if __name__=='__main__':
	import sys
	from misura.client import iutils
	iutils.initApp()
	app=iutils.app
#	qb=ServerSelector()
#	qb.show()
	sys.exit(app.exec_())
