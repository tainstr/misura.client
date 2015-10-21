#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui, QtCore
from . import _
from confwidget import ClientConf
from live import registry
from misura.canon.version import __version__ as canon_version
from version import __version__ as client_version

about="""
<h1> Misura &trade;</h1>
<p>misura.client version: {}<br/>
misura.canon version: {}</p>
<p>Copyright TA Instruments / Waters LLC</p>
<p><small>See public source code repository page for licensing information</small></p>
""".format(client_version, canon_version)

class HelpMenu():

    def add_help_menu(self):
        self.help = self.addMenu('Help')
        self.help.addAction(_('Client configuration'), self.showClientConf)
        self.help.addAction(_('Documentation'), self.showDocSite)
        self.help.addAction(_('Pending operations'), self.showTasks)
        self.help.addAction(_('About'), self.showAbout)

    def hide_help_menu(self):
        self.help.menuAction().setVisible(False)


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

    def showAbout(self):
        label = QtGui.QLabel()
        label.setText(about)
        lay = QtGui.QHBoxLayout()
        lay.addWidget(label)
        dia = QtGui.QDialog()
        dia.setLayout(lay)
        dia.exec_()
