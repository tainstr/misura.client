#!/usr/bin/python
# -*- coding: utf-8 -*-
# CHIARIRE QUESTI IMPORT!!!
from PyQt4 import QtGui, QtCore
from misura.client import _
import network
from clientconf import confdb
from live import registry
import socket

from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from network import wake_on_lan
from livelog import LiveLog

def auto_address(addr):
    if not addr.startswith('https://'):
        addr = 'https://'+addr
        if not addr.endswith('/RPC'):
            if not addr.endswith(':3880'):
                addr += ':3880'
            addr += '/RPC'
    return addr

def addrConnection(addr, user=False, password=False, mac=False):
    addr = auto_address(addr)
    if False in [user, password]:
        user, password = confdb.get_from_key('recent_server', addr)[1:3]
    lw = LoginWindow(addr, user, password, globalconn=False)
    try:
        login = lw.tryLogin(user, password, mac)
    except socket.errno.ECONNREFUSED:
        print 'Connection refused'
        raise
    except:
        login = False
    if not login:
        lw.exec_()
    return lw.obj


class Inc(object):
    n = 0

    def i(self):
        self.n += 1
        return self.n


fail = _('Login Failed.')
class LoginWindow(QtGui.QDialog):
    obj = False
    login_failed = QtCore.pyqtSignal()
    login_succeeded = QtCore.pyqtSignal()

    def __init__(self, addr, user='username', password='password', mac='', globalconn=True, parent=None, context='Local'):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Login Required')
        self.lay = QtGui.QGridLayout(self)
        self.setLayout(self.lay)
        self.addr = addr
        self.mac = mac
        self.userLbl = QtGui.QLabel(_('User Name') + ':')
        self.pwdLbl = QtGui.QLabel(_('Password') + ':')
        self.user = QtGui.QLineEdit(user)
        self.password = QtGui.QLineEdit(password)
        self.password.setEchoMode(QtGui.QLineEdit.Password)
        self.ckSave = QtGui.QCheckBox(_('Save login'), self)
        from misura.client import iutils
        self.ckSave.setCheckState(2 * confdb['saveLogin'])
        self.ok = QtGui.QPushButton('Ok')
        self.ko = QtGui.QPushButton(_('Cancel'))
        self.connect(self.ok, QtCore.SIGNAL('clicked()'), self.tryLogin)
        self.connect(self.ko, QtCore.SIGNAL('clicked()'), self.reject)
        self.lay.addWidget(QtGui.QLabel('Destination:'), 1, 0)
        self.lay.addWidget(QtGui.QLabel(self.addr), 1, 1)
        self.lay.addWidget(self.userLbl, 2, 0)
        self.lay.addWidget(self.user, 2, 1)
        self.lay.addWidget(self.pwdLbl, 3, 0)
        self.lay.addWidget(self.password, 3, 1)
        self.lay.addWidget(self.ok, 4, 0)
        self.lay.addWidget(self.ko, 4, 1)
        self.lay.addWidget(self.ckSave, 5, 1)
        self.obj = False
        if globalconn:
            self.fConnect = network.getConnection
        else:
            self.fConnect = network.simpleConnection
        self.user.setFocus()

    def tryLogin(self, user='', password='', mac=False, ignore=False):
        if user == '':
            user = str(self.user.text())
        if password == '':
            password = str(self.password.text())
        if mac:
            self.mac = mac
        logging.debug('WAKE ON LAN?', repr(self.mac))
        if self.mac:
            map(wake_on_lan, self.mac.split('\n'))
        save = bool(self.ckSave.checkState())
        st, self.obj = self.fConnect(self.addr, user, password, self.mac, save)
        self.ignore = ignore
        
        if st:
            self.login_succeeded.emit()
            self.done(0)
            return self.obj
        else:
            self.obj = False
            self.msg = 'Connection Error'
            if self.obj:
                self.msg = self.obj._error
            logging.error(self.msg)
            self.login_failed.emit()
        return False

# TODO: migliorare stile e gestire con confdb anziché con lista in
# network.manager.


class ServerWidget(QtGui.QWidget):

    def __init__(self, info, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.info = info
        self.lay = QtGui.QVBoxLayout(self)
        self.setLayout(self.lay)
#		self.setMaximumHeight(200)
#		self.setMinimumHeight(200)
#		self.setMinimumWidth(600)
        self.grid = QtGui.QWidget(self)
        self.glay = QtGui.QGridLayout(self.grid)
        self.grid.setLayout(self.glay)
        self.label = info.name + ' @' + info.addr
        lbl = lambda txt, x, y: self.glay.addWidget(QtGui.QLabel(txt), x, y)
        r = Inc()
        cap = ', '.join(info.cap)
        lbl('Name:', r.i(), 0)
        lbl(info.name, r.n, 1)
        lbl('Serial:', r.n, 2)
        lbl(info.serial, r.n, 3)
        lbl('Address:', r.i(), 0)
        lbl(info.addr, r.n, 1)
        lbl('IP:', r.n, 2)
        lbl(str(info.ip), r.n, 3)
        lbl('Host:', r.i(), 0)
        lbl(info.host, r.n, 1)
        lbl('Capabilities:', r.n, 2)
        lbl(cap, r.n, 3)
        lbl('Port:', r.i(), 0)
        lbl(str(info.port), r.n, 1)
        lbl('User:', r.n, 2)
        lbl(info.user, r.n, 3)
        self.lay.addWidget(self.grid)
        self.button = QtGui.QPushButton(_('Connect'), self)
        self.lay.addWidget(self.button)
        self.connect(
            self.button, QtCore.SIGNAL('pressed()'), self.doConnection)
        self.menu = QtGui.QMenu(self)
        self.menu.addAction('Connect', self.doConnection)
        self.connect(
            self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)

    def doConnection(self):
        obj = addrConnection(self.info.addr)
        if not obj:
            return
        network.setRemote(obj)

    def showMenu(self, pt):
        self.menu.popup(self.mapToGlobal(pt))


class ServerSelector(QtGui.QToolBox):

    """Presents and keeps updated a list of available servers"""

    def __init__(self, parent=None, context='Local'):
        QtGui.QToolBox.__init__(self, parent)
        self.connect(network.manager, QtCore.SIGNAL(
            'found(QString)'), self.redraw, QtCore.Qt.QueuedConnection)
        self.connect(network.manager, QtCore.SIGNAL(
            'lost(QString)'), self.redraw, QtCore.Qt.QueuedConnection)
        self.label = _('Server Selector')
        self.redraw()

    def redraw(self):
        logging.debug('redraw')
        while True:
            wg = self.currentWidget()
            idx = self.currentIndex()
            if wg in [0, None]:
                break
            wg.close()
            del wg
            self.removeItem(idx)

        for key, srv in network.manager.servers.iteritems():
            wg = ServerWidget(srv, self)
            self.addItem(wg, wg.label)
        self.addItem(
            ServerWidget(network.ess, self), 'Expert System Solutions Simulation Server')


class ConnectionStatus(QtGui.QWidget):

    def __init__(self, parent=None, context='Local'):
        QtGui.QWidget.__init__(self, parent)
        self.label = _('Connection Status')
        self.setWindowTitle(self.label)
        self.lay = QtGui.QVBoxLayout()
        self.setLayout(self.lay)
        self.connect(network.manager, QtCore.SIGNAL(
            'connected()'), self.displayServerInfo)
        self.addr = QtGui.QLabel()
        self.lay.addWidget(self.addr)
        self.displayServerInfo()

        self.log = LiveLog(self)
        self.lay.addWidget(self.log)

        self.echo = QtGui.QLineEdit(self)
        self.echo.setPlaceholderText(_("Test Echo Logging"))
        self.echo.setMaxLength(50)
        self.lay.addWidget(self.echo)
        self.connect(
            self.echo, QtCore.SIGNAL('returnPressed()'), self.sendEcho)

    def sendEcho(self):
        r = network.manager.remote.send_log(str(self.echo.text()))
        self.log.update()
        self.echo.setText('')

    def displayServerInfo(self):
        if network.manager.addr == '':
            self.addr.setText('No server connected')
            return
        else:
            self.addr.setText('Connected Server: ' + str(network.manager.addr))

