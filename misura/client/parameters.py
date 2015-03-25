#!/usr/bin/python
# -*- coding: utf-8 -*-

# 0=always visible; 1=user ; 2=expert ; 3=advanced ; 4=technician ; 5=developer; 6=never visible
configuration_level=5
import sys
import os
from time import time
from PyQt4 import QtCore
from traceback import print_exc

def determine_path ():
	if hasattr(sys, 'frozen'):
		# for pyinstaller/py2app compatability
		resdir = os.path.dirname(os.path.abspath(sys.executable))
		if sys.platform == 'darwin':
			# special case for py2app
			resdir = os.path.join(resdir, '..', 'Resources')
		return resdir
	else:
		root = __file__
		if os.path.islink (root):
			root = os.path.realpath (root)
		return os.path.dirname (os.path.abspath (root))

# Percorso dell'eseguibile
pathClient=determine_path()
print 'pathClient',pathClient
# Percorso utilizzato per immagazzinare la configurazione del client
pathConf=os.path.join(pathClient, 'conf.sqlite')
pathLang=os.path.join(pathClient,'i18n')
print 'pathLang',pathLang
pathArt=os.path.join(pathClient,'art' )
print 'pathArt',pathArt
locale=QtCore.QLocale.system().name()
locale=str(locale.split('_')[0]).lower()
linguist=False

MAX=10**10
MIN=-MAX

max_curve_len=3000

experimental3to4=True

maxImageCacheSize=25

debug=True


