#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
from time import time
import collections
import threading
from traceback import format_exc
import re
import numpy as np
import datetime

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.canon.csutil import lockme
from .. import network
from .. import units
from ..clientconf import confdb
from .. import _
from ..live import registry
from . import builder

from PyQt4 import QtGui, QtCore

from misura.client.parameters import MAX, MIN


def extend_decimals(cur, default=2, extend_by=2):
    """Find out how many decimals to enable in editing for float value `num`"""
    if np.isnan(cur):
        return 0
    cur = abs(float(cur))
    n = 0
    lim = 10**(-default)
    while n<default:
        d = abs(cur-round(cur, 0))
        if d<=lim:
            break
        cur *= 10
        n+=1
    return n


def getRemoteDev(server, devpath):
    if devpath == 'None':
        return False, None
    sp = server.searchPath(devpath)
    logging.debug('Getting Remote Dev', sp, devpath)
    if not sp:
        return False, None
    logging.debug('Getting Remote Dev', sp)
    dev = server.toPath(sp)
    logging.debug('Got Remote Dev', devpath, dev)
    return True, dev


def info_dialog(text, title='Info', parent=None):
    """Show html text in a simple dialog window."""
    dial = QtGui.QDialog(parent)
    dial.setWindowTitle(title)
    lay = QtGui.QVBoxLayout()
    txt = QtGui.QTextBrowser()
    txt.setHtml(text)
    lay.addWidget(txt)
    dial.setLayout(lay)
    dial.resize(400, 400)
    dial.exec_()

def text_value(val):
    value = repr(val)
    value = (value[:15] + '..') if len(value) > 15 else value
    return value    

def build_presets_menu(comparison, container, menu, set_func, set_to_preset_func):
    menu.clear()
    for name, val in comparison.items():
        if name == '***current***':
            continue
        logging.debug('build_presets_menu', name, val)
        value = text_value(val)
        label = '{}:{}'.format(name, value)
        p = functools.partial(set_func, val)
        menu.addAction(label, p)
        container[name] = (p, val)
        
    if len(comparison)>1:
        val = comparison['***current***']
        presets = set(comparison.keys())
        presets.remove('***current***')
        presets = list(presets)
        p0 = lambda preset: set_to_preset_func(preset, val)
        p = functools.partial(map, p0, presets)
        menu.addAction(_('Copy current to all'), p)
        container['**applyall**'] = (p, val, p0)
            
def build_option_menu(comparison, container, menu, set_func):
    menu.clear()
    for name, vals in comparison.items():
        if name == '***current***':
            continue
        print('build_option_menu', name, vals)
        if len(vals)==1:
            val = vals.items()[0][1]
            value = text_value(val)
            label = '{}:{}'.format(name, value)
            p = functools.partial(set_func, val)
            menu.addAction(label, p)
            container[name] = (p, val)
        else:
            sub = menu.addMenu(name)
            p = functools.partial(set_func, vals.items())
            sub.addAction('Apply all', p)
            container[name] = (p, None)
            for key, val in vals.items():
                value = text_value(val)
                label = '{}:{}'.format(key, value)
                p = functools.partial(set_func, ((key, val)))
                sub.addAction(label, p)
                container[name+':'+key] = (p, key, val) 

class Notifier(QtCore.QObject):
    done = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(object)

class RunMethod(QtCore.QRunnable):
    runnables = []
    step = 2
    emit_result = True

    def __init__(self, func, *args, **kwargs):
        QtCore.QRunnable.__init__(self)
        self.notifier = Notifier()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.pid = 'Waiting: {}'.format(func)
        logging.debug('RunMethod initialized', self.func, 
                      self.args, self.kwargs)
        self.runnables.append(self)
        self.error = False
        self.running = False
        self.done = False
        self.abort = self._abort
        self.result = None
        
    def _abort(self):
        self.error = 'Aborted'
        
    def emit(self, *a, **k):
        return self.notifier.emit(*a, **k)
    
    def connect(self, *a, **k):
        return self.notifier.connect(*a, **k)
    
    def job(self,n,msg=False):
        registry.tasks.job(n, self.pid, msg or self.pid)

    def run(self):
        """Run the task. Call directly to execute synchronously."""
        self.running = True
        registry.tasks.jobs(self.step, self.pid, self.abort)
        logging.debug(
            'RunMethod.run', self.func, self.args, self.kwargs)
        registry.tasks.job(1, self.pid, self.pid)
        try:
            self.result = self.func(*self.args, **self.kwargs)
            logging.debug('RunMethod.run done')
            self.notifier.done.emit()
            if self.emit_result:
                self.notifier.result.emit(self.result)
        except:
            self.error = format_exc()
            logging.debug('RunMethod.run error', self.error)
            self.notifier.failed.emit()
            self.notifier.error.emit(self.error)
        registry.tasks.done(self.pid)
        self.runnables.remove(self)
        self.done = True
        self.running = False
        
    def do(self):
        """Run the task in a separate thread"""
        QtCore.QThreadPool.globalInstance().start(self)



class Active(object):
    interval = 200
    last_async_get = 0
    force_update = False
    _lock = False
    current = None
    """Current server-side value"""
    unit = None
    prop = None
    

    def __init__(self, server, remObj, prop, context='Option', connect=True):
        self._lock = threading.Lock()
        self.server = server
        self.remObj = remObj
        self.path = remObj._Method__name
        self.context = context
        self.update_option(prop)

        # Update the widget whenever the manager gets reconnected
        network.manager.connect(network.manager, QtCore.SIGNAL(
            'connected()'), self.reconnect, QtCore.Qt.QueuedConnection)
        
    def update_option(self, prop = False):
        if not prop:
            prop = self.remObj.gete(self.handle)
            logging.debug('Active.update_option', self.handle)
        self.prop = prop
        for p in 'current', 'type', 'handle', 'factory_default', 'attr', 'readLevel', 'writeLevel', 'name':
            setattr(self, p, prop.get(p, None))
        write_level = getattr(self.remObj, '_writeLevel', 5)
        self.readonly = (self.type == 'ReadOnly') or (
            'ReadOnly' in self.attr) or (write_level < self.writeLevel)
        self.hard = 'Hard' in self.attr
        self.hot = 'Hot' in self.attr
        self.label = _(self.name)
        return self.prop

    def isVisible(self):
        """Compatibility function with QWidget"""
        return True

    def register(self):
        """Re-register itself if visible."""
        if self.isVisible():
            registry.register(self)

    def unregister(self):
        registry.unregister(self)

    def async_get(self):
        """Asynchronous get method, executed in the thread pool."""
        t = time()
        if t - self.last_async_get < self.interval / 1000.:
            return False
        r = RunMethod(self.get)
        r.pid = _('Waiting: ') + self.label
        QtCore.QThreadPool.globalInstance().start(r)
        self.last_async_get = t
        return True

    def reconnect(self):
        self.remObj = getattr(network.manager.remote,  self.path)
        self.update()

    def emit(self, *a):
        if a[0] == QtCore.SIGNAL('selfchanged'):
            self._get(a[1])

    def emitHelp(self):
        parent = self.path.split('/')[0]
        url = 'http://www.expertsystemsolutions.it/wiki/%s/%s' % (
            parent, self.handle)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def emitChanged(self):
        """Current value changed server-side."""
        self.update()
        self.emit(QtCore.SIGNAL('changed'), self.current)
        self.emit(QtCore.SIGNAL('changed()'))
        self.emitOptional()

    def emitRedraw(self):
        """Perform an hard-reset of the widget"""
        self.emit(QtCore.SIGNAL('redraw()'))
        
    def emit_client_changed(self):
        """A set() call originated from the client-side caused the current value to change"""
        self.emit(QtCore.SIGNAL('client_changed()'))
        
    def redraw(self):
        pass
    
    def changed_option(self):
        self.update_option()
        

    def emitError(self, msg):
        msg = self.tr(msg)
        logging.debug(msg)

    def emitOptional(self):
        pass

    def adapt(self, val):
        """Translates between GUI and server data types. It is first called by both adapt2srv() and adapt2gui() methods"""
        return val

    def adapt2gui(self, val):
        """Translate server data types into GUI data type.
        `val` is the server-side data value"""
        val = self.adapt(val)
        val = units.Converter.convert(
            self.prop.get('unit', 'None'), self.prop.get('csunit', 'None'), val)
        return val

    def adapt2srv(self, val):
        """Translates a GUI data type into a server-side data type.
        `val` is the GUI data value (eg: widget signal Qt object)"""
        val = self.adapt(val)
        val = units.Converter.convert(
            self.prop.get('csunit', 'None'), self.prop.get('unit', 'None'), val)
        return val

    def set(self, val, *foo):
        """Set a new value `val` to server. Convert val into server units."""
        val = self.adapt2srv(val)
        if val == self.current:
            logging.debug('Not setting',self.handle, repr(val), repr(self.current), id(self.parent()), self.parent().isVisible())
            return True
        old = self.current
        out = self.remObj.set(self.handle,  val)
        r = self.get()
        if self.current!=old:
            self.emit_client_changed()
        return r

    def set_raw(self, val):
        """Set value directly, without adapt2srv conversion.
        Enable if disabled."""
        old = self.current
        self.remObj.set(self.handle, val)
        enable = None
        if self.remObj.hasattr(self.handle, 'flags'):
            flags = self.remObj.getattr(self.handle, 'flags')
            enable = flags.get('enabled', None)
        if enable==False:
            self.remObj.setattr(self.handle, 'flags', {'enabled': True})
            self._check_flags()
        r = self.get()
        if self.current!=old:
            self.emit_client_changed()
        return r

    def _get(self, rem=None):
        self.register()
        if rem is None:
            self.emitChanged()
        elif self.current != rem:
            self.current = rem
            self.emitChanged()

    def _check_flags(self, *args):
        rem_flags = self.remObj.getFlags(self.handle, *args)
        if rem_flags and (rem_flags.get('enabled', None) is not None):
            self.enable_check.setChecked(rem_flags['enabled'])

    def _call_function_then_emitchanged_and_checkflags(self, function, *args):
        rem = function(self.handle, *args)
        self._get(rem)
        self._check_flags(*args)
        return rem

    @lockme()
    def get(self, *args):
        return self._call_function_then_emitchanged_and_checkflags(
            self.remObj.get, *args)

    @lockme()
    def soft_get(self, *args):
        self._call_function_then_emitchanged_and_checkflags(
            self.remObj.soft_get, *args)

    def emitSelfChanged(self, nval):
        self._get(nval)

    def set_default(self):
        """Sets the remote property to its facotry_default value"""
        fd = self.prop['factory_default']
        self.set(fd)

    def update(self):
        """Updates the GUI to the self.current value.
        To be overridden in subclasses."""
        pass

    def updateFromRemote(self):
        """Force a re-reading from remote object and a GUI update.
        Called during automatic synchronization cycles (like live.KidRegistry)."""
        self.get()
        self.update()
        
    def set_enabled(self,enabled=None):
        return


class ActiveObject(Active, QtCore.QObject):
    client_changed = QtCore.pyqtSignal()
    
    def __init__(self, server, remObj, prop, parent=None, context='Option'):
        Active.__init__(self, server, remObj, prop, context)
        QtCore.QObject.__init__(self, parent=parent)
        self.connect(self, QtCore.SIGNAL('destroyed()'),
                     self.unregister, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('selfchanged'), self._get, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('selfchanged()'), self._get, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('redraw()'), self.redraw, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('changedOption()'), self.changed_option, QtCore.Qt.QueuedConnection)

    def emit(self, *a, **k):
        try:
            return QtCore.QObject.emit(self, *a, **k)
        except:
            return False


class LabelUnit(QtGui.QLabel):
    clicked = QtCore.pyqtSignal()

    def __init__(self, prop, parent=None):
        """Label displaying the measurement unit, optional menu, able to start a drag event."""
        QtGui.QLabel.__init__(self, '.', parent=parent)
        self.prop = prop
        self.menu = False
        #self.setMaximumWidth(30)
        self.setMinimumSize(0,0)
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        self.setAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
        self.setStyleSheet("margin-left: 5px; margin-right: 5px;")

    def sizeHint(self):
        r = QtGui.QLabel.sizeHint(self)
        self.setMaximumWidth(r.width())
        return r

    def setMenu(self, menu):
        self.menu = menu

    def start_drag(self):
        """Begin a drag and drop event"""
        wg = self.parent()
        drag = QtGui.QDrag(wg)
        mimeData = QtCore.QMimeData()
        kid = (wg.remObj['fullpath']+'/'+wg.handle).replace('//','/')
        mimeData.setData("misura/option", '{}:{}'.format(id(wg.server), kid))
        mimeData.setData("text/plain", '{}: {}'.format(self.prop['name'], self.prop['current']))
        drag.setMimeData(mimeData)
        logging.debug('start drag', mimeData.text())
        drag.exec_()

    def show_menu(self, event):
        """Show associated menu"""
        if self.menu:
            self.menu.popup(event.globalPos())
            self.clicked.emit()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.start_drag()
        elif self.menu and event.button() == QtCore.Qt.RightButton:
            self.show_menu(event)
        return QtGui.QLabel.mousePressEvent(self, event)


class LabelWidget(QtGui.QLabel):

    def __init__(self, active):
        self.active = active
        prop = active.prop
        QtGui.QLabel.__init__(
            self, unicode(_(prop['name'], context='Option')), parent=active)
        self.setWordWrap(True)
        self.prop = prop
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

    def mousePressEvent(self, event):
        return self.active.bmenu.mousePressEvent(event)

    def enterEvent(self, event):
        return self.active.enterEvent(event)

    def leaveEvent(self, event):
        return self.active.leaveEvent(event)

    def dropEvent(self, event):
        """Route drop event to parent ActiveWidget"""
        self.active.receive_drop(event)
        return QtGui.QLabel.dropEvent(event)

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent', event.mimeData())
        event.acceptProposedAction()
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()


class ActiveWidget(Active, QtGui.QWidget):

    """Graphical representation of an Option object"""
    bmenu_hide = True
    """Auto-hide menu button"""
    get_on_enter = True
    """Update on mouse enter"""
    get_on_leave = True
    """Update on mouse leave"""
    enable_check = False
    visibility_changed = QtCore.pyqtSignal(bool)
    client_changed = QtCore.pyqtSignal()
    def __init__(self, server, remObj, prop, parent=None, context='Option'):
        Active.__init__(self, server, remObj, prop, context)
        QtGui.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._win_map = {}
        self.label = self.tr(self.name)

        self.lay = QtGui.QHBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.setLayout(self.lay)
        self.label_widget = LabelWidget(self)  # Info label
        self.redraw()
        
    def clear_layout(self, lay=None):
        if lay is None:
            lay=self.lay
        while True:
            w = lay.takeAt(0)
            if not w:
                break
            w1 = w.widget()
            w1.hide()
            if w1 is None:
                self.clear_layout(w.layout())
            else:
                w1.deleteLater()
                
    def set_tooltip(self):
        if not hasattr(self,'lay'):
            return False
        tp = self.prop.get('toolTip','')
        for i in range(self.lay.count()):
            item = self.lay.itemAt(i)
            if not item: continue
            wg = item.widget()
            if not wg: continue 
            wg.setToolTip(tp)
        self.setToolTip(tp)
        return tp
    
    def redraw(self):
        self.clear_layout()
        self.readonly_label = QtGui.QLabel('')
        self.readonly_label.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.readonly_label.setMinimumWidth(100)
        self.readonly_label.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Minimum)
        self.readonly_label.setStyleSheet("border: 1px solid grey; \
                                            margin-left: 0px; margin-right: 0px; \
                                            padding-left: 5px; padding-right: 5px;")
        self.readonly_label.setWordWrap(True)
        self.readonly_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard|
                                                    QtCore.Qt.TextSelectableByMouse|
                                                    QtCore.Qt.LinksAccessibleByMouse)
        self.readonly_label.hide()
        self.lay.addWidget(self.readonly_label)
        
        
        self.emenu = QtGui.QMenu(self)
        self.recent_menu = QtGui.QMenu(_('Recent'), parent=self)
        self.recent_menu.aboutToShow.connect(self.build_recent_menu)
        
        self.presets_menu = QtGui.QMenu(_('Presets'), parent=self)
        self.presets_menu.aboutToShow.connect(self.build_presets_menu)
        
        self.database_menu = QtGui.QMenu(_('Database'), parent=self)
        self.database_menu.aboutToShow.connect(self.build_database_menu)
        
        self.compare_menu = QtGui.QMenu(_('Compare'), parent=self)
        self.compare_menu.aboutToShow.connect(self.build_compare_menu)
        
        self.compare_group_menu = QtGui.QMenu(_('Compare group'), parent=self)
        self.compare_group_menu.aboutToShow.connect(self.build_compare_group_menu)
        
        self.build_extended_menu()
        
        
        self.connect(self, QtCore.SIGNAL('destroyed()'),
                     self.unregister, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('selfchanged'), self._get, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('selfchanged()'), self._get, QtCore.Qt.QueuedConnection)
        self.connect(self, QtCore.SIGNAL('selfhide()'), self.hide)
        self.connect(self, QtCore.SIGNAL('selfshow()'), self.show)
        self.menu_timer = QtCore.QTimer(parent=self)
        self.menu_timer.setSingleShot(True)
        self.menu_timer.setInterval(500)
        self.connect(self.menu_timer, QtCore.SIGNAL(
            'timeout()'), self.do_hide_menu, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('redraw()'), self.redraw, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('changedOption()'), self.changed_option, QtCore.Qt.QueuedConnection)
        self.set_tooltip() 
        
    def new_window(self):
        """Displays a copy of the widget in a new window"""
        win = QtGui.QWidget()
        lay = QtGui.QVBoxLayout()
        wg = self.__class__(self.server, self.remObj, self.prop, parent=win)
        win.setWindowTitle(self.label)
        wg.label_widget.show()
        lay.addWidget(wg.label_widget)
        wg.label_widget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        lay.addWidget(wg)
        wg.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        win.setLayout(lay)
        self._win = win
        win.show()

    @lockme()
    def closeEvent(self, event):
        self.menu_timer.stop()
        self.unregister()
        self.blockSignals(True)
        return super(ActiveWidget, self).closeEvent(event)

    @property
    def unit(self):
        """Get measurement unit for this label"""
        # First check the client-side unit
        if not self.prop:
            return False
        u = self.prop.get('csunit', False)
        if u in ['', 'None', None, False]:
            u = False
        if not u:
            u = self.prop.get('unit', False)
        if u in ['', 'None', None, False]:
            u = False
        return u

    def set_label(self):
        """Update label contents"""
        sym = False
        u = self.unit
        if u and isinstance(u, collections.Hashable):
            sym = units.hsymbols.get(u, False)
        msg = '..'
        if sym:
            msg = u'{}'.format(sym)
        self.bmenu.setText(msg)

    def set_unit(self, unit):
        """Change measurement unit"""
        for u, (act, p) in self.units.iteritems():
            if u != unit:
                act.setChecked(False)
                continue
            act.setChecked(True)
            logging.debug('Setting csunit to', u)
            r = self.remObj.setattr(self.handle, 'csunit', u)
            self.prop['csunit'] = u
            logging.debug('result', r)
        self.set_label()
        self.update_menu()
        self.update()

    def set_flags(self, foo=0):
        out = {}
        for key, act in self.flags.iteritems():
            out[key] = act.isChecked() > 0
        if self.enable_check:
            out['enabled'] = self.enable_check.isChecked()

        logging.debug('updating flags', out)
        r = self.remObj.setFlags(self.handle, out)
        return r

    def update_menu(self):
        flags = self.remObj.getFlags(self.handle)
        logging.debug('remote flags', flags)
        for key, act in self.flags.iteritems():
            if not flags.has_key(key):
                logging.debug('Error, key disappeared', key)
            act.setChecked(flags[key] * 2)
            if key == 'enabled':
                self.enable_check.setChecked(flags[key] * 2)
        
        if self.remObj.navigator:
            self.remObj.navigator.build_menu_from_configuration(self.remObj, self.nav_menu)
            self.emenu.addAction(self.nav_menu.menuAction())
        else:
            logging.debug('NO navigator defined', self.remObj._navigator)
            self.emenu.removeAction(self.nav_menu.menuAction())
            
    def set_enabled(self, enabled=None):
        if enabled is None:
            enabled = self.prop.get('flags',{'enabled':True}).get('enabled', True)
        enabled = bool(enabled)
        for i in range(self.layout().count()):
            wg = self.layout().itemAt(i).widget()
            if wg not in (self.label, self.enable_check, 0, None):
                wg.setEnabled(enabled)
    
        
    def build_extended_menu(self):
        # Extended menu
        self.emenu.clear()
        # Add flags to context menu
        self.flags = {}
        prop = self.prop
        if prop.has_key('flags'):
            for key, val in prop['flags'].iteritems():
                act = self.emenu.addAction(key, self.set_flags)
                act.setCheckable(True)
                act.setChecked(val * 2)
                self.flags[key] = act
                if key == 'enabled':
                    encheck = QtGui.QCheckBox(self)
                    encheck.setToolTip(_('Is option enabled?'))
                    encheck.setChecked(val * 2)
                    encheck.stateChanged.connect(self.set_enabled)
                    self.connect(
                        encheck, QtCore.SIGNAL('stateChanged(int)'), self.set_flags)
                    self.lay.addWidget(encheck)
                    self.enable_check = encheck
                    self.set_enabled(val)

        # Units sub-menu
        self.units = {}
        u = self.unit
        u1 = ''
        if u != 'None' and type(u) == type(''):
            un = self.emenu.addMenu(_('Units'))
            kgroup, f, p = units.get_unit_info(u, units.from_base)
            same = units.from_base.get(kgroup, {u: lambda v: v}).keys()
            for u1 in same:
                p = functools.partial(self.set_unit, u1)
                act = un.addAction(_(u1), p)
                act.setCheckable(True)
                if u1 == u:
                    act.setChecked(True)
                self.units[u1] = (act, p)
                
        if not self.readonly:
            self.emenu.addAction(_('Reset to default value'), self.set_default)
            if not hasattr(self.remObj,'_remoteDict'):
                self.emenu.addMenu(self.recent_menu)
        if hasattr(self.remObj,'_remoteDict'):
            self.emenu.addAction(_('Check for modification'), self.get)
        if self.remObj._writeLevel>3:
            self.emenu.addAction(_('Option Info'), self.show_info)
        self.emenu.addAction(_('Detach'), self.new_window)
        
        
        if 'fullpath' in self.remObj:
            self.emenu.addAction('Hide this option', self.set_option_hidden)
        
        if self.prop.get('aggregate', ''):
            self.agg_menu = self.emenu.addMenu(_('Aggregation'))
            self.agg_menu.menuAction().hovered.connect(functools.partial(self.build_aggregation_menu, self.agg_menu))
        if self.remObj.compare_presets is not None:
            # ONLY if online
            self.emenu.addMenu(self.presets_menu)
        #else:
        #    # ONLY if offline
        self.emenu.addMenu(self.compare_menu)
        if self.prop['type'] in ['Float', 'Integer','String']:
            self.emenu.addMenu(self.database_menu)
        if len(self.prop.get('children', [])):
            self.emenu.addMenu(self.compare_group_menu)
        self.nav_menu = self.emenu.addMenu(_('Navigator'))
        
        #self.emenu.addAction(_('Online help for "%s"') % self.handle, self.emitHelp)
        # Units button
        self.bmenu = LabelUnit(self.prop, self)
        self.bmenu.setMenu(self.emenu)
        self.bmenu.setSizePolicy(
            QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.bmenu.clicked.connect(self.update_menu)
        if not self.unit or self.type.startswith('Role') or self.type=='Table':
            self.bmenu.hide()
        self.set_label()
        self.lay.addWidget(self.bmenu)
        
    def set_option_hidden(self):
        self.hide()
        self.label_widget.hide()
        self.readonly_label.hide()
        return
        #TODO: need a way to easily restore the visibility! 
        # eg: am Interface panel context menu to recall all hidden options
        fp = self.remObj['fullpath']
        rule = '^'+fp+self.handle+'$'
        opt = confdb['opt_hide']
        logging.debug('HIDE', fp, rule, opt)
        if rule not in opt:
            if len(opt):
                rule = '\n'+rule
            confdb['opt_hide'] = opt+rule
            logging.debug('Set opt_hide to', confdb['opt_hide'])

        
        
    def update_aggregate(self):
        r = self.remObj.update_aggregate(self.handle)
        logging.debug('Update aggregate', self.handle)
        if r:
            self.get()
        
    def build_aggregation_menu(self, menu):
        menu.clear()
        menu.addAction(_('Update'), self.update_aggregate)
        aggregation = self.prop.get('aggregate', "")
        logging.debug('Build aggregation menu:', self.handle, aggregation)
        self._menu_map = {}
        builder.build_recursive_aggregation_menu(self.remObj.root, self.remObj, aggregation, 
                                         {self.remObj['fullpath']: self.handle}, menu, self._menu_map, self._win_map)

            
    def build_presets_menu(self):
        self.presets = {}
        comparison = self.remObj.compare_presets(self.handle)
        set_to_preset_func = functools.partial(self.remObj.set_to_preset, self.handle)
        build_presets_menu(comparison, self.presets, self.presets_menu, self.set_raw, 
                           set_to_preset_func)

            
    def build_compare_menu(self):
        """Populate option comparison menu"""
        self.compare = {}
        comparison = self.remObj.compare_option(self.handle)
        build_option_menu(comparison, self.compare, self.compare_menu, self.set_raw)
        
    def build_compare_group_menu(self):
        """Populate option group comparison menu"""
        self.compare_group = {}
        comparison = self.remObj.compare_option(self.handle, *self.prop['children'].keys())
        wm = self.parent().parent().widgetsMap.copy()
        wm[self.handle] = self
        set_func = lambda keyvals: [wm[k].set_raw(v) for k,v in keyvals]
        build_option_menu(comparison, self.compare_group, self.compare_group_menu, set_func)
        
    def build_database_menu(self):
        self.database_menu.clear()
        fullpath = self.remObj['fullpath']
        #TODO: we should get real regex into sqlite for this to work...
        # Sample wildcard
        sn = re.findall(r'^/[\w]+/sample(\d+)/[\w+]?', fullpath)
        if sn:
            sn1 = '_'*len(sn[0])
            fullpath = fullpath.replace('/sample{}/'.format(sn[0]), '/sample'+sn1+'/')
        
        # Shot wildcard
        sn = re.findall(r'^/flash/sample[_]+/T[-]?\d+/N(\d+)/[\w+]?', fullpath)
        if sn:
            sn1 = '_'*len(sn[0])
            fullpath = fullpath.replace('/N{}/'.format(sn[0]), '/N'+sn1+'/')       
        
        mro = None
        if 'mro' in self.remObj:
            fullpath = None
            mro = self.remObj['mro']
        
        ret = confdb.index.query_recent_option(self.prop['type'], 
                                               fullpath=fullpath, 
                                               handle=self.handle, 
                                               mro=mro)
        for (t, test, value) in ret:
            func = functools.partial(self.set, value)
            act = self.database_menu.addAction('{}, {} on {}'.format(value, test, t), func)
            
    def build_recent_menu(self):
        self.recent_menu.clear()
        if 'chron' not in self.prop:
            return False
        times, values = self.remObj.getattr(self.handle, 'chron')
        if not len(times):
            return False
        t0 = time()
        v1 = values[-2::-1]
        for i, t in enumerate(times[-2::-1]):
            v = v1[i]
            t = datetime.timedelta(seconds=int(t0-t))
            self.recent_menu.addAction('{} on {} ago'.format(v, t), functools.partial(self.set, v))
        return True

    def isVisible(self):
        try:
            return QtGui.QWidget.isVisible(self)
        except:
            return False

    def emit(self, *a, **k):
        try:
            return QtGui.QWidget.emit(self, *a, **k)
        except:
            return False

    def enterEvent(self, event):
        """Update the widget anytime the mouse enters its area."""
        if self.get_on_enter:
            self.get()
        # Show only if label_widget is not visible
        if not self.label_widget.isVisible():
            self.bmenu.show()
        return QtGui.QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
        if self.get_on_leave:
            self.get()
        if self.bmenu_hide and not self.unit:
            QtCore.QTimer.singleShot(500, self.do_hide_menu)
        return QtGui.QWidget.leaveEvent(self, event)

    def do_hide_menu(self):
        """Delayed hiding"""
        try:
            cur = self.mapFromGlobal(QtGui.QCursor.pos())
        except RuntimeError:
            # Widget was deleted in the meanwhile...
            return
        x, y = cur.x(), cur.y()
        if x < 0 or y < 0 or x > self.width() or y > self.height():
            self.bmenu.hide()
        else:
            # Retry later
            self.menu_timer.start()

    def clear(self):
        """Removes all widgets in this layout"""
        for i in range(self.lay.count()):
            item = self.lay.itemAt(0)
            if item == 0:
                break
            elif item == self.label:
                continue
            self.lay.removeItem(item)
            w = item.widget()
            w.hide()
            w.close()
            del w

    def emitHelp(self):
        self.emit(QtCore.SIGNAL('help'), 0)
        Active.emitHelp(self)

    def emitError(self, msg):
        Active.emitError(self, msg)
        self.emit(QtCore.SIGNAL('error(QString)'), msg)

    def showEvent(self, e):
        self.register()
        self.visibility_changed.emit(True)
        return QtGui.QWidget.showEvent(self, e)

    def hideEvent(self, e):
        self.unregister()
        self.visibility_changed.emit(False)
        return QtGui.QWidget.hideEvent(self, e)

    def receive_drop(self, event):
        """Receive a drop event from any sub widget"""
        return

    def dropEvent(self, event):
        self.receive_drop(event)
        return QtGui.QWidget.dropEvent(self, event)

    def dragEnterEvent(self, event):
        logging.debug('dragEnterEvent', event.mimeData())
        event.acceptProposedAction()
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def show_info(self):
        prop = self.prop
        logging.debug(prop)
        t = '<h1> Option: %s </h1>' % prop.get('name', 'Object')

        for k, v in prop.iteritems():
            t += '<b>{}</b>: {}<br/>'.format(k, v)

        info_dialog(t, parent=self)
        

        

    
    