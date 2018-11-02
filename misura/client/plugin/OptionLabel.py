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

    def __init__(self, *args, **kwargs):
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
        s.add(setting.Str('format', '',
                          descr='Formatter',
                          usertext='Formatter'),
              1)
        s.add(setting.Int(
            'changeset', 0,
            descr='Changeset',
            usertext='Changeset'),
            100) # hidden=True,
        
        
    def update(self):
        """Update OptionLabel with the current option text"""
        from misura.client import axis_selection as axsel
        self.doc = self.document
        data = self.document.data
        y = self.settings.yData
        opt = self.settings.option
        fmt = self.settings.format
        obj, name = data[y].linked.conf.from_column(opt)
        logging.debug('OptionLabel', self.settings.option, y, opt, name, obj)
        self.toset(self, 'changeset', obj._changeset)
        self.opt = obj.gete(name)
        val = obj[name]
        typ = self.opt['type']
        if fmt and typ!='Table':
            fmt = '{:'+fmt+'}'
            val = fmt.format(val)
        else:
            if typ in ['String', 'TextArea']:
                func = str
            else:
                func = getattr(self, 'cvt_'+typ, lambda val: 'NotSupported: {}'.format(typ))
            val = func(val)
        
        self.toset(self, 'label', val)
        self.apply_ops()
    
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
        r = u'<math>\n<mtable columnlines="solid">\n'
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
        
        r += u'</mtable>\n</math>' 
        return r
        


document.thefactory.register(OptionLabel)
