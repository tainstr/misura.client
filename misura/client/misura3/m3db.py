#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
import platform
import os
from traceback import print_exc
import datetime
from time import sleep


pyodbc = False
try:
    import pyodbc
except:
    print_exc()
    print 'Misura3 import is not available. Install pyodbc.'

import numpy

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.option import ao



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
    if tp in [6, 7, 9, 10]:
        return 'horizontal'
    if tp == etp.DilatometroVerticale:
        return 'vertical'
    if tp in [5, 12]:
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
    logging.debug('getHeaderCols', tt, tcode)
    # DILATOMETRY
    h = ['t', 'T']
    c = [fimg.Tempo, fimg.Temp]
    if tt in [etp.DilatometroVerticale,  etp.DilatometroOrizzontale, etp.Calibrazione]:
        h += ['d', 'S', 'camA', 'camB', 'P', 'Mov']
        c += [fimg.Sint_SX, fimg.Rapporto_DX, fimg.Angolo_SX,
              fimg.Rapporto_SX,  fimg.Angolo_DX, fimg.Posizione]
    elif tt in [etp.Dilatometro, etp.CorrezioneDilatometro, etp.Impasto, etp.CurvaCorrezione]:
        h += ['d']
        c += [fimg.Sint_SX]

    # FLEX
    elif tt in [etp.Flessimetro]:
        h += ['d', 'S', 'camA', 'P', 'Mov']
        c += [fimg.Sint_SX, fimg.Rapporto_DX,
              fimg.Sint_DX, fimg.Angolo_DX, fimg.Posizione]

    # HSM
    elif tt in [etp.ProvinoSingolo, etp.DropAnalysis]:
        h += ['h', 'ang', 'eqhw', 'A', 'S', 'P', 'w', 'soft']
        c += [fimg.Sint_SX, fimg.Angolo_SX, fimg.Rapporto_SX, fimg.Area_SX,
              fimg.Rapporto_DX, fimg.Angolo_DX, fimg.Larghezza, fimg.Colonna01]
    elif tt == etp.ProvinoR or (tt == etp.ProvinoDoppioCompleto and tcode.endswith('R')):
        h += ['h', 'ang', 'eqhw', 'A', 'w', 'soft']
        c += [fimg.Sint_DX, fimg.Angolo_DX, fimg.Rapporto_DX,
              fimg.Area_DX, fimg.Larghezza2, fimg.Colonna02]
    elif tt == etp.ProvinoL or (tt == etp.ProvinoDoppioCompleto and tcode.endswith('L')):
        h += ['h', 'ang', 'eqhw', 'A', 'w', 'soft']
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
        if R==0:
            logging.error('Zero rate:', i, R,T,S)
            break
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
    logging.debug(vT)
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
        logging.debug('Where:', r, idx)
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
           'time': t, 'temp': T, 'value': 'None'}, d, priority=100 + i)
    return sh


def getConnectionCursor(path):
    if 'Linux' in platform.platform():
        # FIXME: Molti valori completamente sballati dalla lettura odbc.
        # Passare a SQLite3?
        cs = "DSN=M3DB"
    else:
        driver = "{Microsoft Access Driver (*.mdb)}"
        cs = "DRIVER=%s;DBQ=%s" % (driver, path)
    logging.debug(cs)
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


