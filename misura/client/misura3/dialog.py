# -*- coding: utf-8 -*-
import os
from traceback import format_exc

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from preview import ImagePreview
from table import TestsTable
import convert
from m3db import getImageCode, getConnectionCursor, etp, validate_tabname

from ..live import registry
from misura.client import widgets

from PyQt4 import QtCore, QtGui

settings = QtCore.QSettings(
    QtCore.QSettings.NativeFormat, QtCore.QSettings.UserScope, 'Expert System Solutions', 'Misura 4')
    

class TestDialog(QtGui.QWidget):

    """Dialogo per la visualizzazione delle prove contenute in un database Misura3."""
    format = 'ImageM3'  # Do not do image format decompression while converting
    img = True  # Require images in the produced file
    keep_img = True  # Keep images in the produced file
    force = True  # Update existing files
    converter = False # File converter
    
    def __init__(self, parent=None, importOptions=True, path=False):
        global settings
        QtGui.QWidget.__init__(self, parent)
        self.setMinimumSize(600, 0)
        self.setWindowTitle('Misura3 Database Listing')
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.importAllFields = False
        self.imported = {}
        self.conn = False
        # Bottone di connessione DB
        self.DB = QtGui.QPushButton("", self)
        self.lay.addWidget(self.DB)
        self.connect(self.DB, QtCore.SIGNAL('clicked()'), self.selectDB)
        # Creazione tabella
        self.table = TestsTable(parent=self)
        self.lay.addWidget(self.table)
        self.connect(self, QtCore.SIGNAL('changedDB(QString)'), self.resetList)

        # Connessione DB
        self.path = path
        if not path:
            self.path = self.getPath()
        if not self.path:
            self.selectDB()
        else:
            self.setDB(self.path)

        # Ricerca per tipo
        self.filterType = QtGui.QComboBox(self)
        for lbl in dir(etp):
            if '_' in lbl:
                continue
            i = getattr(etp, lbl)
            self.filterType.addItem(str(lbl), i)
        self.connect(self.filterType, QtCore.SIGNAL(
            'currentIndexChanged(int)'), self.setFilterType)

        # Ricerca per stringa
        self.searchText = QtGui.QLineEdit(self)
        self.connect(self.searchText, QtCore.SIGNAL(
            'returnPressed()'), self.setSearchText)

        self.do = QtGui.QPushButton('Import')
        self.connect(self.do, QtCore.SIGNAL('clicked()'), self.select)

        # Import Options
        self.doPreview = QtGui.QCheckBox('Preview images below', self)
        self.connect(self.doPreview, QtCore.SIGNAL('clicked()'), self.preview)
        self.doPreview.setCheckState(2)

        self.doForceData = QtGui.QCheckBox('Force data update', self)
        self.doForceData.setCheckState(2)

        self.doForceImages = QtGui.QComboBox(self)
        self.doForceImages.addItem('Require images')
        self.doForceImages.addItem('Do not require images')
        self.doForceImages.addItem('Force new image conversion')
        if not self.img:
            u = 1
        if self.img and self.keep_img:
            u = 0
        if self.img and not self.keep_img:
            u = 2
        self.doForceImages.setCurrentIndex(u)

        grid = QtGui.QWidget(self)
        glay = QtGui.QGridLayout()
        grid.setLayout(glay)

        j = 0
        glay.addWidget(self.filterType, j, 0)
        glay.addWidget(self.searchText, j, 1)

        # Show import options
        if importOptions:
            j += 1
            glay.addWidget(self.doPreview, j, 0)
            glay.addWidget(self.doForceImages, j, 1)
            j += 1
            glay.addWidget(self.doForceData, j, 0)
            glay.addWidget(self.do, j, 1)
        else:
            self.doPreview.hide()
            self.doForceData.hide()
            self.doForceImages.hide()
        self.lay.addWidget(grid)

        self.strip = ImagePreview(self)
        self.strip.hide()
        self.lay.addWidget(self.strip)
        # Option to execute a full import to dictionary or only a path|id
        # import:
        self.fullImport = False
        self.connect(self.table, QtCore.SIGNAL('doubleClicked(QModelIndex)'), self.select)
#        self.connect( 
#            self.table, QtCore.SIGNAL('entered(QModelIndex)'), self.select)
        self.connect(
            self.table, QtCore.SIGNAL('clicked(QModelIndex)'), self.preview)

    def getPath(self):
        path = settings.value('/Misura3Archive', None)
        if path is None or not os.path.exists(path):
            logging.debug('path does not exist', path)
            return False
        return path

    def selectDB(self):
        """Select a new database path and open it"""
        path = QtGui.QFileDialog.getOpenFileName(
            self, "Select Misura3 Database", "C:\ESS\Misura3\db")
        settings.setValue('/Misura3Archive', path)
        self.path = path
        self.setDB(path)
        self.table.path = path
        self.table.cursor = self.cursor

    def setDB(self, path):
        """Open the database path"""
        if self.conn:
            self.conn.close()
        try:
            self.conn, self.cursor = getConnectionCursor(path)
        except:
            logging.error('setDB %',format_exc())
        self.DB.setText(path)
        self.emit(QtCore.SIGNAL('changedDB(QString)'), path)

    def resetList(self, *args):
        self.cursor.execute("select * from PROVE")
        tests = self.cursor.fetchall()
        self.table.curveModel.setTests(tests)
        self.table.resizeRowsToContents()

    def setFilterType(self, idx):
        tt = self.filterType.itemData(idx)
        logging.debug('Selecting', tt)
        self.cursor.execute("select * from PROVE where [Tipo Prova] = %i" % tt)
        tests = self.cursor.fetchall()
        self.table.curveModel.setTests(tests)

    def setSearchText(self):
        t = str(self.searchText.text()).lower()
        if len(t) < 1:
            self.resetList()
            return
        tests = self.table.curveModel.tests
        ntests = []
        for row in tests:
            if t in row[2].lower():
                ntests.append(row)
        self.table.curveModel.setTests(ntests)

    def getCode(self, row):
        prova = self.table.curveModel.tests[row]
        return getImageCode(prova[0])
        
    def done(self, pid):
        if pid != self.pid:
            return
        if self.progress_timer:
            self.progress_timer.stop()
            self.progress_timer = False
        if not self.converter:
            return
        if self.converter.progress < 100:
            logging.error('Conversion aborted', self.converter.outpath)
            self.converter.interrupt = True
            return
        logging.debug('exported to ', self.outdir)
        self.emit(QtCore.SIGNAL('imported(QString)'), self.outpath)
        self.emit(QtCore.SIGNAL('select(QString)'), self.outpath)

    def convert(self, path):
        path = str(path)
        dbpath, idprove = path.split('|')
        outdir = os.path.dirname(dbpath)
        outdir = os.path.join(outdir, 'm4')
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        self.outdir = outdir
        
        self.force = self.doForceData.isChecked()
        fi = self.doForceImages.currentIndex()

        if fi == 0:
            self.keep_img = True
            self.img = True
        elif fi == 1:
            self.img = False
            self.keep_img = True
        elif fi == 2:
            self.img = True
            self.keep_img = False
        self.pid = 'Converting to misura format: ' + idprove
        
        self.converter = convert.Converter(dbpath, self.outdir)
        self.outpath = self.converter.get_outpath(idprove, img=self.img,
                                             keep_img=self.keep_img)   
        
        self.connect(registry.tasks, QtCore.SIGNAL('sig_done(QString)'), self.done)
        run = widgets.RunMethod(self.converter.convert, frm=self.format)
        run.step = 100        
        run.pid = self.pid
        QtCore.QThreadPool.globalInstance().start(run)
        self.progress_timer = QtCore.QTimer(self)
        self.progress_timer.setInterval(300)
        self.connect(self.progress_timer, QtCore.SIGNAL('timeout()'), self.update_progress)
        self.progress_timer.start()
        
    def update_progress(self):
        if not self.converter:
            self.progress_timer.stop()
            return
        registry.tasks.job(self.converter.progress, self.pid)
        QtGui.qApp.processEvents()

    def select(self, idx=False):
        """Import selected test/tests"""
        sel = self.table.selectedIndexes()
        done = []
        for idx in sel:
            i = idx.row()
            if i in done:
                continue
            done.append(i)
            prova = self.table.curveModel.tests[i]
            logging.debug('importing test: ', prova)
            self.tname = validate_tabname(prova[2])
            imported = self.path + '|' + str(prova[0])
            self.convert(imported)
            

    def preview(self, idx=False):
        if not self.doPreview.isChecked():
            self.strip.hide()
            return
        if idx is False:
            return
        i = idx.row()
        prova = self.table.curveModel.tests[i]
        if prova[3] not in [etp.ProvinoSingolo, etp.ProvinoDoppioCompleto, etp.ProvinoDoppioParziale, etp.SoloImmagini]:
            self.strip.hide()
            return
        code = self.getCode(i)
        image_dir = os.path.dirname(str(self.path)) + '/' + code + '/' + code + 'H'
        self.cursor.execute(
            "select * from IMMAGINI where IDProve = '%s'" % code)
        rows = self.cursor.fetchall()
        self.strip.dmodel.setPathData(image_dir, rows)
        self.strip.show()
        print 'Showing images from',len(rows),image_dir

