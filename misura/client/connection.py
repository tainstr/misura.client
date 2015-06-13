#!/usr/bin/python
# -*- coding: utf-8 -*-
# CHIARIRE QUESTI IMPORT!!!
from PyQt4 import QtGui,QtCore
from widgets.active import Autoupdater
from misura.client import _
import network
from clientconf import confdb
from live import registry

from misura.canon.logger import Log as logging

def getConnection(srv):
	lw=LoginWindow(srv.addr, srv.user, srv.password)
	login=lw.tryLogin(srv.user, srv.password)
	if not login: lw.exec_()
	
def addrConnection(addr,user=False,password=False):
	if False in [user,password]:
		user,password=confdb.getUserPassword(addr)
	lw=LoginWindow(addr, user, password, globalconn=False)
	try:
		login=lw.tryLogin(user, password)
	except: 
		login=False
	if not login: 
		lw.exec_()
	return lw.obj

class Inc(object):
	n=0
	def i(self):
		self.n+=1 
		return self.n

class LoginWindow(QtGui.QDialog):
	def __init__(self, addr, user='username', password='password', globalconn=True, parent=None, context='Local'):
		QtGui.QDialog.__init__(self, parent)
		self.setWindowTitle('Login Required')
		self.lay=QtGui.QGridLayout(self)
		self.setLayout(self.lay)
		self.addr=addr
		self.userLbl=QtGui.QLabel(_('User Name')+':')
		self.pwdLbl=QtGui.QLabel(_('Password:')+':')
		self.user=QtGui.QLineEdit(user)
		self.password=QtGui.QLineEdit(password)
		self.ckSave=QtGui.QCheckBox(_('Save login'),self)
		from misura.client import iutils
		self.ckSave.setCheckState(2*confdb['saveLogin'])
		self.ok=QtGui.QPushButton('Ok')
		self.ko=QtGui.QPushButton(_('Cancel'))
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
		self.obj=False
		if globalconn:
			self.fConnect=network.getConnection
		else:
			self.fConnect=network.simpleConnection
		self.user.setFocus()

	def tryLogin(self, user='', password='', ignore=False):
		if user=='': user=str(self.user.text())
		if password=='': password=str(self.password.text())
		save=bool(self.ckSave.checkState())
		st,self.obj=self.fConnect(self.addr, user, password, save)
		if st:
			self.done(0)
			return self.obj
		elif not ignore:
			msg='Error'
			if self.obj is not None:
				msg=self.obj._error
			QtGui.QMessageBox.warning(self, 'Login Failed', msg)
		
		return False

#TODO: migliorare stile e gestire con confdb anziché con lista in network.manager.
class ServerWidget(QtGui.QWidget):
	def __init__(self,info,parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.info=info
		self.lay=QtGui.QVBoxLayout(self)
		self.setLayout(self.lay)
#		self.setMaximumHeight(200)
#		self.setMinimumHeight(200)
#		self.setMinimumWidth(600)
		self.grid=QtGui.QWidget(self)
		self.glay=QtGui.QGridLayout(self.grid)
		self.grid.setLayout(self.glay)
		self.label=info.name+' @'+info.addr
		lbl=lambda txt,x,y: self.glay.addWidget(QtGui.QLabel(txt),x,y)
		r=Inc()
		cap=', '.join(info.cap)
		lbl('Name:',r.i(),0)	; 	lbl(info.name,r.n,1)	;	lbl('Serial:',r.n,2)	; lbl(info.serial,r.n,3)
		lbl('Address:',r.i(),0)	; 	lbl(info.addr,r.n,1)	;	lbl('IP:',r.n,2)	; lbl(str(info.ip),r.n,3)
		lbl('Host:',r.i(),0)	;	lbl(info.host,r.n,1)	;	lbl('Capabilities:',r.n,2)	; lbl(cap,r.n,3)
		lbl('Port:',r.i(),0)	; 	lbl(str(info.port),r.n,1);	lbl('User:',r.n,2)	; lbl(info.user,r.n,3)
		self.lay.addWidget(self.grid)
		self.button=QtGui.QPushButton(_('Connect'),self)
		self.lay.addWidget(self.button)
		self.connect(self.button,QtCore.SIGNAL('pressed()'),self.doConnection)
		self.menu=QtGui.QMenu(self)
		self.menu.addAction('Connect',self.doConnection)		
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)

	def doConnection(self):
		obj=addrConnection(self.info.addr)
		if not obj: return
		network.setRemote(obj)
		
	def showMenu(self, pt):
		self.menu.popup(self.mapToGlobal(pt))
		
class ServerSelector(QtGui.QToolBox):
	"""Presents and keeps updated a list of available servers"""
	def __init__(self, parent=None, context='Local'):
		QtGui.QToolBox.__init__(self, parent)
		self.connect(network.manager, QtCore.SIGNAL('found(QString)'), self.redraw, QtCore.Qt.QueuedConnection)
		self.connect(network.manager, QtCore.SIGNAL('lost(QString)'), self.redraw, QtCore.Qt.QueuedConnection)
		self.label=_('Server Selector')
		self.redraw()

	def redraw(self):
		logging.debug('%s', 'redraw')
		while True:
			wg=self.currentWidget()
			idx=self.currentIndex()
			if wg in [0,None]: break
			wg.close(); del wg
			self.removeItem(idx)
		
		for key, srv in network.manager.servers.iteritems():
			wg=ServerWidget(srv,self)
			self.addItem(wg,wg.label)
		self.addItem(ServerWidget(network.ess,self),'Expert System Solutions Simulation Server')
		
		


class ConnectionStatus(QtGui.QWidget):
	def __init__(self, parent=None, context='Local'):
		QtGui.QWidget.__init__(self, parent)
		self.label=_('Connection Status')
		self.setWindowTitle(self.label)
		self.lay=QtGui.QVBoxLayout()
		self.setLayout(self.lay)
		self.connect(network.manager, QtCore.SIGNAL('connected()'), self.displayServerInfo)
		self.addr=QtGui.QLabel()
		self.lay.addWidget(self.addr)
		self.displayServerInfo()
		
		self.log=LiveLog(self)
		self.lay.addWidget(self.log)
		
		self.echo=QtGui.QLineEdit(self)
		self.echo.setPlaceholderText(_("Test Echo Logging"))
		self.echo.setMaxLength(50)
		self.lay.addWidget(self.echo)
		self.connect(self.echo,QtCore.SIGNAL('returnPressed()'),self.sendEcho)
		
	def sendEcho(self):
		r=network.manager.remote.send_log(str(self.echo.text()))
		self.log.update()
		self.echo.setText('')

	def displayServerInfo(self):
		if network.manager.addr=='':
			self.addr.setText('No server connected')
			return
		else:
			self.addr.setText('Connected Server: '+str(network.manager.addr))

from time import strftime, time
from datetime import datetime

class LiveLog(QtGui.QTextEdit, Autoupdater):
	def __init__(self, parent=None):
		QtGui.QTextEdit.__init__(self, parent)
		self.setReadOnly(True)
		self.setLineWrapMode(self.NoWrap)
		self.nlog=0
		self.label=_('Log')
		self.menu=QtGui.QMenu(self)
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		Autoupdater.__init__(self, callback=self.update, menu=self.menu)
		if registry!=None:
			self.connect(registry, QtCore.SIGNAL('log()'), self.slotUpdate, QtCore.Qt.QueuedConnection)
		self.slotUpdate()
		self.setFont(QtGui.QFont('TypeWriter',  7, 50, False))

	def slotUpdate(self):
		logging.debug('%s', 'LiveLog.slotUpdate')
		if registry==None:
			logging.debug('%s', 'No registry')
			return
		buf=registry.log_buf
		if len(buf)<=self.nlog:
			logging.debug('%s', 'No new log')
			return
		txt=''
		for line in buf[self.nlog:]:
			if type(line)!=type([]): continue
			if len(line)<2: continue
			st=datetime.fromtimestamp(line[0]).strftime('%X')
			p=line[1]
			fmsg=line[3]
			txt+='[%s!%-2i] %s\n' % (st,p,  fmsg)
		txt=txt.rstrip('\n')
		self.append(txt)
		txt=self.toPlainText()
		if len(txt)>5000:
			txt=txt[-3000:]
			self.setPlainText(txt)
			self.moveCursor(QtGui.QTextCursor.End)
			self.moveCursor(QtGui.QTextCursor.StartOfLine)
			self.ensureCursorVisible()
		self.nlog=len(buf)

	def update(self):
		logging.debug('%s', 'LiveLog.update')
		registry.updateLog()
