#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from misura.client.widgets.active import *
from aChooser import aChooser
from .. import _
from ..network import TransferThread
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)


class aFileList(aChooser):
    
    def redraw(self):
        super(aFileList, self).redraw()
        self.file_actions = QtGui.QPushButton('...')
        self.file_actions.setMaximumWidth(40)
        self.file_menu = QtGui.QMenu() 
        self.file_actions.setMenu(self.file_menu)
        self.file_menu.addAction(_('Send'), self.send)
        self.file_menu.addAction(_('Download'), self.download)
        self.lay.addWidget(self.file_actions)
        self.prevIdx = 0
        self.transfer = False
        self.set_enabled()       

    def send(self, filename=False, *a, **kw):
        """Upload local file"""
        if filename:
            n=filename
        else:
            n = QtGui.QFileDialog.getOpenFileName(
                parent=self, caption=_("Upload File"))
        if len(n) == 0 or not os.path.exists(n):
            logging.debug('File Upload Aborted')
            return False
        url = self.remObj.conn_addr + \
            self.remObj['fullpath'][:-1]  # remove trailing /
        logging.debug('Transfer target:', repr(url), n, self.handle)
        self.transfer = TransferThread(
            url=url, outfile=n, post={'opt': self.handle}, parent=self)
        from ..live import registry
        self.transfer.set_tasks(registry.tasks)
        self.transfer.start()
        self.transfer.dlFinished.connect(self._after_send)
        return n
    
    def _after_send(self, *a):
        self.set(self.adapt2gui(str(self.transfer.outfile)))
        self.changed_option()
        
    def download(self, filename=False):
        """Download currently selected file"""
        if not filename:
            filename = QtGui.QFileDialog.getSaveFileName(self, 
                                                     _('Choose a filename where to save current selection'), 
                                                     self.current)
        if not filename:
            logging.debug('Bug report aborted')
            return False
        # remove final RPC
        addr = self.remObj.conn_addr[:-3] + 'conf'
        url = addr + \
            self.remObj['fullpath'] + self.handle +'/' + self.current
        logging.debug('Transfer target:', repr(url), self.current, self.handle)
        self.transfer = TransferThread(url=url, outfile=filename, parent=self)
        from ..live import registry
        self.transfer.set_tasks(registry.tasks)
        self.transfer.start()   
        return filename  
        
        
        
        
        
               