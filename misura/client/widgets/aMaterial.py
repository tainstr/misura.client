#!/usr/bin/python
# -*- coding: utf-8 -*-
from .. import _
from misura.client.widgets.active import *
from aString import aString
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)


class aMaterial(aString):

    def __init__(self, server, path,  prop, parent=None, extended=False):
        aString.__init__(
            self, server, path,  prop, parent=None, extended=False)
        matlist = QtGui.QPushButton('...')
        self.lay.addWidget(matlist)
        self.connect(matlist, QtCore.SIGNAL('clicked()'), self.listMaterials)
        self.set_enabled()

    def listMaterials(self):
        mats = self.server.storage.listMaterials()
        logging.debug(mats)
        mat = QtGui.QInputDialog.getItem(self, "Select the material name",
                                         "Select an already used material name or input a new one.",
                                         QtCore.QStringList(mats))
        if not mat[1]:
            return
        self.browser.setText(str(mat[0]))
        self.set()
