#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Render a Misura Option object into a text label"""
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
import veusz.document as document
from . import utils
from veusz import widgets
import veusz.setting as setting
from misura.client import _

class OptionLabel(utils.OperationWrapper, widgets.TextLabel):
    typename = 'optionlabel'
    description = "Label for option"
    connected = False
    _proxy = False
    
    def __init__(self, *args, **kwargs):
        self.connected = False
        widgets.TextLabel.__init__(self, *args, **kwargs)
        if type(self) == OptionLabel:
            self.readDefaults()
            
        self.addAction(widgets.widget.Action('up', self.update,
                                                   descr='Update Label',
                                                   usertext='Update Label'))
   
        
    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        widgets.TextLabel.addSettings(s)
        s.add( setting.Dataset(
            'yData', 'y',
            descr=_('Dataset pointing to the containing option'),
            usertext=_('Dataset')), 0 ) 
        
        s.add(setting.Str('option', '',
                          descr='Option path',
                          usertext='Option path'),
              1)
        s.add(setting.Str('prefix', '',
                          descr='Prefix',
                          usertext='Prefix'),
              2)
        s.add(setting.Str('format', '',
                          descr='Formatter',
                          usertext='Formatter'),
              3)
        s.add(setting.Int(
            'changeset', -1,
            descr='Changeset',
            usertext='Changeset'),
            100) # hidden=True,
        
        # Default text size
        s.Text.size = '8pt'
        
        
    def check_update(self, *a):
        logging.debug('check_update', a, self.settings.option, self.settings.changeset, self.proxy._changeset)
        if self.settings.changeset<self.proxy._changeset:
            self.update()
            return True
        return False
    
    @property
    def proxy(self):
        if self._proxy:
            return self._proxy
        y = self.settings.yData
        self._proxy, self.opt_name = self.document.data[y].linked.conf.from_column(self.settings.option)
        return self._proxy
        
        
    def update(self):
        """Update OptionLabel with the current option text"""
        self.doc = self.document
        if not self.connected:
            self.document.signalModified.connect(self.check_update)
            self.connected = True
            
        opt = self.settings.option
        fmt = self.settings.format
        pre = self.settings.prefix
        logging.debug('OptionLabel', self.settings.option, self.settings.yData, 
                      opt, self.proxy, self.opt_name)
        self.toset(self, 'changeset', self.proxy._changeset)
        self.opt = self.proxy.gete(self.opt_name)
        val = self.proxy[self.opt_name]
        typ = self.opt['type']
        if fmt and typ!='Table':
            fmt = '{:'+fmt+'}'
            val = pre + ' ' + fmt.format(val)
        else:
            if typ in ['String', 'TextArea']:
                func = pre + ' '+str
            else:
                func = getattr(self, 'cvt_'+typ, lambda val: 'NotSupported: {}'.format(typ))
            val = func(val)
            if typ!='Table':
                val = pre + ' '+ val
        
        self.toset(self, 'label', val)
        self.apply_ops()
        
    def draw(self, *a, **k):
        self.check_update()
        return super(OptionLabel,self).draw(*a, **k)
        
    
    def cvt_Integer(self, val):
        if val<1e6:
            return str(val)
        return '{:E}'.format(val)
    
    def cvt_Float(self, val):
        return '{:.4E}'.format(val)
    
    def cvt_Meta(self, val):
        r = ''
        for k,v in val.items():
            r += '{}:{:.2E}\\\\'.format(k,v)
        return r
    
    def cvt_Table(self, val):
        """Create a MathML table"""
        if len(val)<=1:
            return 'Empty table'
        header0 = val[0]
        N = len(header0)
        visible = self.opt.get('visible', [1]*N)
        precision0 = self.opt.get('precision', [None]*N)
        N = sum(visible)
        header = []
        precision = []
        for i, h in enumerate(header0):
            if visible[i]:
                header.append(h)
                precision.append(precision0[i])
                
        # Build table
        r = u'<math>\n'
        pre = self.settings.prefix
        if pre:
            r+=u'<mfrac><mtext>{}</mtext>\n'.format(pre)
        r+=u'<mtable columnlines="solid">\n'
        
        
        header_fmt = u'<mtr> ' + (u'<mtd><mtext>{}</mtext></mtd> ')*N + u'</mtr>\n'
        r += header_fmt.format(*[ h[0].replace('&','+') for h in header])
        
        # Build row format
        row_fmt = u'<mtr> '
        for i, h in enumerate(header):
            row_fmt +=u'<mtd>{'
            if len(h)==2:
                p = precision[i]
                if self.settings.format:
                    row_fmt += u':'+self.settings.format
                elif h[1]=='Float':
                    if p is not None:
                        row_fmt += u':.'+str(p) + u'f'
                    else:
                        # Generic formatter
                        #TODO: use extend_decimals?
                        row_fmt += u':.2E'
            row_fmt += u'}</mtd>'
        row_fmt += u'</mtr>\n'
        
        # Rows
        for row0 in val[1:]:
            row = []
            for i,z in enumerate(row0):
                if visible[i]:
                    row.append(z)
            r+= row_fmt.format(*row)
        
        r += u'</mtable>\n'
        if pre:
            r+= u'</mfrac>\n'
        r += u'</math>' 
        return r
        


document.thefactory.register(OptionLabel)
