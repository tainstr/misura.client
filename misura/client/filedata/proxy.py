#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Interfaces for local and remote file access"""
from misura.canon.logger import Log as logging
from misura.client.connection import addrConnection
from misura.canon.indexer import SharedFile
from cPickle import loads
import functools
import xmlrpclib
from misura.canon import option


class RemoteFileProxy(object):

    """Wrapper class for SharedFile. Does the necessary binary extraction and pickle/unpickle"""
    conf = False

    def __init__(self, obj, conf=False, live=None):
        self.obj = obj
        # It is considered live if has the same uid as parent FileServer live
        # uid.
        my = self.obj.get_uid()
        if live is None:
            live = self.obj.parent().get_live()
            live = my == live
        self.live = live
        self.conf = conf
        if conf is False:
            self.load_conf()
        else:
            self.conf = conf

    def load_conf(self):
        """Override remote load_conf method in order to receive remote tree 
        and build a local ConfigurationProxy object."""
        # The configuration of a live file is the remote server itself!
        if self.live:
            if not self.conf:
                self.conf = self.obj.root
            return True
        # Otherwise unpickle the configuration tree dict and get a
        # ConfigurationProxy for it
        d = self._decode(self.obj.conf_tree)
        logging.debug('%s %s %s', 'loading conf', len(d), d.keys())
        self.conf = option.ConfigurationProxy(desc=d)
        return True

    def copy(self):
        ro = self.obj.copy()
        ro.connect()
        r = RemoteFileProxy(ro, self.conf, self.live)
        return r

    def get_path(self):
        """Extends the path by adding the address| part"""
        uid = self.obj.get_uid()
        h, addr = self.obj.addr.split('//')
        path = '{}//{}:{}@{}|{}'.format(h,
                                        self.obj.user, self.obj.password, addr, uid)
        return path

    def isopen(self):
        """Returns both if the remote file is opened and if the connection is still valid"""
        try:
            r = self.obj.isopen()
        except:
            return False
        return r

    def connect(self):
        return self.obj.connect()

    def reopen(self):
        """Do nothing on remote objects!"""
        return True

    def close(self):
        """Do nothing on remote objects!"""
        return True

    def __getattr__(self, path):
        if path.startswith('_') or (path in dir(self)):
            return object.__getattribute__(self, path)
        # Get the function from the object
        a = getattr(self.obj, path)
        # If the function requires a decoding, build the partial decoding
        # function
        if self.obj.decode(path):
            a = functools.partial(self._decode, a)
        return a

    def _decode(self, func, *a, **k):
        """Wrapper caller for functions which needs decoding of their return type."""
        r = func(*a, **k)
        if isinstance(r, xmlrpclib.Binary):
            r = r.data
        if isinstance(r, str):
            r = loads(r)
        return r


def getRemoteFile(address):
    """Decode address in the form http(s)://(user):(password)@host....|uid, connects to the host and 
    returns the remote file object corresponding to uid"""
    addr, uid = address.split('|')
    user, password = False, False
    if '@' in addr and addr.startswith('http'):
        cred, addr = addr.split('@')
        h, cred = cred.split('//')
        user, password = cred.split(':')
        addr = h + '//' + addr
    srv = addrConnection(addr, user, password)
    obj = getattr(srv.storage.test, uid)
    obj.connect()
    return RemoteFileProxy(obj)


def getFileProxy(filename):
    if filename.startswith('http'):
        r = getRemoteFile(filename)
    else:
        r = SharedFile(filename)
    return r
