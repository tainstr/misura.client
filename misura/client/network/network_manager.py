#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import select
import socket
from time import sleep
from traceback import format_exc

try:
    from PyQt4 import QtCore
except:
    QtCore = None

from info import ServerInfo

try:
    from misura.client import pybonjour
except:
    pybonjour = False

regtype = '_https._tcp'
timeout = 2

# FIXME: should be qt-independent and run from live.KidRegistry!


class NetworkManager(QtCore.QThread):
    addr = ''
    connected = False
    remote = None
    transport = False
    
    def __init__(self):
        self.scan = True
        """Ciclo di scansione attivo?"""
        self.user = 'admin'
        self.password = 'admin'
        self.queue = []
        self.resolved = {}
        self.servers = {}
        self.browser = False
        """Dizionario contenente i server disponibili"""
        QtCore.QThread.__init__(self)
        try:
            self.browser = pybonjour.DNSServiceBrowse(
                regtype=regtype, callBack=self.browse_callback)
        except:
            logging.debug(format_exc())

    def query_record_callback(self, sdRef, flags, interfaceIndex, errorCode, fullname,
                              rrtype, rrclass, rdata, ttl):
        """Get the IP address of the referenced service"""
        # Unqueue this reference
        logging.debug('query_record_callback', sdRef)
        self.queue.remove(sdRef)
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return
        ip = socket.inet_ntoa(rdata)  # IP
        logging.debug('Searching', fullname, self.resolved)
        srv = self.resolved[fullname.replace('.', '')]
        srv.ip = ip
        logging.debug('Found service:', srv)
        self.emit(QtCore.SIGNAL('found(QString)'), srv.addr)
        self.servers[srv.fullname] = srv
        # Close query reference
        sdRef.close()
        self.transport = False

    def resolve_callback(self, sdRef, flags, interfaceIndex, errorCode, fullname,
                         hosttarget, port, txtRecord):
        """Full resolution of a service"""
        if not pybonjour:
            return
        # Unqueue this reference
        logging.debug('resolve_callback', sdRef)
        self.queue.remove(sdRef)
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            logging.debug('kDNSService Error:', errorCode)
            return
        if not fullname.startswith('misura'):
            logging.debug('Wrong service name:', fullname)
            return
        logging.debug('Query IP')
        # Query for IP address
        query_sdRef = pybonjour.DNSServiceQueryRecord(interfaceIndex=interfaceIndex,
                                                      fullname=hosttarget,
                                                      rrtype=pybonjour.kDNSServiceType_A,
                                                      callBack=self.query_record_callback)

        srv = ServerInfo(fullname, hosttarget, port, txtRecord[1::2])
        self.resolved[hosttarget.replace('.', '')] = srv
        # Put the query in the queue
        self.queue.append(query_sdRef)
        # Close resolve reference
        sdRef.close()
        logging.debug('done resolve_callback')

    def browse_callback(self, sdRef, flags, interfaceIndex, errorCode, serviceName,
                        regtype, replyDomain):
        """Inspect what the browser has found and evaluate if to resolve or to discart it."""
        if not pybonjour:
            return
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            logging.debug('Found error ', errorCode)
            return
        if serviceName[:7] != 'misura':
            logging.debug('Wrong service name:', serviceName)
            return
        fullname = serviceName + '.' + regtype + replyDomain
        # If flags means the service has been lost, remove it
        if not (flags & pybonjour.kDNSServiceFlagsAdd):
            if not self.servers.has_key(fullname):
                return
            srv = self.servers.pop(fullname)
            logging.debug(self.servers)
            logging.debug('Service lost', srv)
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
            logging.debug('scan', self.queue)
            # Search for something to process
            ready = select.select([self.browser] + self.queue, [], [], 2)
            for ref in ready[0]:
                pybonjour.DNSServiceProcessResult(ref)
            # If there is nothing left to do, wait
            if len(self.queue) == 0:
                sleep(5)
        logging.debug('Network Manager CLOSED')
        self.browser.close()

    def copy(self, path=False):
        """Return a copy of this object with a new HTTP connection."""
        obj = self.remote.copy()
        obj.connect()
        return obj

    def set_remote(self, server=None):
        self.remote = server
        if not server:
            self.connected = False
            return False
        self.connected = True
        return True
