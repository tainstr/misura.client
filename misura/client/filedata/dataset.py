#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Libreria per il plotting semplice durante l'acquisizione."""
from veusz import document
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


class MisuraDataset(document.Dataset):

    def __init__(self, data=[], linked=False):
        document.Dataset.__init__(self, data=data, linked=linked)
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
        self.m_label = ''
        """Label for GUI"""
        self.tags = set([])
        self.m_opt = False

    @property
    def mtype(self):
        """Object type"""
        return self.__class__.__name__
    
    def saveDataRelationToText(self, fileobj, name):
        """Write data if changed from the linked file"""
        # TODO: only if ds is not equal to its original version
        # build up descriptor
        out = "SetDataVal('{}','data', slice(None,None), [" .format(name)
        fileobj.write(out)
        fileobj.write(self.datasetAsText(fmt='%e', join=' ').replace('\n', ', '))
        fileobj.write("])\n")
        
        for attr in ('m_keep', 'm_name', 'm_pos', 'm_col', 'm_var',
                     'm_label', 'm_initialDimension', 'm_percent', 'm_update',
                     'unit','old_unit'):
            out = "SetDataAttr({!r}, {!r}, {!r})\n".format(name, attr, getattr(self, attr))
            fileobj.write(out)
        
