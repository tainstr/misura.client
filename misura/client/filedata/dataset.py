#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Libreria per il plotting semplice durante l'acquisizione."""
from veusz import datasets
from misura.canon import option
import collections


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


class MisuraDataset(datasets.Dataset):

    def __init__(self, data=[], linked=False):
        datasets.Dataset.__init__(self, data=data, linked=linked)
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
        self.m_percent = False
        """Flag which indicate if the dataset has been converted to percentile."""
        self.m_initialDimension = None
        """Initial dimension configured for the dataset."""
        self.m_update = False
        """Update on reload"""
        self.unit = None
        """Measurement unit"""
        self.old_unit = None
        """Original measurement unit"""
        self.tags = set([])
        self.m_opt = False
        
    @property
    def m_percent(self):
        return self.attr['m_percent']
    @m_percent.setter
    def m_percent(self, nval):
        self.attr['m_percent'] = nval
        
    @property
    def m_label(self):
        return self.attr['label']
    @m_label.setter
    def m_label(self, nval):
        self.attr['label'] = nval
        
    @property
    def unit(self):
        return self.attr['unit']
    @unit.setter
    def unit(self, nval):
        self.attr['unit'] = nval
        
    @property
    def old_unit(self):
        return self.attr['old_unit']
    @old_unit.setter
    def old_unit(self, nval):
        self.attr['old_unit'] = nval
        
#     @property
#     def m_opt(self):
#         return self.attr['m_opt']
#     @m_opt.setter
#     def m_opt(self, nval):
#         self.attr['m_opt'] = nval
        
    @property
    def m_update(self):
        return self.attr['m_update']
    @m_update.setter
    def m_update(self, nval):
        self.attr['m_update'] = nval
        
    @property
    def m_initialDimension(self):
        return self.attr['m_initialDimension']
    @m_initialDimension.setter
    def m_initialDimension(self, nval):
        self.attr['m_initialDimension'] = nval
        
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
           
        
