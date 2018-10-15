#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from PyQt4 import QtGui, QtCore

from misura.canon.plugin import dataimport
from misura.canon.plugin import default_plot_plugins, default_plot_rules
from misura.canon.indexer import SharedFile
from .. import _
from ..clientconf import confdb
from .. import widgets


from operation import jobs, job, done

CONVERT_ABORT = QtGui.QMessageBox.RejectRole
CONVERT_OVERWRITE = QtGui.QMessageBox.ActionRole
CONVERT_RENAME = QtGui.QMessageBox.YesRole
CONVERT_OPEN = QtGui.QMessageBox.AcceptRole

def confirm_overwrite(path, parent=None):
    msg = QtGui.QMessageBox(QtGui.QMessageBox.Warning, _('Overwrite destination file?'),
                            _('Destination file will be overwritten:\n{}'.format(path)),
                            parent=parent)
    msg.setEscapeButton(msg.addButton(_('Cancel'), CONVERT_ABORT))
    msg.addButton(_('Overwrite'), CONVERT_OVERWRITE)
    msg.addButton(_('Rename'), CONVERT_RENAME)
    msg.addButton(_('Open'), CONVERT_OPEN)
    msg.exec_()
    return msg.buttonRole(msg.clickedButton())

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
        logging.info('Conversion aborted - cannot determine outpath', path, outpath)
        return False
    ok = CONVERT_OVERWRITE
    if os.path.exists(outpath):
        ok = confirm_overwrite(outpath, caller)
        if ok == CONVERT_ABORT:
            logging.debug('Overwrite cancelled')
            return False
        if ok == CONVERT_OVERWRITE:
            SharedFile.close_handlers(outpath)
            
    if ok == CONVERT_OPEN:
        caller.converter.outpath = outpath
        caller._open_converted()
        return True
    elif ok == CONVERT_RENAME:
        dname = os.path.dirname(outpath)
        fname = os.path.basename(outpath)[:-3]
        i = 1
        while  os.path.exists(outpath):
            outpath = os.path.join(dname, fname + str(i) + '.h5')
            logging.debug('Renamed to', outpath)
            i += 1
        
    # Renaming/overwriting
    caller.converter.outpath = outpath
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
    logging.debug('get_default_plot_plugin_class', plugin_class)
    plot_rule_func = default_plot_rules.get(instrument_name, lambda *a: confdb['rule_plot'])
    return plugin_class, plot_rule_func
