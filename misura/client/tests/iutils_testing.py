#!/usr/bin/python
# -*- coding: utf-8 -*-
import disable_print_and_logging
import os
import sys
from misura.canon.logger import Log
from PyQt4 import QtGui, QtCore
def determine_path ():
	"""Borrowed from wxglade.py"""
	try:
		root = __file__
		if os.path.islink (root):
			root = os.path.realpath (root)
		return os.path.dirname (os.path.abspath (root))
	except:
		Log.debug('%s %s', "I'm sorry, but something is wrong.")
		Log.debug('%s', "There is no __file__ variable. Please contact the author.")
		sys.exit ()
		
client_test_dir=os.path.join(determine_path())
db3_dir=os.path.join(client_test_dir,'db3')
db3_path=os.path.join(db3_dir,'test.mdb')
data_dir=os.path.join(client_test_dir,'data')
rem=None

#FIXME: client should not import utils_testing, which is a server facility. ####
#                                                                              #
# for now, we do this only to have a simple way to create a temporary shared   #
# memory. Anyway the client should not be aware of the existence of shared     #
# memory.                                                                      # 
# WE WILL REMOVE THIS AS SOON AS WE HAVE A GREEN AND FULL TESTS SUITE          #
#                                                                              #
#                                                                              #
from misura import utils_testing                                               #
#                                                                              #
################################################################################


app = QtGui.QApplication([])

win=sys.platform.startswith('win')

class Dummy(object):
	connect=lambda s: 1
	start_acquisition=connect
	
	def __init__(self,name='dummy',parent=False):
		self.dummyname=name
		self.childs={}
		self.p=parent
		
	def set(self,a,v):
		Log.debug('%s %s %s', 'Dummy.set', a, v)
		return True
		
	def copy(self):
		return self
	
	def parent(self):
		if self.p is False:
			self.p=Dummy(self.dummyname)
		return self.p
	
	def analyze(self,*foo):
		Log.debug('%s %s', 'Analyzer arguments', len(foo))
		
	def __getattr__(self, a='dummy'):
		if a=='dummyname':
			return self.dummyname
		if not self.childs.has_key(a):
			self.childs[a]=Dummy(a,parent=self)
		return self.childs[a]
		


# SIMPLE SIGNAL DEBUGGING
# Thanks to: http://stackoverflow.com/a/2063216
_oldConnect = QtCore.QObject.connect
_oldDisconnect = QtCore.QObject.disconnect
_oldEmit = QtCore.QObject.emit

def _wrapConnect(callableObject, oldConnect):
    """Returns a wrapped call to the old version of QtCore.QObject.connect"""
    @staticmethod
    def call(*args):
        callableObject(*args)
        oldConnect(*args)
    return call

def _wrapDisconnect(callableObject, oldDisconnect):
    """Returns a wrapped call to the old version of QtCore.QObject.disconnect"""
    @staticmethod
    def call(*args):
        callableObject(*args)
        oldDisconnect(*args)
    return call

def enableSignalDebugging(obj=QtCore.QObject, **kwargs):
	"""Call this to enable Qt Signal debugging. This will trap all
	connect, and disconnect calls."""
	f = lambda *args: None
	connectCall = kwargs.get('connectCall', f)
	disconnectCall = kwargs.get('disconnectCall', f)
	emitCall = kwargs.get('emitCall', f)

	def printIt(msg):
		def call(*args):
			Log.debug('%s %s', msg, args)
		return call
	obj.connect = _wrapConnect(connectCall, obj.connect)
	obj.disconnect = _wrapDisconnect(disconnectCall, obj.disconnect)
	oldEmit=obj.emit
	def new_emit(self, *args):
		Log.debug('%s %s', 'EMIT', args)
		emitCall(self, *args)
		oldEmit(self, *args)
	
	obj.emit = new_emit	

from misura.client import network
import threading

class FakeProxy(network.MisuraProxy):
	addr='https://testing/RPC'
	"""Remote server address"""
	user='test'
	"""User name"""
	password='test'
	"""User password"""
	def __init__(self,obj):
		self.remObj=obj
		self._lock=threading.Lock()
		
	def copy(self):
		return FakeProxy(self.remObj)
	
	def connect(self):
		return True
	
	def toPath(self,p):
		r=self.remObj.toPath(p)
		return FakeProxy(r)
	
	def parent(self):
		Log.debug('%s', dir(self.remObj))
		return FakeProxy(self.remObj.parent())
	
	def child(self,name):
		r=None
		cf=getattr(self.remObj,'child',False)
		if cf:
			r=self.remObj.child(name)
		if r is None:
			r=getattr(self.remObj,name)
		return FakeProxy(r)
	
	@property
	def remoteNames(self):
		return dir(self.remObj)+self.remObj.subhandlers.keys()
	
	def __call__(self, *args, **kwargs):
		return self.remObj(*args, **kwargs)
	
	def to_root(self):
		return FakeProxy(self.remObj.root)
	
def silent_remove(filename):
	if os.path.exists(filename): 
		os.remove(filename)

