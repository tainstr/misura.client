#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Genering rendering utilities for a Misura Option object"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtCore

class OptionAbstractWidget(object):
    current_changeset = 0
    _proxy = False
    connected = False
    
    @property
    def changeset(self):
        if not self.proxy:
            return -1
        return max([p._changeset for p in self.proxy])
        
    def check_update(self, *a):
        #logging.debug('check_update', self.path, a, self.current_changeset, self.changeset)
        if self.changeset and self.current_changeset<self.changeset:
            self.update()
            return True
        return False
    
    @property
    def proxy(self):
        if self._proxy:
            return self._proxy
        ds = self.settings.dataset
        y = self.document.get_from_data_or_available(ds, False)
        # Ensure it is not a derived or native dataset
        y = y if hasattr(y, 'linked') else False
        # Search for a datasets starting with y:
        if not y and '/' in ds:
            prefix = ds.split('/')[0]
            logging.debug('Dataset not found, scanning prefix', ds, prefix)
            for d, yds in self.document.iter_data_and_available():
                if d.startswith(prefix) and hasattr(yds, 'linked'):
                    y = yds
                    break
        if not y:
            logging.debug('Dataset not found: will return an empty widget',ds)
            return []
        if not y.linked:
            logging.debug('No linked file for', ds)
            return []
        if not y.linked.conf:
            logging.debug('No configuration for linked file', ds)
            return []
        self._proxy = []
        self.opt_name = []
        from misura.client.live import registry
        for p, n in self.get_proxies_and_options(y.linked.conf):
            self._proxy.append(p)
            self.opt_name.append(n)
            if p and n and n in p:
                sig = 'client_changed_{}()'.format(p.plain_kid(n))
                registry.reconnect(sig, self.update)
        return self._proxy
    
    def get_proxies_and_options(self):
        """List all involved options"""
        return []
    
    def update(self):
        self.doc = self.document
        if not self.connected:
            self.document.signalModified.connect(self.check_update)
            self.connected = True
        # Force proxy reset
        self._proxy = False
        self.current_changeset = self.changeset
    
    def draw(self, *a, **k):
        self.check_update()
        return super(OptionAbstractWidget,self).draw(*a, **k)