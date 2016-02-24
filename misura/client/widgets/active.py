#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
from time import time
import collections
import threading
import math

from misura.canon.logger import Log as logging
from misura.canon.csutil import lockme
from .. import network
from .. import units
from ..clientconf import confdb
from .. import _
from ..live import registry


from PyQt4 import QtGui, QtCore

from misura.client.parameters import MAX, MIN


def extend_decimals(cur, default=2, extend_by=2):
    """Find out how many decimals to enable in editing for float value `num`"""
    cur = float(cur)
    if abs(cur) < 1 and abs(cur) > 1e-32:
        print 'extend_decimals for', cur
        dc = math.log(abs(1. / cur), 10)
        dc = round(abs(dc), 0)
        print 'extend_decimals for', cur, dc
        return int(dc) + extend_by
    return default


def getRemoteDev(server, devpath):
    if devpath == 'None':
        return False, None
    sp = server.searchPath(devpath)
    logging.debug('%s %s %s', 'Getting Remote Dev', sp, devpath)
    if not sp:
        return False, None
    logging.debug('%s %s', 'Getting Remote Dev', sp)
    dev = server.toPath(sp)
    logging.debug('%s %s %s', 'Got Remote Dev', devpath, dev)
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


class RunMethod(QtCore.QRunnable):
    runnables = []
    step = 2

    def __init__(self, func, *args, **kwargs):
        QtCore.QRunnable.__init__(self)
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.pid = 'Waiting: {}'.format(func)
        logging.debug(
            'RunMethod initialized %s %s %s', self.func, self.args, self.kwargs)
        self.runnables.append(self)

    def run(self):
        registry.tasks.jobs(self.step, self.pid)
        logging.debug(
            'RunMethod.run %s %s %s', self.func, self.args, self.kwargs)
        registry.tasks.job(1, self.pid, self.pid)
        r = self.func(*self.args, **self.kwargs)
        logging.debug('RunMethod.run result %s', r)
        self.runnables.remove(self)
        registry.tasks.done(self.pid)


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
        self.prop = prop

        for p in 'current', 'type', 'handle', 'factory_default', 'attr', 'readLevel', 'writeLevel', 'name':
            setattr(self, p, prop[p])
        write_level = getattr(self.remObj, '_writeLevel', 5)
        self.readonly = (self.type == 'ReadOnly') or (
            'ReadOnly' in self.attr) or (write_level < self.writeLevel)

        self.hard = 'Hard' in self.attr
        self.hot = 'Hot' in self.attr
        self.label = _(self.name)

        # Update the widget whenever the manager gets reconnected
        network.manager.connect(network.manager, QtCore.SIGNAL(
            'connected()'), self.reconnect, QtCore.Qt.QueuedConnection)

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
#       print 'emitChanged', self.label

#    def emitSelfChanged(self, nval):
#        """Called from diff threads"""
#        self.emit(QtCore.SIGNAL('selfchanged'), nval)

    def emitError(self, msg):
        msg = self.tr(msg)
        logging.debug('%s', msg)

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
            logging.debug('Not setting',self.handle, repr(val))
            return True
        out = self.remObj.set(self.handle,  val)
        logging.debug('%s %s %s %s', 'Active.set', self.handle, repr(val), out)
        self.get()
        
    def set_raw(self, val):
        """Set value directly, without adapt2srv conversion"""
        self.remObj.set(self.handle, val)
        self.get()

    def _get(self, rem=None):
        self.register()
        if rem is None:
            self.emitChanged()
        elif self.current != rem:
            self.current = rem
            self.emitChanged()

    def _check_flags(self, *args):
        rem_flags = self.remObj.getFlags(self.handle, *args)
        if rem_flags and (rem_flags['enabled'] is not None):
            self.enable_check.setChecked(rem_flags['enabled'])

    def _call_function_then_emitchanged_and_checkflags(self, function, *args):
        rem = function(self.handle, *args)
        self._get(rem)
        self._check_flags(*args)
        return rem

    @lockme
    def get(self, *args):
        self._call_function_then_emitchanged_and_checkflags(
            self.remObj.get, *args)

    @lockme
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


class ActiveObject(Active, QtCore.QObject):

    def __init__(self, server, remObj, prop, parent=None, context='Option'):
        Active.__init__(self, server, remObj, prop, context)
        QtCore.QObject.__init__(self, parent=parent)
        self.connect(self, QtCore.SIGNAL('destroyed()'),
                     self.unregister, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('selfchanged'), self._get, QtCore.Qt.QueuedConnection)
        self.connect(
            self, QtCore.SIGNAL('selfchanged()'), self._get, QtCore.Qt.QueuedConnection)

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
        self.setMaximumWidth(30)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)

    def setMenu(self, menu):
        self.menu = menu

    def start_drag(self):
        """Begin a drag and drop event"""
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()
        mimeData.setData("text/plain", self.prop['kid'])
        drag.setMimeData(mimeData)
        drag.exec_()

    def show_menu(self, event):
        """Show associated menu"""
        if self.menu:
            self.menu.popup(event.globalPos())
            self.clicked.emit()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.start_drag()
        elif self.menu and event.button() == QtCore.Qt.LeftButton:
            self.show_menu(event)
        return QtGui.QLabel.mousePressEvent(self, event)


class LabelWidget(QtGui.QLabel):

    def __init__(self, active):
        self.active = active
        prop = active.prop
        QtGui.QLabel.__init__(
            self, unicode(_(prop['name'], context='Option')), parent=active)
        self.prop = prop

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
        logging.debug('%s %s', 'dragEnterEvent', event.mimeData())
        event.acceptProposedAction()
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()


class ActiveWidget(Active, QtGui.QWidget):

    """Graphical representation of an Option object"""
    bmenu_hide = True
    """Auto-hide menu button"""
    get_on_enter = True
    """Update on mouse enter"""

    def __init__(self, server, remObj, prop, parent=None, context='Option'):
        Active.__init__(self, server, remObj, prop, context)
        QtGui.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.lay = QtGui.QHBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.setLayout(self.lay)
        self.label = self.tr(self.name)
        self.label_widget = LabelWidget(self)  # Info label
        self.emenu = QtGui.QMenu(self)
        self.presets_menu = QtGui.QMenu(_('Presets'), parent=self)
        self.presets_menu.aboutToShow.connect(self.build_presets_menu)
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

    @lockme
    def closeEvent(self, event):
        self.menu_timer.stop()
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
            logging.debug('%s %s', 'Setting csunit to', u)
            r = self.remObj.setattr(self.handle, 'csunit', u)
            self.prop['csunit'] = u
            logging.debug('%s %s', 'result', r)
        self.set_label()
        self.update_menu()
        self.update()

    def set_flags(self, foo=0):
        out = {}
        for key, act in self.flags.iteritems():
            out[key] = act.isChecked() > 0
        if self.enable_check:
            out['enabled'] = self.enable_check.isChecked()

        logging.debug('%s %s', 'updating flags', out)
        r = self.remObj.setFlags(self.handle, out)
        return r

    def update_menu(self):
        flags = self.remObj.getFlags(self.handle)
        logging.debug('%s %s', 'remote flags', flags)
        for key, act in self.flags.iteritems():
            if not flags.has_key(key):
                logging.debug('%s %s %s', 'Error, key disappeared', key)
            act.setChecked(flags[key] * 2)
            if key == 'enabled':
                self.enable_check.setChecked(flags[key] * 2)

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
                    encheck.setChecked(val * 2)
                    self.connect(
                        encheck, QtCore.SIGNAL('stateChanged(int)'), self.set_flags)
                    self.lay.addWidget(encheck)
                    self.enable_check = encheck

        # Units sub-menu
        self.units = {}
        u = self.unit
        u1 = ''
        if u != 'None' and type(u) == type(''):
            un = self.emenu.addMenu(_('Units'))
            kgroup, f, p = units.get_unit_info(u, units.from_base)
            same = units.from_base.get(kgroup, {u: lambda v: v}).keys()
            logging.debug('%s %s', kgroup, same)
            for u1 in same:
                p = functools.partial(self.set_unit, u1)
                act = un.addAction(_(u1), p)
                act.setCheckable(True)
                if u1 == u:
                    act.setChecked(True)
                self.units[u1] = (act, p)

        self.emenu.addAction(_('Set default value'), self.set_default)
        self.emenu.addAction(_('Check for modification'), self.get)
        self.emenu.addAction(_('Option Info'), self.show_info)
        if self.remObj.compare_presets is not None:
            self.emenu.addMenu(self.presets_menu)
        #self.emenu.addAction(_('Online help for "%s"') % self.handle, self.emitHelp)
        # Units button
        self.bmenu = LabelUnit(self.prop, self)
        self.bmenu.setMenu(self.emenu)
        self.bmenu.setSizePolicy(
            QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.bmenu.clicked.connect(self.update_menu)
        if not self.unit:
            self.bmenu.hide()
        self.set_label()
        self.lay.addWidget(self.bmenu)

    
    def build_presets_menu(self):
        self.presets = {}
        self.presets_menu.clear()
        comparison = self.remObj.compare_presets(self.handle)
        for preset, val in comparison.iteritems():
            if preset == '***current***':
                continue
            value = repr(val)
            value = (value[:15] + '..') if len(value) > 15 else value
            label = '{}: {}'.format(preset, value)
            print 'preset action',preset, val
            p = functools.partial(self.set_raw, val)
            self.presets_menu.addAction(label, p)
            self.presets[preset] = (p, val)
    
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
        """Update the widget anytime the mouse enters its area.
        This must be overridden in one-shot widgets, like buttons."""
        if self.get_on_enter:
            self.get()
        # Show only if label_widget is not visible
        if not self.label_widget.isVisible():
            self.bmenu.show()
        return QtGui.QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
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

    def emitChanged(self):
        """Il valore corrente si è modificato sul server"""
        # aggiorno anche gli attributi
        Active.emitChanged(self)
        self.emit(QtCore.SIGNAL('changed'), self.current)

    def emitError(self, msg):
        Active.emitError(self, msg)
        self.emit(QtCore.SIGNAL('error(QString)'), msg)

    def showEvent(self, e):
        self.register()
        return QtGui.QWidget.showEvent(self, e)

    def hideEvent(self, e):
        self.unregister()
        return QtGui.QWidget.hideEvent(self, e)

    def receive_drop(self, event):
        """Receive a drop event from any sub widget"""
        return

    def dropEvent(self, event):
        self.receive_drop(event)
        return QtGui.QWidget.dropEvent(self, event)

    def dragEnterEvent(self, event):
        logging.debug('%s %s', 'dragEnterEvent', event.mimeData())
        event.acceptProposedAction()
        if event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def show_info(self):
        prop = self.prop
        logging.debug('%s', prop)
        t = '<h1> Option: %s </h1>' % prop.get('name', 'Object')

        for k, v in prop.iteritems():
            t += '<b>{}</b>: {}<br/>'.format(k, v)

        info_dialog(t, parent=self)
