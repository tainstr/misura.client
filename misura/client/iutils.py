#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Standard interface construction utilities"""
from PyQt4 import QtGui, QtCore
import os
import sys
from misura.canon.logger import Log as logging
from time import sleep
import signal

import parameters as  params
import network 
from live import registry # needed for initialization
from clientconf import confdb, settings
signal.signal(signal.SIGINT, signal.SIG_DFL) # cattura i segnali

app=None
translators=[]

network.manager.connect(network.manager,
	QtCore.SIGNAL('connected(QString,QString,QString,bool)'),
	confdb.mem_server)
network.manager.connect(network.manager,
	QtCore.SIGNAL('found(QString)'),
	confdb.found_server)
network.manager.connect(network.manager,
	QtCore.SIGNAL('lost(QString)'),
	confdb.rem_server)

net=network.manager
def connectNetwork():
	global net
	prev=str(settings.value('/ServerAddress'))
	net.connect(net, QtCore.SIGNAL('connected()'), saveAddress)
	if len(prev.split(':'))==2:
		s=network.ServerInfo(fullname='previous')
		s.fromAddr(prev)
		s.user=settings.value('/ServerUser')
		s.password=settings.value('/ServerPassword')
		s.name=settings.value('/ServerName')
		s.host='previous'
		net.servers['previous']=s
		
def saveAddress():
	settings.setValue('/ServerAddress', net.addr)
	settings.setValue('/ServerUser', net.user)
	settings.setValue('/ServerPassword', net.password)
#	settings.setValue('/ServerName', net.name)

def initClient():
	global translators, app,  confdb, registry
	app = QtGui.QApplication.instance()
	app.connect(app, QtCore.SIGNAL('aboutToQuit()'), closeApp)
	app.connect(app, QtCore.SIGNAL('lastWindowClosed()'), closeApp)
	initTranslations(app)
	initNetwork()
	initRegistry()
	
def initTranslations(app):
	appTranslator=QtCore.QTranslator()
	pathLang=os.path.join(params.determine_path(),'i18n')
	logging.debug('%s %s', 'initClient: pathLang', pathLang)
	lang=confdb['lang']
	if lang=='sys': lang=params.locale
	logging.debug('%s', "misura_"+lang)
	if appTranslator.load("misura_"+lang, pathLang):
		logging.debug('%s', 'installing translator')
		app.installTranslator(appTranslator)
		# devo creare un riferimento permanente onde evitare che il QTranslator vada distrutto
		translators.append(appTranslator)
	else:
		logging.debug('%s', 'translations not available')
	
def initNetwork():
	"""Start zeroconf network scanner - deprecated"""
	#network.manager.start()
	
def initRegistry():
	# Avvio il registro
	registry.set_manager(network.manager)
	registry.toggle_run(True)
	
def closeRegistry():
	logging.debug('iutils.closeRegistry')
	registry.toggle_run(False)
	sleep(1)
	registry.terminate()

stylesheet=""

def initApp(name='misura', org="Expert System Solutions", domain="expertsystemsolutions.it",client=True,qapp=False):
	"""Inzializzazione generale di una applicazione misura Client.
	Creazione QApplication, installazione dei traduttori"""
	global translators, app
	app=qapp
	if not app:
		app = QtGui.QApplication(sys.argv)
	app.connect(app, QtCore.SIGNAL('aboutToQuit()'), closeApp)
	app.setOrganizationName(org)
	if domain:
		app.setOrganizationDomain(domain)
	app.setApplicationName(name)
	app.setStyleSheet(stylesheet)
	if client: initClient()

def closeApp():
	"""Operazioni di pulizia prima della chiusura"""
	# Save configuration
	logging.debug('Closing App')
	confdb.save()
	closeRegistry()
	network.manager.scan=False
	sleep(1)
	network.manager.terminate()
	network.closeConnection()

def xcombinations(items, n):
	# Origine:
	# http://code.activestate.com/recipes/190465/
	if n==0: yield []
	else:
		for i in xrange(len(items)):
			for cc in xcombinations(items[:i]+items[i+1:],n-1):
				yield [items[i]]+cc
from scipy import sqrt
def plotPalette(n):
	"""Generatore di tavolozza massimo contrasto per i grafici."""
	l=n**(1/3.)+2 # arrotondamento per eccesso
	l=int(l)
	v=range(255, 0, int(-255/(l)))
	v.append(0)
	cc=[]
	for c in xcombinations(v, 3):
		cc.append(c)
	r=[]
	for i in range(2*n):
		if i % 2==0: i=i//2
		else: i=-i
		r.append(cc[i])
	return r

def isProxy(obj):
	r=repr(obj)
	return ( 'AutoProxy' in r ) or ( 'MisuraProxy' in r )


def guessNextName(name):
	"""Add +1 to a name composed of string+integer"""
	v=list(name)
	if len(v)<1: return '', 0, '0'
	dg=set('0123456789')
	if v[-1] not in dg: return name, 1, name+'1'
	n=[]
	while len(v)>0:
		c=v.pop()
		if c in dg: n.append(c)
		else:
			v.append(c)
			break
	n.reverse()
#	print n, v
	n=int(''.join(n))
	name=''.join(v)
	return name, n, name+str(n+1)

def namingConvention(path,splt='/'):
	"""If path pertains to a sample property, returns its sample number and option name"""
	if not splt+'sample' in path:
		return path,None
	if path.endswith(splt): path=path[:-1]
	v=path.split(splt)
	# Find sample number
	for i,d in enumerate(v):
		if not d.startswith('sample'):
			continue
		idx=int(d[6:])
		break
	# Find option name
	# If it is properly a sample option
	if v[-2].startswith('sample'):
		return v[-1],idx
	# Otherwise, return path starting from sample
	return splt.join(v[i:]),idx
def num_to_string(val):
	if type(val)==type(''): 
		return val
	a=abs(val)
	if 0.01 < a < 1000 or a<10**-14:
		s='%.2f' % val
	elif 1000<a<10000:
		s='%.1f' % val
	else:
		s='%.2E' % val
	return s

def getOpts():
	"""-h Address
	-o Object
	Returns a dictionary with defaults or expressed variables.
	"""
	import sys, getopt
	opts, args=getopt.getopt(sys.argv[1:], 'h:o:')
	logging.debug('%s %s', opts, args)
	h='https://admin:admin@localhost:3880/RPC'
	o='/'
	r={'-h':False, '-o':False}
	for opt, val in opts:
		if opt=='o':
			if not val.startswith('/'): val='/'+val
			if not val.endswith('/'): val+='/'
		if opt=='h':
			if not h.startswith('https://'):
				val='https://'+val
			if not h.endswith('/RPC'):
				val+='/RPC'
		r[opt]=val
	return r

def get_plotted_tree(base,m=False):
	"""Builds a dictionary for the base graph:
		m => {'plot': {plotpath: dsname,...},
			  'dataset': {dsname: plotpath,...},
			  'axis':{axispath:[ds0,ds1,...]},
			  'sample':[smp0,smp1,...]}"""
	if m is False:
		m={'plot':{},'dataset':{},'axis':{},'sample':[]}
	for wg in base.children:
		# Recurse until I find an xy object
		if wg.typename=='page':
			m=get_plotted_tree(wg,m)
		elif wg.typename=='graph':
			m=get_plotted_tree(wg,m)
		elif wg.typename=='xy':
# 			print 'get_plotted_tree found xy',wg.path
			dsn=wg.settings.yData
			ds=wg.document.data.get(dsn,False)
			if ds is False: 
# 				print 'get_plotted_tree: dataset not found!',ds
				continue
			if not m['plot'].has_key(wg.path):
				m['plot'][wg.path]=[]
			m['plot'][wg.path].append(dsn)
			if not m['dataset'].has_key(dsn):
				m['dataset'][dsn]=[]
			m['dataset'][dsn].append(wg.path)
			if not '/sample' in dsn:
# 				print 'get_plotted_tree: skipping sample',dsn
				continue
			smp=getattr(ds,'m_smp',False)
			if not smp:
# 				print 'get_plotted_tree: sample not assigned',dsn 
				continue
			if smp.ref: 
# 				print 'get_plotted_tree: sample is reference',smp.ref,smp
				continue
			m['sample'].append(smp)
			# Save the dataset under its axis key
			axpath=wg.parent.path+'/'+wg.settings.yAxis
			if not m['axis'].has_key(axpath):
				m['axis'][axpath]=[]
			m['axis'][axpath].append(dsn)
		elif wg.typename in ('axis','axis-function'):
# 			print 'get_plotted_tree found axis',wg.path
			if wg.settings.direction!='vertical': continue
			if not m['axis'].has_key(wg.path):
				m['axis'][wg.path]=[]
	return m
