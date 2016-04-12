#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui, QtCore, uic
from . import _
from .confwidget import ClientConf
from .live import registry
from misura.canon.version import __version__ as canon_version
from . import parameters
from version import __version__ as client_version
import os

about="""
<h1> Misura &trade;</h1>
<p>misura.client version: {}<br/>
misura.canon version: {}</p>
<p>Copyright TA Instruments / Waters LLC</p>
<p><small>See public source code repository page for licensing information</small></p>
""".format(client_version, canon_version)

def showAbout():
    dialog = QtGui.QDialog()
    uic.loadUi(os.path.join(parameters.pathUi, 'about_misura.ui'), dialog)
    dialog.logo_label.setScaledContents(True)
    dialog.label_client_version.setText('client: ' + client_version)
    dialog.label_canon_version.setText('canon: ' + canon_version)

    dialog.logo_label.setPixmap(QtGui.QPixmap(os.path.join(parameters.pathArt, 'logo.png')))
    dialog.setWindowIcon(QtGui.QIcon(os.path.join(parameters.pathArt, 'icon.svg')))

    dialog.exec_()


class HelpMenu():

    def add_help_menu(self, menu_bar):
        self.help = menu_bar.addMenu('Help')
        self.help.addAction(_('Client configuration'), self.showClientConf)
        self.help.addAction(_('Documentation'), self.showDocSite)
        self.help.addAction(_('Pending operations'), self.showTasks)
        self.help.addAction(_('About'), showAbout)

    def showClientConf(self):
        """Show client configuration panel"""
        self.cc = ClientConf()
        self.cc.show()

    def showDocSite(self):
        url = 'http://misura.readthedocs.org'
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def showTasks(self):
        registry.taskswg.user_show = True
        registry.taskswg.show()
