#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging
import select
import socket
from time import sleep
from traceback import format_exc

try:
	from PyQt4 import QtCore
except:
	QtCore=None
	
from info import ServerInfo

try:
	from misura.client import pybonjour
except:
	pybonjour=False

regtype='_https._tcp'
timeout  = 2

#FIXME: should be qt-independent and run from live.KidRegistry!
class NetworkManager(QtCore.QThread):
	def __init__(self):
		self.scan=True
		"""Ciclo di scansione attivo?"""
		self.user='admin'
		self.password='admin'
		self.queue=[]
		self.resolved={}
		self.servers={}
		self.browser=False
		"""Dizionario contenente i server disponibili"""
		QtCore.QThread.__init__(self)
		try:
			self.browser=pybonjour.DNSServiceBrowse(regtype = regtype, callBack = self.browse_callback)
		except:
			logging.debug(format_exc())
		self.addr=''
		"""Indirizzo cui si è connessi"""
		self.connected=False
		"""È stata stabilita una connessione?"""
		self.remote=None
		"""Oggetto MisuraProxy per la connessione corrente"""
		self.transport=False

	def query_record_callback(self, sdRef, flags, interfaceIndex, errorCode, fullname,
								rrtype, rrclass, rdata, ttl):
		"""Get the IP address of the referenced service"""
		# Unqueue this reference
		logging.debug('%s %s', 'query_record_callback', sdRef)
		self.queue.remove(sdRef)
		if errorCode != pybonjour.kDNSServiceErr_NoError:
			return 
		ip=socket.inet_ntoa(rdata) #IP
		logging.debug('%s %s %s', 'Searching', fullname, self.resolved)
		srv=self.resolved[fullname.replace('.', '')]
		srv.ip=ip
		logging.debug('%s %s', 'Found service:', srv)
		self.emit(QtCore.SIGNAL('found(QString)'), srv.addr)
		self.servers[srv.fullname]=srv
		# Close query reference
		sdRef.close()
		self.transport=False
		
	def resolve_callback(self, sdRef, flags, interfaceIndex, errorCode, fullname,
						hosttarget, port, txtRecord):
		"""Full resolution of a service"""
		if not pybonjour:
			return
		# Unqueue this reference
		logging.debug('%s %s', 'resolve_callback', sdRef)
		self.queue.remove(sdRef)
		if errorCode != pybonjour.kDNSServiceErr_NoError:
			logging.debug('%s %s', 'kDNSService Error:', errorCode)
			return
		if not fullname.startswith('misura'):
			logging.debug('%s %s', 'Wrong service name:', fullname)
			return
		logging.debug('%s', 'Query IP')
		# Query for IP address
		query_sdRef = pybonjour.DNSServiceQueryRecord(interfaceIndex = interfaceIndex,
									fullname = hosttarget,
									rrtype = pybonjour.kDNSServiceType_A,
									callBack = self.query_record_callback)
									
		srv=ServerInfo(fullname, hosttarget, port, txtRecord[1::2])
		self.resolved[hosttarget.replace('.', '')]=srv
		# Put the query in the queue
		self.queue.append(query_sdRef)
		# Close resolve reference
		sdRef.close()
		logging.debug('%s', 'done resolve_callback')
		
	def browse_callback(self, sdRef, flags, interfaceIndex, errorCode, serviceName,
						regtype, replyDomain):
		"""Inspect what the browser has found and evaluate if to resolve or to discart it."""
		if not pybonjour:
			return
		if errorCode != pybonjour.kDNSServiceErr_NoError:
			logging.debug('%s %s', 'Found error ', errorCode)
			return
		if serviceName[:7]!='misura': 
			logging.debug('%s %s', 'Wrong service name:', fullname)
			return
		fullname=serviceName+'.'+regtype+replyDomain
		# If flags means the service has been lost, remove it
		if not (flags & pybonjour.kDNSServiceFlagsAdd):
			if not self.servers.has_key(fullname): return
			srv=self.servers.pop(fullname)
			logging.debug('%s', self.servers)
			logging.debug('%s %s', 'Service lost', srv)
			self.emit(QtCore.SIGNAL('lost(QString)'), srv.fullname)
			return 
		# Ask full resolution of the service
		resolve_sdRef = pybonjour.DNSServiceResolve(0, interfaceIndex,
													serviceName,
													regtype,
													replyDomain,
													self.resolve_callback)
		# Put the resolution in the queue
		self.queue.append(resolve_sdRef)
			
	def run(self):
		"""Network scanning thread"""
		if not pybonjour:
			return
		sleep(1)
		pybonjour.DNSServiceProcessResult(self.browser)
		while self.scan:
			logging.debug('%s %s', 'scan', self.queue)
			# Search for something to process
			ready = select.select([self.browser]+self.queue, [], [], 2)
			for ref in ready[0]:
				pybonjour.DNSServiceProcessResult(ref)
			# If there is nothing left to do, wait
			if len(self.queue)==0: sleep(5)
		logging.debug('%s', 'Network Manager CLOSED')
		self.browser.close()
		
	def copy(self, path=False):
		"""Return a copy of this object with a new HTTP connection."""
		obj=self.remote.copy()
		obj.connect()
		return obj
		
	def set_remote(self, server=None):
		self.remote=server
		if not server:
			self.connected=False
			return False
		self.connected=True
		return True
		
	
