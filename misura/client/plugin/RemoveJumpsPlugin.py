#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Stepped jumps removal tool on target curve"""
import os
from traceback import format_exc
import numpy as np
from misura.canon.logger import get_module_logging
from tables.utils import idx2long
logging = get_module_logging(__name__)
from misura.canon import version as canon_version
from misura.client import version as client_version

import veusz.plugins as plugins
import veusz.document as document
from veusz.document import operations
import utils
from misura.client.clientconf import confdb
from misura.client import _

from PyQt4 import QtGui, QtCore

msg = _('Press Fix to correct the jump by translating points before or after the jump, \
Retry to seek next jump, Abort to exit from procedure')

class RemoveJumpsPlugin(utils.OperationWrapper, plugins.ToolsPlugin):

    """Intercept all curves at a given x or y by placing datapoints"""
    # a tuple of strings building up menu to place plugin on
    menu = ('Misura', 'Remove Jumps')
    # unique name for plugin
    name = 'RemoveJumps'
    # name to appear on status tool bar
    description_short = 'Remove jumps from the selected curve'
    # text to appear in dialog box
    description_full = 'Stepped procedure to select and remove jumps from a curve'
    
    def __init__(self, curve=''):
        """Create default Misura document"""

        self.fields = [
            plugins.FieldWidget("curve",
                                descr="Target curve:",
                                widgettypes=set(['xy']),
                                default=curve),
        ]
        
    def create_line(self):
        self.cmd.To(self.graph.path)
        self.cmd.Add('line', name='jump', mode='point-to-point', positioning='axes',
        xAxis=self.curve.settings.xAxis, yAxis=self.curve.settings.yAxis, clip=True)
        self.cmd.To('jump')
        self.cmd.Set('Line/color', 'red')
        self.cmd.Set('Line/width', '2pt')
        
    def move_line(self, idx):
        self.cmd.To(self.graph.path+'/jump')
        self.cmd.Set('xPos', self.x[idx])
        self.cmd.Set('xPos2', self.x[idx-1])
        self.cmd.Set('yPos', self.y[idx])
        self.cmd.Set('yPos2', self.y[idx-1])
        
    def delete_line(self):
        self.cmd.To(self.graph.path)
        self.cmd.Remove('jump')
    
    
    def remove_jump(self, idx, before=True):
        logging.debug('remove_jump', idx, before)
        if before:
            self.y[:idx] += self.y[idx]-self.y[idx-1]
        else:
            self.y[idx-1:] += self.y[idx-1]-self.y[idx]
        
        ds = self.doc.data[self.curve.settings.yData]
        ds.data = self.y
        self.ops.append(operations.OperationDatasetSet(self.curve.settings.yData, ds))
                            
        self.apply_ops()
            
    
    def jump_removal_step(self):
        self.filter = (self.xrange[0]<self.x)*(self.x<self.xrange[1]) * (self.yrange[0]<self.y)*(self.y<self.yrange[1])
        p = self.jump_index
        while p<len(self.jump_positions)-2:
            p += 1
            j = self.jump_positions[p]+1
            # Out of axis ranges
            if not self.filter[j]:
                logging.debug('Skipping', self.filter[j], self.x[j], self.y[j])
                continue
            break
        if p==len(self.jump_positions)-2:
            logging.debug('No more points to analyze')
            return False
        self.jump_index = p
        logging.debug('Analyzing jump index', j, self.jump_index)
        self.move_line(j)
        
        qm = QtGui.QMessageBox
        box = qm(qm.Question, _('Delete this jump?'), msg)
        box.addButton(str(_('Fix Before')), qm.AcceptRole)
        box.addButton(_('Fix After'), qm.ApplyRole)
        ignore = box.addButton(_('Ignore jump'), qm.ActionRole)
        abort = box.addButton(_('Abort'), qm.DestructiveRole)
        box.setDefaultButton(ignore)
        box.setEscapeButton(abort)
        box.exec_()
        btn = box.buttonRole(box.clickedButton())
        if btn == qm.DestructiveRole:
            return False
        if btn == qm.AcceptRole:
            self.remove_jump(j, before=True)
        if btn == qm.ApplyRole:
            self.remove_jump(j, before=False)
        return True
    

    def apply(self, cmd, fields):
        self.fields = fields
        self.cmd = cmd
        doc = cmd.document
        self.doc = doc
        
        self.curve = doc.resolveFullWidgetPath(fields['curve'])
        self.graph = self.curve.parent
        self.xrange = self.graph.getChild(self.curve.settings.xAxis).plottedrange
        self.yrange = self.graph.getChild(self.curve.settings.yAxis).plottedrange
        
        self.x = doc.data[self.curve.settings.xData].data
        self.y = doc.data[self.curve.settings.yData].data
        
        self.distance = abs(np.diff(self.y))
        
        
        self.jump_positions = np.argsort(self.distance)[::-1]
        
        self.create_line()
        self.jump_index = -1
        try:
            while self.jump_removal_step():
                logging.debug('Next step')
            logging.debug('Finished')
        except:
            logging.error(format_exc())
        self.delete_line()
        return True

plugins.toolspluginregistry.append(RemoveJumpsPlugin)
