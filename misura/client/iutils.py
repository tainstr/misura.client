#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Standard interface construction utilities"""
import os
import sys
import collections
from collections import OrderedDict, defaultdict
from time import sleep
import signal
from pickle import loads, dumps

import veusz.dialogs.exceptiondialog
veusz.dialogs.exceptiondialog._emailUrl = None

from PyQt4 import QtGui, QtCore

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)

import parameters as params
import network
from live import registry  # needed for initialization
from clientconf import confdb, settings, activate_plugins
signal.signal(signal.SIGINT, signal.SIG_DFL)  # cattura i segnali
import veusz.utils
from veusz import document


app = None
translators = []

network.manager.connect(network.manager,
                        QtCore.SIGNAL(
                            'connected(QString,QString,QString,QString,QString,QString,bool)'),
                        confdb.mem_server)
network.manager.connect(network.manager,
                        QtCore.SIGNAL('found(QString)'),
                        confdb.found_server)
network.manager.connect(network.manager,
                        QtCore.SIGNAL('lost(QString)'),
                        confdb.rem_server)

net = network.manager


def initClient():
    global translators, app,  confdb, registry
    app = QtGui.QApplication.instance()
    app.connect(app, QtCore.SIGNAL('aboutToQuit()'), closeApp)
    app.connect(app, QtCore.SIGNAL('lastWindowClosed()'), closeApp)
    initTranslations(app)
    initNetwork()
    initRegistry()
    activate_plugins(confdb)


def initTranslations(app):
    appTranslator = QtCore.QTranslator()
    pathLang = os.path.join(params.determine_path(), 'i18n')
    logging.debug('initClient: pathLang', pathLang)
    lang = confdb['lang']
    if lang == 'sys':
        lang = params.locale
    logging.debug("misura_" + lang)
    if appTranslator.load("misura_" + lang, pathLang):
        logging.debug('installing translator')
        app.installTranslator(appTranslator)
        # devo creare un riferimento permanente onde evitare che il QTranslator
        # vada distrutto
        translators.append(appTranslator)
    else:
        logging.debug('translations not available')


def initNetwork():
    """Start zeroconf network scanner - deprecated"""
    # network.manager.start()
    pass


def initRegistry():
    # Avvio il registro
    registry.set_manager(network.manager)
    registry.toggle_run(True)


def closeRegistry():
    logging.debug('iutils.closeRegistry')
    registry.toggle_run(False)
    sleep(1)
    registry.terminate()

stylesheet = ""


def initApp(name='misura', org="Expert System Solutions", domain="expertsystemsolutions.it", client=True, qapp=False):
    """Inzializzazione generale di una applicazione misura Client.
    Creazione QApplication, installazione dei traduttori"""
    global translators, app
    app = qapp
    if not app:
        app = QtGui.QApplication(sys.argv)
    app.connect(app, QtCore.SIGNAL('aboutToQuit()'), closeApp)
    app.setOrganizationName(org)
    if domain:
        app.setOrganizationDomain(domain)
    app.setApplicationName(name)
    app.setStyleSheet(stylesheet)
    if client:
        initClient()
    app.setAttribute(QtCore.Qt.AA_DontShowIconsInMenus, False)
    return app

app_closed = False


def closeApp():
    """Connected to quit and last window closed signals."""
    # Avoid closing multiple times if multiple signals are sent!
    global app_closed
    if app_closed:
        return
    app_closed = True
    logging.debug('Closing App')
    # Save configuration
    confdb.save()
    closeRegistry()
    network.manager.scan = False
    sleep(0.1)
    network.manager.terminate()
    network.closeConnection()


def xcombinations(items, n):
    # Origine:
    # http://code.activestate.com/recipes/190465/
    if n == 0:
        yield []
    else:
        for i in xrange(len(items)):
            for cc in xcombinations(items[:i] + items[i + 1:], n - 1):
                yield [items[i]] + cc
from scipy import sqrt


def plotPalette(n):
    """Generatore di tavolozza massimo contrasto per i grafici."""
    l = n**(1 / 3.) + 2  # arrotondamento per eccesso
    l = int(l)
    v = range(255, 0, int(-255 / (l)))
    v.append(0)
    cc = []
    for c in xcombinations(v, 3):
        cc.append(c)
    r = []
    for i in range(2 * n):
        if i % 2 == 0:
            i = i // 2
        else:
            i = -i
        r.append(cc[i])
    return r


def isProxy(obj):
    r = repr(obj)
    return ('AutoProxy' in r) or ('MisuraProxy' in r)


def guessNextName(name):
    """Add +1 to a name composed of string+integer"""
    v = list(name)
    if len(v) < 1:
        return '', 0, '0'
    dg = set('0123456789')
    if v[-1] not in dg:
        return name, 1, name + '1'
    n = []
    while len(v) > 0:
        c = v.pop()
        if c in dg:
            n.append(c)
        else:
            v.append(c)
            break
    n.reverse()
    n = int(''.join(n))
    name = ''.join(v)
    return name, n, name + str(n + 1)


def num_to_string(val):
    if type(val) == type(''):
        return val
    a = abs(val)
    if 0.01 < a < 1000 or a < 10**-14:
        s = '%.2f' % val
    elif 1000 < a < 10000:
        s = '%.1f' % val
    else:
        s = '%.2E' % val
    return s


def getOpts():
    """-h Address
    -o Object
    Returns a dictionary with defaults or expressed variables.
    """
    import sys
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], 'h:o:')
    logging.debug(opts, args)
    h = 'https://admin:admin@localhost:3880/RPC'
    o = '/'
    r = {'-h': False, '-o': False}
    for opt, val in opts:
        if opt == 'o':
            if not val.startswith('/'):
                val = '/' + val
            if not val.endswith('/'):
                val += '/'
        if opt == 'h':
            if not h.startswith('https://'):
                val = 'https://' + val
            if not h.endswith('/RPC'):
                val += '/RPC'
        r[opt] = val
    return r


def get_custom(doc, name):
    for ctype, cname, val in doc.customs:
        if cname == name:
            return val
    return False

from veusz.utils import iter_widgets, searchFirstOccurrence



def most_involved_node(involved_plots, doc, exclude=':kiln'):
    # Collect all involved datasets
    involved = []
    for inp in involved_plots:
        # 'plot' entry is created by get_plotted_tree
        # Add to involved all datasets involved in all curves plotted
        # in the involved_plots
        involved += doc.model.plots['plot'].get(inp, [])
    # Find the common ancestor
    involved = [inv.split('/') for inv in involved]
    best_involved = involved
    lengths = [len(inv) for inv in involved]
    max_len = max(lengths)
    best_count = -1
    crumbs = []
    # Groups of most common names sorted by depth
    most_commons = [] 
    best = False
    for i in range(max_len):
        # Exclude the last element
        if len(crumbs) >= max_len : #-1:
            break
        # Keep only longer than current depth (i)
        best_involved = filter(lambda inv: len(inv) > i+1, 
                               best_involved)
        # Then keep only common anchestors
        if crumbs:
            best_involved = filter(lambda inv: inv[:len(crumbs)] == crumbs, 
                                   best_involved)
        
        # Names of the current depth (i) across all involved datasets
        level = [inv[i] for inv in best_involved]
        level = filter(lambda el: exclude not in el, level)
        
        # Find the most common name for the current depth (i)
        j = -1
        mc = []
        best = False
        for m, count in collections.Counter(level).most_common():
            if count > j:
                best = m
            j = count
            mc.append(m)
        if not best:
            break
        most_commons.append(mc)
        # Stop if the count decreases
        if count < best_count:
            break
        best_count = count
        crumbs.append(best)
        
    #print 'most_common', involved_plots, crumbs, most_commons
    return crumbs, most_commons


def calc_plot_hierarchy(doc, page_obj, exclude=':kiln/'):
    pages = doc.model.plots['page']

    hierarchy = defaultdict(list)

    for page, page_plots in pages.iteritems():
        crumbs = most_involved_node(page_plots, doc, exclude=exclude)[0]
        notes = doc.resolveFullWidgetPath(page).settings.notes
        hierarchy[len(crumbs)].append((page, page_plots, crumbs, notes))

    hierarchy = sorted(hierarchy.iteritems(), cmp=lambda a, b: a[0] - b[0])
    hierarchy = [sorted(h[1], key=lambda a: '/'.join(a[2]).lower())
                 for h in hierarchy]
    inpage = False
    level = -1
    page_idx = -1
    for level, pages in enumerate(hierarchy):
        for page_idx, (page_name, page_plots, crumbs, notes) in enumerate(pages):
            if page_name == page_obj.name:
                inpage = True
                break
        if inpage:
            break
    if not inpage:
        level = -1
        page_idx = -1

    return hierarchy, level, page_idx


def get_plotted_tree(base, m=False):
    """Builds a dictionary for the base graph:
            m => {'plot': {plotpath: dsname,...},
                      'dataset': {dsname: plotpath,...},
                      'axis':{axispath:[ds0,ds1,...]},
                      'xaxis':{axispath:[ds0, ds1, ...]},
                      'sample':[smp0,smp1,...]. 
                      'page': [plot names...}"""
    if m is False:
        m = {'plot': OrderedDict(),
             'dataset': OrderedDict(),
             'axis': OrderedDict(),
             'xaxis': OrderedDict(),
             'sample': [],
             'page': defaultdict(list)}
    for wg in base.children:
        # Recurse until I find an xy object
        if wg.typename in ('page', 'grid'):
            m = get_plotted_tree(wg, m)
        elif wg.typename == 'graph':
            m = get_plotted_tree(wg, m)
        elif wg.typename == 'xy':
            dsn = wg.settings.yData
            ds = wg.document.data.get(dsn, False)
            if ds is False:
                continue
            if not m['plot'].has_key(wg.path):
                m['plot'][wg.path] = []
            m['plot'][wg.path].append(dsn)
            if not m['dataset'].has_key(dsn):
                m['dataset'][dsn] = []
            m['dataset'][dsn].append(wg.path)
            # Fill page: plots map
            page = searchFirstOccurrence(wg, 'page', -1)
            m['page'][page.name].append(wg.path)

            # Save the dataset under its axis key
            axpath = wg.parent.path + '/' + wg.settings.yAxis
            if not m['axis'].has_key(axpath):
                m['axis'][axpath] = []
            m['axis'][axpath].append(dsn)
            
            # Save also x axis
            xaxpath = wg.parent.path + '/' + wg.settings.xAxis
            if not m['xaxis'].has_key(xaxpath):
                m['xaxis'][xaxpath] = []
            m['xaxis'][xaxpath].append(wg.settings.xData)

            # Fill sample map
            if not '/sample' in dsn:
                continue
            smp = getattr(ds, 'm_smp', False)
            if not smp:
                continue
            if smp.ref:
                continue
            m['sample'].append(smp['fullpath'])

        elif wg.typename in ('axis', 'axis-function'):
            if wg.settings.direction != 'vertical':
                if not m['xaxis'].has_key(wg.path):
                    m['xaxis'][wg.path] = []
            elif not m['axis'].has_key(wg.path):
                m['axis'][wg.path] = []
    # Persistent sorting
    for k0 in m.keys():
        if k0 in ('sample', 'changeset'):
            continue
        for k1 in m[k0].keys():
            m[k0][k1] = sorted(m[k0][k1])
    return m


def shorten(name, number_of_chars_to_show=30):
    if len(name) <= number_of_chars_to_show:
        return name

    return name[0:number_of_chars_to_show / 2] + "..." + name[-number_of_chars_to_show / 2:]

# Caricamento icone


def loadIcons():
    """Icons loading. Must be called after qapplication init."""
    # d=list(os.path.split(veusz.utils.utilfuncs.resourceDirectory))[:-1]+['misura','client','art']
    # artdir=os.path.join(*tuple(d))

    for key in ['m4.connect', 'm4.db', 'm4.open', 'm4.sintering',
                'm4.softening', 'm4.sphere', 'm4.halfSphere',
                'm4.melting', 'm4.single-ramp', 'm4.icon']:
        n = key.split('.')[1] + '.svg'
        n = os.path.join(params.pathArt, n)
        logging.debug( n)
        if not os.path.exists(n):
            continue
        veusz.utils.action._iconcache[key] = QtGui.QIcon(n)
        
def theme_icon(name, ext='.svg'):
    if QtGui.QIcon.hasThemeIcon(name):
        return QtGui.QIcon.fromTheme(name)
    p = os.path.join(params.pathIcons, name+ext)
    if not os.path.exists(p):
        p = os.path.join(params.pathArt, name+ext)
    if not os.path.exists(p):
        logging.debug('ICON not found', name, p)
        return QtGui.QIcon()
    return QtGui.QIcon(p)


def with_waiting_mouse_cursor(function_to_call):
    QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
    try:
        function_to_call()
    finally:
        QtGui.QApplication.restoreOverrideCursor()
