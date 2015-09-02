#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
from misura.canon.logger import Log as logging

pyodbc = False
import pyodbc
import datetime
from time import sleep
import numpy
import platform
import os
from traceback import print_exc
from misura.canon import bitmap
from misura.client.database import ProgressBar
from misura.canon.option import ao
import convert
import functools
from PyQt4 import QtCore, QtGui
settings = QtCore.QSettings(
    QtCore.QSettings.NativeFormat, QtCore.QSettings.UserScope, 'Expert System Solutions', 'Misura 4')

badchars = ['_']


def validate_tabname(fn):
    """Purifica un table name da tutti i caratteri potenzialmente invalidi"""
    if getattr(fn, 'toUtf8', False):
        fn = fn.toUtf8()
    fn = unicode(fn)
    fn = fn.encode('ascii', 'ignore')
    # scarta tutti i caratteri non alfanumerici
    fn = "".join(
        [x for x in fn if x.isalpha() or x.isdigit() or x not in badchars])
    return fn

# Subdefinizioni
fields_Heat = ''  # Ciclo di cottura
for i in range(1, 9):
    fields_Heat += 'Salita%i, TempMax%i, Stasi%i, ' % (i, i, i)

# intervalli
fields_Intervalli = 'Tipo_Salita, Inizio, Intervallo, Fine, Inizio1, Intervallo1, Fine1, '
fields_Intervalli += 'Intervallo2, Fine2, Intervallo3, Fine3, '

fields_Data = 'Posizione, '  # dati acquisiti
for p in '_SX', '_DX':
    fields_Data += 'Sint%s, Angolo%s, Rapporto%s, Area%s, ' % (p, p, p, p)
fields_Data += 'Temp, Tempo, Larghezza, Larghezza2,Colonna01,Colonna02'

fields_Termodil = ''
for i in range(1, 4):
    fields_Termodil += 'Termodil%i, ' % (i)
for i in range(1, 4):
    fields_Termodil += 'Termodil%i_Exp, ' % (i)

# Definizione di una riga della tabella PROVE (impostazioni della prova)
fields_PROVE = 'IDProve, Data, Desc_Prova, Tipo_Prova, Classe, ' + fields_Intervalli + \
    'Tempo_Totale, Tempo_Parziale, Note, Temp_Sint, Temp_Rammoll, Temp_Sfera, ' +\
    'Temp_Mezza_Sfera, Temp_Fusione, ' + fields_Termodil +\
    'Inizio_Sint , Indice_Rammoll, ' + fields_Heat + \
    'Pb, ti, td, Fattore, Left_Margin, Right_Margin, Top_Margin, Bottom_Margin, FireFree'
fields_PROVE = fields_PROVE.replace(' ', '').split(',')
# Definizione di una riga della tabella IMMAGINI (dati acquisiti)
fields_IMMAGINI = 'IDProve, IDImmagini, Numero_Immagine, ' + fields_Data
fields_IMMAGINI = fields_IMMAGINI.replace(' ', '').split(',')


class enumTipoProva:
    All = -1
    ProvinoSingolo = 0
    ProvinoDoppioCompleto = 1
    ProvinoDoppioParziale = 2
    SoloImmagini = 3
    Impasto = 4
    CurvaCorrezione = 5
    Dilatometro = 6
    CorrezioneDilatometro = 7
    DilatometroVerticale = 8
    DilatometroOrizzontale = 9
    Calibrazione = 10
    DropAnalysis = 11
    Flessimetro = 12
    Rodaggio = 13
    DTA = 15
    FSE = 16  # ?
    ProvinoR = 110
    ProvinoL = 111

etp = enumTipoProva()


def getInstrumentName(tp):
    """Converts Misura3 test type into misura instrument type name"""
    if tp in [0, 1, 2, 3, 4, 110, 111]:
        return 'hsm'
    if tp in [6, 7, 9]:
        return 'horizontal'
    if tp == etp.DilatometroVerticale:
        return 'vertical'
    if tp in [5, 10, 12]:
        return 'flex'
    if tp == etp.Rodaggio:
        return 'kiln'
    if tp == etp.DTA:
        return 'dta'


class fieldIMG:

    def __init__(self):
        for i, c in enumerate(fields_IMMAGINI):
            setattr(self, c, i)

    def __call__(self, n):
        return fields_IMMAGINI[n]
fimg = fieldIMG()


class fieldPRV:

    def __init__(self):
        for i, c in enumerate(fields_PROVE):
            setattr(self, c, i)

    def __call__(self, n):
        return fields_PROVE[n]
fprv = fieldPRV()


def getHeaderCols(tt, tcode='', all=False):
    """Selects and returns the appropriate columns and their headers"""
    global etp, fimg
    logging.debug('%s %s %s', 'getHeaderCols', tt, tcode)
    # DILATOMETRY
    h = ['t', 'T']
    c = [fimg.Tempo, fimg.Temp]
    if tt in [etp.DilatometroVerticale,  etp.DilatometroOrizzontale, etp.Calibrazione]:
        h += ['Dil', 'S', 'camA', 'camB', 'P', 'Mov']
        c += [fimg.Sint_SX, fimg.Rapporto_DX, fimg.Angolo_SX,
              fimg.Rapporto_SX,  fimg.Angolo_DX, fimg.Posizione]
    elif tt in [etp.Dilatometro, etp.CorrezioneDilatometro, etp.Impasto, etp.CurvaCorrezione]:
        h += ['Dil']
        c += [fimg.Sint_SX]

    # FLEX
    elif tt in [etp.Flessimetro]:
        h += ['Flex', 'S', 'camA', 'P', 'Mov']
        c += [fimg.Sint_SX, fimg.Rapporto_DX,
              fimg.Sint_DX, fimg.Angolo_DX, fimg.Posizione]

    # HSM
    elif tt in [etp.ProvinoSingolo, etp.DropAnalysis]:
        h += ['Sint', 'Ang', 'Ratio', 'Area', 'S', 'P', 'Width', 'Softening']
        c += [fimg.Sint_SX, fimg.Angolo_SX, fimg.Rapporto_SX, fimg.Area_SX,
              fimg.Rapporto_DX, fimg.Angolo_DX, fimg.Larghezza, fimg.Colonna01]
    elif tt == etp.ProvinoR or (tt == etp.ProvinoDoppioCompleto and tcode.endswith('R')):
        h += ['Sint', 'Ang', 'Ratio', 'Area', 'Width', 'Softening']
        c += [fimg.Sint_DX, fimg.Angolo_DX, fimg.Rapporto_DX,
              fimg.Area_DX, fimg.Larghezza2, fimg.Colonna02]
    elif tt == etp.ProvinoL or (tt == etp.ProvinoDoppioCompleto and tcode.endswith('L')):
        h += ['Sint', 'Ang', 'Ratio', 'Area', 'Width', 'Softening']
        c += [fimg.Sint_SX, fimg.Angolo_SX, fimg.Rapporto_SX,
              fimg.Area_SX, fimg.Larghezza, fimg.Colonna01]

    # OTHER
    elif tt in [etp.Rodaggio]:
        h += ['S', 'P']
        c += [fimg.Angolo_DX, fimg.Rapporto_DX]
    elif tt == etp.FSE:
        h = ['t', 'W', 'Flex', 'Disp']
        c += [fimg.Rapporto_SX, fimg.Sint_SX]
    elif tt == etp.DTA:
        h += ['DTA', 'S', 'P']
        c += [fimg.Sint_SX, fimg.Rapporto_DX, fimg.Angolo_DX]
    if all:
        h1 = []
        for i, f in enumerate(fields_IMMAGINI):
            if i not in c:
                h1.append(f)
            else:
                j = c.index(i)
                h1.append(h[j])
        c = range(len(fields_IMMAGINI))
        h = h1
    return h, c


def getPlotCols(tt):
    cols = (3, )
    if tt in [etp.Rodaggio]:
        cols = (3, 4)
    elif tt == etp.FSE:
        cols = (2, 3, 4)
    return cols


def getHeatingCycle(entry):
    """Translate heating cycle expressed as Ramp, Temp, Stasis in a PROVE entry, 
    into misura [t,T,S] list format"""
    out = [[0, 0]]
    addt = 0
    for i in range(1, 9):
        s = 'Salita%i,TempMax%i,Stasi%i' % (i, i, i)
        R, T, S = s.split(',')
        R = entry[getattr(fprv, R)]
        T = entry[getattr(fprv, T)]
        S = entry[getattr(fprv, S)]
        if None in [R, T]:
            break
        t0, T0 = out[-1]
        R = R * numpy.sign(T - T0)
        t = float(t0 + 60. * (T - T0) / R)
        if i == 1 and t == 0:
            addt = 1
        t += addt
        out.append([t, T])
        if S == None:
            continue
        if S > 0:
            out.append([t + 60. * S, T])
    return out


shm4 = {'Temp_Sint': 'Sintering',
        'Temp_Rammoll': 'Softening',
        'Temp_Sfera': 'Sphere',
        'Temp_Mezza_Sfera': 'HalfSphere',
        'Temp_Fusione': 'Melting'}
shm4d = {'Sintering': 'Sintering point',
         'Softening': 'Softening point',
         'Sphere': 'Sphere point',
         'HalfSphere': 'Half sphere point',
         'Melting': 'Melting point'}


def getCharacteristicShapes(test, cols):
    """Returns the characteristic shapes of a test supporting them"""
    sh = {}
    if test[fprv.Tipo_Prova] not in [etp.ProvinoSingolo, etp.ProvinoR, etp.ProvinoL, etp.ProvinoDoppioCompleto]:
        return sh
    vt = numpy.array(cols[fimg.Tempo]).astype('float')
    vT = numpy.array(cols[fimg.Temp]).astype('float')
    logging.debug('%s', vT)
    for i, name in enumerate('Temp_Sint,Temp_Rammoll,Temp_Sfera,Temp_Mezza_Sfera,Temp_Fusione'.split(',')):
        r = test[getattr(fprv, name)]
        if r == None:
            continue
        # Point as temperature
        if r > 0:
            v = vT  # Search on temp. vector
        # Point as -time
        else:
            r = -r 	# Turn positive
            v = vt  # Search on time vector
        d = numpy.abs(v - r)
        idx = numpy.where(d == d.min())[0][0]
        idx = int(idx)
        logging.debug('%s %s %s', 'Where:', r, idx)
        if idx == 0:
            t = 'None'
            T = 'None'
            point = 'None'
            idx = 'None'
        else:
            t = float(vt[idx])
            T = float(vT[idx])
        hnd = shm4[name]
        d = shm4d[hnd]
        ao(sh, hnd, 'Meta', {
           'time': t, 'temp': T, 'point': idx, 'value': 'None'}, d, priority=100 + i)
    logging.debug('%s', sh)
    return sh


class TestListModel(QtCore.QAbstractTableModel):

    """Modello di dati per la tabella PROVE, contenente la lista di tutte le prove presenti nel database."""

    def __init__(self):
        QtCore.QAbstractTableModel.__init__(self)
        self.tests = []
        self.header = fields_PROVE

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.tests)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.tests[0])

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        if role == QtCore.Qt.DisplayRole:
            obj = self.tests[index.row()]
            if len(obj) <= index.column():
                return 0
            obj = obj[index.column()]
            # Converto in stringa se l'oggetto è datetime
            if type(obj) == type(datetime.datetime(1, 2, 3)):
                if obj.year > 1900:
                    obj = obj.strftime('%d %b %Y')
            return obj

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return None
        if role == QtCore.Qt.DisplayRole:
            return self.header[section]

    def setTests(self, tests):
        self.tests = tests
        QtCore.QAbstractTableModel.reset(self)


class TestsTable(QtGui.QTableView):

    """Visualizzazione tabellare delle prove contenute nel database."""

    def __init__(self, path='', parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.path = path
        self.curveModel = TestListModel()
        self.setModel(self.curveModel)
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionModel(self.selection)
        self.setColumnWidth(0, 45)
        self.setColumnWidth(1, 50)
        self.setColumnWidth(2, 350)


def getConnectionCursor(path):
    if 'Linux' in platform.platform():
        # FIXME: Molti valori completamente sballati dalla lettura odbc.
        # Passare a SQLite3?
        cs = "DSN=M3DB"
    else:
        driver = "{Microsoft Access Driver (*.mdb)}"
        cs = "DRIVER=%s;DBQ=%s" % (driver, path)
    logging.debug('%s', cs)
    conn = pyodbc.connect(cs)
    cursor = conn.cursor()
    return conn, cursor


def getImageCode(code):
    code = code.decode('ascii', 'replace').split('\x00')[0].split('?')[0]
    code = str(code)
    try:
        int(code[-1])
    except:
        code = code[:-1]
    return code


class TestDialog(QtGui.QWidget):

    """Dialogo per la visualizzazione delle prove contenute in un database Misura3."""
    format = 'm3'  # Do not do image format decompression while converting
    img = True  # Require images in the produced file
    keep_img = True  # Keep images in the produced file
    force = True  # Update existing files

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

        # Mostra opzioni importazione
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
#		self.connect(self.table, QtCore.SIGNAL('doubleClicked(QModelIndex)'), self.select)
        self.connect(
            self.table, QtCore.SIGNAL('entered(QModelIndex)'), self.select)
        self.connect(
            self.table, QtCore.SIGNAL('clicked(QModelIndex)'), self.preview)

    def getPath(self):
        path = settings.value('/Misura3Archive', None)
        if path == None or not os.path.exists(path):
            logging.debug('%s %s', 'path does not exist', path)
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
            print_exc()
        self.DB.setText(path)
        self.emit(QtCore.SIGNAL('changedDB(QString)'), path)

    def resetList(self, *args):
        self.cursor.execute("select * from PROVE")
        tests = self.cursor.fetchall()
        self.table.curveModel.setTests(tests)
        self.table.resizeRowsToContents()

    def setFilterType(self, idx):
        tt = self.filterType.itemData(idx)
        logging.debug('%s %s', 'Selecting', tt)
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

    def convert(self, path):
        path = str(path)
        dbpath, idprove = path.split('|')
        outdir = os.path.dirname(dbpath)
        outdir = os.path.join(outdir, 'm4')
        if not os.path.exists(outdir):
            os.mkdir(outdir)
        progress = ProgressBar(
            'Converting to misura file format', dbpath, 'Running')
        progress.bar.setValue(0)
        progress.show()
        progress.connect(
            progress, QtCore.SIGNAL('jobs(int)'), progress.bar.setMaximum)
        progress.connect(
            progress, QtCore.SIGNAL('job(int)'), progress.bar.setValue)
        fsignal = functools.partial(progress.emit, QtCore.SIGNAL('job(int)'))
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

        outpath = convert.convert(dbpath, idprove, outdir,
                                  force=self.force,
                                  img=self.img,
                                  keep_img=self.keep_img,
                                  format=self.format,
                                  signal=fsignal)
        logging.debug('%s %s', 'exported to ', outdir)
        progress.hide()
        progress.close()
        del progress
        self.emit(QtCore.SIGNAL('imported(QString)'), outpath)
        return outpath

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
            logging.debug('%s %s', 'importing test: ', prova)
            self.tname = validate_tabname(prova[2])
            imported = self.path + '|' + str(prova[0])
            outpath = self.convert(imported)
            self.emit(QtCore.SIGNAL('select(QString)'), outpath)

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
        dir = os.path.dirname(str(self.path)) + '/' + code + '/' + code + 'H'
        self.cursor.execute(
            "select * from IMMAGINI where IDProve = '%s'" % code)
        self.strip.dmodel.setPathData(dir, self.cursor.fetchall())
        self.strip.show()


class ImagePreviewModel(QtCore.QAbstractTableModel):

    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.dat = []
        self.path = ''

    def setPathData(self, path, data):
        self.dat = []
        self.path = ''
        if not os.path.exists(os.path.dirname(path)):
            logging.debug('%s %s', 'Path does not exists', path)
            QtCore.QAbstractTableModel.reset(self)
            return
        self.dat = data
        self.path = path
        QtCore.QAbstractTableModel.reset(self)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.dat)

    def rowCount(self, index=QtCore.QModelIndex()):
        return 1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() <= self.rowCount()):
            return 0
        if role == QtCore.Qt.DisplayRole:
            code = os.path.basename(self.path)
            num = self.dat[index.column()][fimg.Numero_Immagine]
            img = '%s.%03i' % (self.path, int(num))
            return img

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                h = u'%.1f°C' % self.dat[section][fimg.Temp]
                return h
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

maxImageCacheSize = 500


class ImageDecoder(QtCore.QThread):

    def __init__(self, parent=None, maxWidth=100):
        QtCore.QThread.__init__(self, parent)
        self.names = [False] * maxImageCacheSize
        self.images = {}
        self.queue = []
        self.maxWidth = maxWidth

    def cache(self, path):
        if path in self.names:
            return self.images[path]
        pix = QtGui.QImage()
        img = open(path, 'rb').read()
        img = bitmap.decompress(img)
        pix.loadFromData(img, 'BMP')
        pix = pix.scaledToWidth(self.maxWidth)
        self.names.append(path)
        self.images[path] = pix
        # keep image cache length
        d = self.names.pop(0)
        if d:
            del self.images[d]
        return pix

    def append(self, path, index):
        self.queue.append([path, index])

    def get(self, path):
        if not path in self.names:
            return False
        return self.images[path]

    def run(self):
        while True:
            if len(self.queue) == 0:
                sleep(.1)
                continue
            # Always read last requested data
            path, index = self.queue.pop(-1)
            self.cache(path)
            model = index.model()
            self.emit(QtCore.SIGNAL('cached(QModelIndex)'), index)


class ImagePreviewDelegate(QtGui.QItemDelegate):

    """Delegato per la visualiazzazione delle celle nella tabella immagini"""

    def __init__(self, parent=None):
        QtGui.QItemDelegate.__init__(self, parent)
        self.maxWidth = 100
        self.decoder = ImageDecoder(self)
        self.connect(
            self.decoder, QtCore.SIGNAL('cached(QModelIndex)'), parent.update)
        self.decoder.start()

    def paint(self, painter, option, index):
        """Ricezione e disegno delle immagini"""
        model = index.model()
        path = model.data(index)
        img = self.decoder.get(path)

        if img:
            pix = QtGui.QPixmap.fromImage(img)
            painter.save()
            painter.translate(option.rect.x(), option.rect.y())
            painter.drawPixmap(0, 0, pix.width(), pix.height(), pix)
            painter.restore()
            self.parent().resizeRowToContents(index.row())
        else:
            self.decoder.append(path, index)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.maxWidth, self.maxWidth)

    def zoom(self, width=100):
        self.maxWidth = width
        self.parent().resizeRowsToContents()
        self.parent().resizeColumnsToContents()

    def zoomIn(self):
        self.zoom(self.maxWidth * 1.1)

    def zoomOut(self):
        self.zoom(self.maxWidth * 0.9)


class ImagePreview(QtGui.QTableView):

    """Table for previewing images contained in the test."""

    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        self.dmodel = ImagePreviewModel(self)
        self.setModel(self.dmodel)
        self.setItemDelegate(ImagePreviewDelegate(self))
        self.selection = QtGui.QItemSelectionModel(self.model())
        self.setSelectionModel(self.selection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.menu = QtGui.QMenu(self)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
        self.zoomIn = self.menu.addAction(
            'Zoom In', self.itemDelegate().zoomIn)
        self.zoomOut = self.menu.addAction(
            'Zoom Out', self.itemDelegate().zoomOut)
        self.zoomOk = self.menu.addAction(
            'Zoom Reset', self.itemDelegate().zoom)
        self.setMinimumSize(0, 150)

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))


if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    dia = QtGui.QDialog()
    lay = QtGui.QVBoxLayout()
    dia.setLayout(lay)
    lay.addWidget(TestDialog())
    dia.exec_()
    app.exec_()
