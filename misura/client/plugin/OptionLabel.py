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

def clean_row(row, header):
    for i,h in enumerate(header):
        if len(h)==2 and h[1]=='Float':
            if row[i] is None:
                row[i] = 0
    return row


class OptionLabel(utils.OperationWrapper, widgets.TextLabel):
    typename = 'optionlabel'
    description = "Label for option"
    connected = False
    _proxy = False
    current_changeset = 0
    
    def __init__(self, *args, **kwargs):
        self.connected = False
        self.opt_name = []
        widgets.TextLabel.__init__(self, *args, **kwargs)
        if type(self) == OptionLabel:
            self.readDefaults()
            
        self.addAction(widgets.widget.Action('up', self.update,
                                                   descr='Update Label',
                                                   usertext='Update Label'))
        for name in ('prefix', 'format', 'option','dataset', 'showName'):
            self.settings.get(name).setOnModified(self.update)
   
        
    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        widgets.TextLabel.addSettings(s)
        s.add( setting.Dataset(
            'dataset', '',
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
        s.add(setting.Bool('showName', False,
                          descr='Show name',
                          usertext='Show name',
                          formatting=True),
              1)
        
        # Default text size
        s.Text.size = '8pt'
        
    @property
    def changeset(self):
        if not self.proxy:
            return -1
        return max([p._changeset for p in self.proxy])
        
    def check_update(self, *a):
        logging.debug('check_update', a, self.settings.option, self.current_changeset, self.changeset)
        if self.changeset and self.current_changeset<self.changeset:
            self.update()
            return True
        return False
    
    @property
    def proxy(self):
        if self._proxy:
            return self._proxy
        ds = self.settings.dataset
        y = self.document.data.get(ds, False)
        if not y:
            return []
        if not y.linked:
            logging.debug('No linked file for', ds)
            return []
        if not y.linked.conf:
            logging.debug('No configuration for linked file', ds)
            return []
        self._proxy = []
        self.opt_name = []
        split = ',' if ',' in self.settings.option else ';'
        for opt in self.settings.option.split(split):
            p, n= y.linked.conf.from_column(opt)
            self._proxy.append(p)
            self.opt_name.append(n) 
        return self._proxy
    
    def create_label(self, proxy, opt_name):
        """Create label fragment for `opt_name` of `proxy`"""
        if not proxy:
            return None
        if not opt_name in proxy:
            return None
        opt = proxy.gete(opt_name)
        if 'Hidden' in opt['attr']:
            return None
        fmt = self.settings.format
        val = proxy[opt_name]
        typ = opt['type']
        name = ''
        if self.settings.showName:
            name = opt['name']+': '
        if fmt and typ!='Table':
            fmt = '{:'+fmt+'}'
            val = name+fmt.format(val)
        else:
            if typ in ['String', 'TextArea']:
                func = lambda val,opt: '{}'.format(val)
            else:
                func = getattr(self, 'cvt_'+typ, 
                               lambda *a: 'NotSupported: {}'.format(typ))
            val = func(val, opt)
            if name and typ!='Table':
                val = name+val
         
        return val    
        
        
    def update(self):
        """Update OptionLabel with the current option text"""
        self.doc = self.document
        if not self.connected:
            self.document.signalModified.connect(self.check_update)
            self.connected = True
        # Force proxy reset
        self._proxy = False

        logging.debug('OptionLabel', self.settings.option, self.settings.dataset, 
                    self.proxy, self.opt_name, self.changeset)
        self.current_changeset = self.changeset
        split = ',' if ',' in self.settings.option else ';'
        opts = self.settings.option.split(split)
        label = ''
        newline = '\\\\'
        for i, proxy in enumerate(self.proxy):
            new = self.create_label(proxy, self.opt_name[i])
            if new is None:
                logging.info('Not creating option for', i, opts[i])
                continue
            # Remove closing tag
            if '</math>' in new:
                new = new.replace('</math>', '')
                newline = '\n'
            # Remove also opening tag if already found
            if '<math>' in label:
                new = new.replace('<math>','')
            label += new
            if i<len(self.proxy):
                label+=newline
        
        pre = self.settings.prefix
        
        # Add closing tag
        if '<math>' in label:
            label+='</math>'
        # Add prefix:
        elif pre:
            label = pre + ' '+ label
        
        self.toset(self, 'label', label)
        self.apply_ops()
        
    def draw(self, *a, **k):
        self.check_update()
        return super(OptionLabel,self).draw(*a, **k)
        
    
    def cvt_Integer(self, val, opt):
        if val<1e6:
            return str(val)
        return '{:E}'.format(val, opt)
    
    def cvt_Float(self, val, opt):
        if opt.get('precision',-1)>0:
            fmt = '{:.'+str(opt['precision'])+'f}'
            return fmt.format(val)
        return '{:.4E}'.format(val)
    
    def cvt_Meta(self, val, opt):
        r = ''
        for k,v in val.items():
            r += '{}:{:.2E}\\\\'.format(k,v)
        return r
    
    def cvt_Table(self, val, opt):
        """Create a MathML table"""
        if len(val)<=1:
            return 'Empty table'
        header0 = val[0]
        N = len(header0)
        visible = opt.get('visible', [1]*N)
        precision0 = opt.get('precision', [None]*N)
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
        if self.settings.showName and not pre:
            pre = opt['name']
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
            r+= row_fmt.format(*clean_row(row, header))
        
        r += u'</mtable>\n'
        if pre:
            r+= u'</mfrac>\n'
        r += u'</math>' 
        return r
        


document.thefactory.register(OptionLabel)
