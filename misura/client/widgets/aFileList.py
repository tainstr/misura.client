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

    def __init__(self, *a, **kw):
        """Widget representing a FileList option type, allowing to upload a new file via the stream interface."""
        aChooser.__init__(self, *a, **kw)
        # TODO: make menu and add Download, Delete, Rename,... like in presets.
        self.bSend = QtGui.QPushButton('Send')
        self.bSend.setMaximumWidth(40)
        self.connect(self.bSend, QtCore.SIGNAL('clicked(bool)'), self.send)
        self.lay.addWidget(self.bSend)
        self.prevIdx = 0
        self.transfer = False
        self.set_enabled()

    def send(self, *args):
        """Upload local file"""
        n = QtGui.QFileDialog.getOpenFileName(
            parent=self, caption=_("Upload File"))
        if len(n) == 0 or not os.path.exists(n):
            logging.debug('File Upload Aborted')
            return False
        if os.path.basename(n) in self.prop['options']:
            # TODO: allow to overwrite....
            QtGui.QMessageBox.warning(self, _('Overwriting file'), _(
                'A file with the same name already exists.\nPlease choose a different one.'))
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
        
        
        
        
        
               