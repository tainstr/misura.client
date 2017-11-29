#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Libreria per il plotting semplice durante l'acquisizione."""
import collections
from __builtin__ import property

from veusz import datasets
from misura.canon import option
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from .. import units



class Sample(object):

    def __init__(self, conf=option.ConfigurationProxy(), linked=None, ref=True, idx=-1):
        self.conf = conf
        self.ref = ref
        self.linked = linked
        self.m_style = False
        self.m_marker = False
        self.m_color = False
        self.children = collections.OrderedDict()  # children datasets
        self._name = 'sample'
        self.idx = idx
        self.parent = False

    @property
    def mtype(self):
        """Object type"""
        return self.__class__.__name__

    def name(self):
        return self._name

    def __str__(self):
        fn = 'None'
        if self.linked is not None:
            fn = self.linked.filename
        return 'Sample Obj: %r\nConf: %r\nFilename:%r\nReference: %s' % (self, self.conf, fn, self.ref)

    def __setitem__(self, key, val):
        self.conf[key] = val

    def __getitem__(self, key):
        return self.conf[key]

    def get(self, key, opt):
        return self.conf.desc.get(key, opt)

    def has_key(self, key):
        return self.conf.has_key(key)
        
class AbstractMisuraDataset(object):
    def __init__(self, linked=False):
        self.attr = {'label': ''}
        self.m_opt = False
# 		assert linked!=False
        self.m_keep = True
        """Save on commit"""
        self.m_name = ''
        """Dataset name"""
        self.m_pos = 0
        """Listing position"""
        self.m_smp = Sample(linked=linked)
        """Sample reference"""
        self.m_col = ''
        """Column name"""
        self.m_var = ''
        """Variable name"""
        self.m_initialDimension = None
        """Initial dimension configured for the dataset."""
        self.m_update = False
        """Update on reload"""
        self.unit = None
        """Measurement unit"""
        self.old_unit = None
        """Original measurement unit"""
        self.tags = set([])
        
    @property
    def m_label(self):
        return self.attr['label']
    @m_label.setter
    def m_label(self, nval):
        self.attr['label'] = nval
        
    def _get_unit(self, name, alt=None):
        """Get proper unit based on Table column, if
        dataset represents a column in the table"""
        u = self.m_opt.get(name, alt)
        if not self.m_opt['type']=='Table' or u==alt or isinstance(u, basestring):
            return u
        #FIXME: Ineffective, see design issue FLTD-348
        i = self.m_opt.get('column', -1)
        return u[i]
    
    def _set_unit(self, name, nval):
        """Set proper unit based on Table column,if
        dataset represents a column in the table"""
        u = self.m_opt.get(name, None)
        if not self.m_opt['type']=='Table' or u==None or isinstance(u, basestring):
            self.m_opt[name] = nval 
            return 
        #FIXME: Ineffective, see design issue FLTD-348
        i = self.m_opt.get('column', -1)
        self.m_opt[name][i] = nval
                
        
    @property
    def unit(self):
        u = self.attr['unit']
        if isinstance(u, list):
            u=u[-1]
        return u
    
    @unit.setter
    def unit(self, nval):
        if self.m_opt and nval:
            self._set_unit('csunit', nval)
        self.attr['unit'] = nval
        
    @property
    def old_unit(self):
        if not self.m_opt:
            return self.attr['old_unit']
        return self._get_unit('unit', alt=self.attr['old_unit'])
    
    @old_unit.setter
    def old_unit(self, nval):
        if not self.m_opt:
            self.attr['old_unit'] = nval
        else:
            self.attr['old_unit'] = self._get_unit('unit') 
        
    @property
    def m_percent(self):
        # This is natively a part ds
        if self.old_unit in ('None', None):
            return False
        if self.unit in units.from_base['part']:
            return True
        return False
    
    @m_percent.setter 
    def m_percent(self, nval):
        logging.error('read-only m_percent', nval)
        
    @property
    def m_update(self):
        return self.attr['m_update']
    @m_update.setter
    def m_update(self, nval):
        self.attr['m_update'] = nval
        
    @property
    def m_initialDimension(self):
        ini = self.attr['m_initialDimension']
        if self.m_opt:
            ini = self.m_opt.get('initialDimension', ini)
            self.attr['m_initialDimension'] = ini
        if not ini:
            return None
        # Convert initial dimension to the current unit
        u = getattr(self, 'unit', 'percent')
        ou = getattr(self, 'old_unit', u)
        ini1 =  units.Converter.convert(ou, u,  ini)
        return ini1
    
    @m_initialDimension.setter
    def m_initialDimension(self, nval):
        if nval is None:
            self.attr['m_initialDimension'] = nval
            return None
        # Convert initial dimension to the original unit
        u = getattr(self, 'unit', 'percent')
        ou = getattr(self, 'old_unit', u)
        ini1 = units.Converter.convert(u, ou,  nval)
        self.attr['m_initialDimension'] = ini1
        if self.m_opt:
            self.m_opt['initialDimension'] = ini1
        
    @property
    def m_keep(self):
        return self.attr['m_keep']
    @m_keep.setter
    def m_keep(self, nval):
        self.attr['m_keep'] = nval
        
    @property
    def m_name(self):
        return self.attr['m_name']
    @m_name.setter
    def m_name(self, nval):
        self.attr['m_name'] = nval
        
    @property
    def m_pos(self):
        return self.attr['m_pos']
    @m_pos.setter
    def m_pos(self, nval):
        self.attr['m_pos'] = nval
        
#     @property
#     def m_smp(self):
#         return self.attr['m_smp']
#     @m_smp.setter
#     def m_smp(self, nval):
#         self.attr['m_smp'] = nval
        
    @property
    def m_var(self):
        return self.attr['m_var']
    @m_var.setter
    def m_var(self, nval):
        self.attr['m_var'] = nval

    @property
    def mtype(self):
        """Object type"""
        return self.__class__.__name__
           
class MisuraDataset(datasets.Dataset, AbstractMisuraDataset):
    def __init__(self, data=[], linked=False):
        datasets.Dataset.__init__(self, data=data, linked=linked)
        AbstractMisuraDataset.__init__(self, linked=linked)
