#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore

from misura.canon.plugin import dataimport
from misura.canon.plugin import default_plot_plugins, default_plot_rules

from .. import _
from ..clientconf import confdb
from .. import widgets


from operation import jobs, job, done


def confirm_overwrite(path, parent=None):
    msg = QtGui.QMessageBox(QtGui.QMessageBox.Warning, _('Overwrite destination file?'),
                            _('Destination file will be overwritten:\n{}'.format(path)),
                            parent=parent)
    ow = msg.addButton(_('Overwrite'), 1)
    re = msg.addButton(_('Rename'), 2)
    op = msg.addButton(_('Open'), 3)
    ex = msg.addButton(_('Cancel'), 0)
    v = {ow: 1, re: 2, ex: 0, op: 3}
    msg.exec_()
    ret = v[msg.clickedButton()]
    return ret

def convert_file(caller, path):
    """Caller must implement:
    - connect select(QString)
    - _open__converted
    - _failed_conversion
    """
    if path.endswith('.h5'):
        caller.emit(QtCore.SIGNAL('do_open(QString)'), path)
        #caller.open_file(path)
        return True
    caller.converter = False
    caller.converter = dataimport.get_converter(path)
    if not caller.converter:
        title = _('No file format converter found')
        logging.debug(title, path)
        QtGui.QMessageBox.warning(None, title, title + '\n' + path)
        return False
    caller.converter.confdb = confdb
    # Check overwrite
    outpath = caller.converter.get_outpath(path)
    if outpath is False:
        return False
    ok = 1
    if os.path.exists(outpath):
        ok = confirm_overwrite(outpath, caller)
        if not ok:
            logging.debug('Overwrite cancelled')
            return False
    if ok == 3:
        caller.converter.outpath = outpath
        caller._open_converted()
        return True
    elif ok == 2:
        dname = os.path.dirname(outpath)
        fname = os.path.basename(outpath)[:-3]
        i = 1
        while  os.path.exists(outpath):
            outpath = os.path.join(dname, fname + str(i) + '.h5')
            logging.debug('Renamed to', outpath)
            i += 1
    caller.converter.outpath = outpath
    # Go
    run = widgets.RunMethod(caller.converter.convert, path,
                            jobs, job, done)
    run.step = 100
    run.pid = caller.converter.pid
    caller.connect(run.notifier, QtCore.SIGNAL(
        'done()'), caller._open_converted, QtCore.Qt.QueuedConnection)
    caller.connect(run.notifier, QtCore.SIGNAL(
        'failed(QString)'), caller._failed_conversion, QtCore.Qt.QueuedConnection)
    QtCore.QThreadPool.globalInstance().start(run)
    return True


def get_default_plot_plugin_class(instrument_name):
    from ..clientconf import confdb
    from .. import plugin
    plugin_class = default_plot_plugins.get(instrument_name, plugin.DefaultPlotPlugin)
    print 'defaultPlot', plugin_class
    plot_rule_func = default_plot_rules.get(instrument_name, lambda *a: confdb['rule_plot'])
    return plugin_class, plot_rule_func
