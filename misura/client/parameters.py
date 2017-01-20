#!/usr/bin/python
# -*- coding: utf-8 -*-


import sys
import os
from time import time
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtCore
from traceback import print_exc
from os.path import expanduser

def determine_path(root=False):
    if hasattr(sys, 'frozen'):
        # for pyinstaller/py2app compatability
        resdir = os.path.dirname(os.path.abspath(sys.executable))
        if sys.platform == 'darwin':
            # special case for py2app
            resdir = os.path.join(resdir, '..', 'Resources')
        return resdir
    else:
        if root is False:
            root = __file__
        if os.path.islink(root):
            root = os.path.realpath(root)
        return os.path.dirname(os.path.abspath(root))

# Percorso dell'eseguibile
pathClient = determine_path()
logging.debug('pathClient', pathClient)
# Percorso utilizzato per immagazzinare la configurazione del client
pathConf = os.path.expanduser("~/MisuraData/conf.sqlite")
pathLang = os.path.join(pathClient, 'i18n')
logging.debug('pathLang', pathLang)
pathArt = os.path.join(pathClient, 'art')
pathUi = os.path.join(pathClient, 'ui')
logging.debug('pathArt', pathArt)
locale = QtCore.QLocale.system().name()
locale = str(locale.split('_')[0]).lower()

MAX = 10**10
MIN = -MAX

max_curve_len = 3000

experimental3to4 = True

maxImageCacheSize = 25

debug = True
