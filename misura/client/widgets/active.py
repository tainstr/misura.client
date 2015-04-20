#!/usr/bin/python
# -*- coding: utf-8 -*-
from traceback import print_exc
import functools
from time import sleep, time
import collections

from misura.client import network
from misura.client import units
from misura.client.clientconf import confdb
from misura.client.linguist import Linguist
from misura.client.live import registry

from PyQt4 import QtGui, QtCore

from misura.client.parameters import MAX,MIN


def getRemoteDev(server, devpath):
	if devpath=='None': return False, None
	sp=server.searchPath(devpath)
	print 'Getting Remote Dev',sp,devpath
	if not sp: return False, None
	print 'Getting Remote Dev',sp
	dev=server.toPath(sp)
	print 'Got Remote Dev',devpath,dev
	return True, dev
	
def info_dialog(text, title='Info', parent=None):
	"""Show html text in a simple dialog window."""
	dial=QtGui.QDialog(parent)
	dial.setWindowTitle(title)
	lay=QtGui.QVBoxLayout()
	txt=QtGui.QTextBrowser()
	txt.setHtml(text)
	lay.addWidget(txt)
	dial.setLayout(lay)
	dial.resize(400, 400)
	dial.exec_()


		
class RunMethod(QtCore.QRunnable):
	runnables=[]
	
	def __init__(self, func, *args, **kwargs):
		QtCore.QRunnable.__init__(self)
		self.func=func
		self.args=args
		self.kwargs=kwargs
		print 'RunMethod initialized', self.func, self.args, self.kwargs
		self.runnables.append(self)
		
	def run(self):
		print 'RunMethod.run', self.func, self.args, self.kwargs
		r=self.func(*self.args, **self.kwargs)
		print 'RunMethod.run result', r
		self.runnables.remove(self)
		


class Active(Linguist):
	interval=200
	last_async_get=0
	force_update=False
	current=None
	"""Current server-side value"""
	def __init__(self, server, remObj, prop, context='Option', connect=True):
		Linguist.__init__(self, context)
		self.server=server
		self.remObj=remObj
		self.path=remObj._Method__name
		self.prop=prop
		
		for p in 'current', 'type', 'handle', 'factory_default', 'attr', 'readLevel', 'writeLevel', 'name', 'kid':
			setattr(self, p, prop[p])
		self.readonly=self.type=='ReadOnly' or 'ReadOnly' in self.attr
		self.hard='Hard' in self.attr
		self.hot='Hot' in self.attr
		self.label=self.tr(self.name)
		
		# Update the widget whenever the manager gets reconnected
		network.manager.connect(network.manager, QtCore.SIGNAL('connected()'), self.reconnect, QtCore.Qt.QueuedConnection)
		
		
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
		t=time()
		if t-self.last_async_get<self.interval/1000.:
			return False
		r=RunMethod(self.get)
		QtCore.QThreadPool.globalInstance().start(r)
		self.last_async_get=t
		return True
	
	def reconnect(self):
		self.remObj=getattr(network.manager.remote,  self.path)
		self.update()
		
	def emit(self, *a):
		if a[0]==QtCore.SIGNAL('selfchanged'):
			self._get(a[1])
		
	def emitHelp(self):
		parent=self.path.split('/')[0]
		url='http://www.expertsystemsolutions.it/wiki/%s/%s' % (parent, self.handle)
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

	def emitChanged(self):
		"""Current value changed server-side."""
		self.update()
		self.emit(QtCore.SIGNAL('changed'), self.current)
		self.emit(QtCore.SIGNAL('changed()'))
		self.emitOptional()
#		print 'emitChanged', self.label
		
	def emitSelfChanged(self, nval):
		"""Called from diff threads"""
		self.emit(QtCore.SIGNAL('selfchanged'), nval)

	def emitError(self, msg):
		msg=self.tr(msg)
		print msg

	def emitOptional(self):
		pass

	def adapt(self, val):
		"""Translates between GUI and server data types. It is first called by both adapt2srv() and adapt2gui() methods"""
		return val
	def adapt2gui(self, val):
		"""Translate server data types into GUI data type. 
		`val` is the server-side data value"""
		val=self.adapt(val)
		val=units.Converter.convert(self.prop.get('unit','None'),self.prop.get('csunit','None'),val)
		return val
	def adapt2srv(self, val):
		"""Translates a GUI data type into a server-side data type.
		`val` is the GUI data value (eg: widget signal Qt object)"""
		val=self.adapt(val)
		val=units.Converter.convert(self.prop.get('csunit','None'),self.prop.get('unit','None'),val)
		return val

	def set(self, val,*foo):
		"""Set a new value `val` to server. Convert val into server units."""
		val=self.adapt2srv(val)
		if val==self.current:
			print 'nothing to set'
			return True
		out=self.remObj.set(self.handle,  val)
		print 'Active.set',self.handle, repr(val),  out
		self.get()

	def _get(self, rem=None):
		self.register()
		if rem is None:
			self.emitChanged()
		elif self.current!=rem:
			self.current=rem
			self.emitChanged()

	def get(self, *args):
		rem=self.remObj.get(self.handle, *args)
		self._get(rem)
		return rem
		
	def emitSelfChanged(self, nval):
		self._get(nval)
	
	def set_default(self):
		"""Sets the remote property to its facotry_default value"""
		fd=self.prop['factory_default']
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
		self.connect(self, QtCore.SIGNAL('destroyed()'), self.unregister)
		self.connect(self, QtCore.SIGNAL('selfchanged'), self._get)
		self.connect(self, QtCore.SIGNAL('selfchanged()'), self._get)
		
	def emit(self, *a, **k):
		return QtCore.QObject.emit(self, *a, **k)
		
class LabelWidget(Linguist,QtGui.QWidget):
	def __init__(self, parent,context='Option'):
		Linguist.__init__(self, context)
		QtGui.QWidget.__init__(self,parent=parent)
		self.active=parent
		prop=parent.prop
		self.lay=QtGui.QHBoxLayout()
		self.lay.setContentsMargins(0,0,0,0)
		self.lay.setSpacing(0)
		self.setLayout(self.lay)
		
		self.menu=QtGui.QMenu(self)
		
		# Add flags to context menu
		self.flags={}
		if prop.has_key('flags'):
			for key, val in prop['flags'].iteritems():
				act=self.menu.addAction(key, self.set_flags)
				act.setCheckable(True)
				act.setChecked(val*2)
				self.flags[key]=act
				if key=='enabled':
					encheck=QtGui.QCheckBox(self)
					encheck.setChecked(val*2)
					self.connect(encheck,QtCore.SIGNAL('stateChanged(int)'),self.set_flags)
					self.lay.addWidget(encheck)
					self.enable_check=encheck
		
		# Units sub-menu
		self.units={}
		u=self.unit
		if u!='None' and type(u)==type(''):
			un=self.menu.addMenu(self.mtr('Units'))
			kgroup,f,p=units.get_unit_info(u,units.from_base)
			same=units.from_base.get(kgroup,{u:lambda v: v}).keys()
			print kgroup, same
			for u1 in same:
				p=functools.partial(self.set_unit,u1)
				act=un.addAction(self.mtr(u1),p)
				act.setCheckable(True)
				if u1==u:
					act.setChecked(True)
				self.units[u1]=(act,p)
			
			
		self.menu.addAction(self.mtr('Set default value'), parent.set_default)
		self.menu.addAction(self.mtr('Check for modification'), parent.get)
		self.menu.addAction(self.mtr('Option Info'), self.show_info)
		self.menu.addAction(self.mtr('Online help for "%s"') % parent.handle, parent.emitHelp)

		self.label=QtGui.QLabel()
		self.label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.label.connect(self.label, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		self.set_label()
		self.lay.addWidget(self.label)
		
	@property
	def unit(self):
		"""Get measurement unit for this label"""
		# First check the client-side unit
		u=self.active.prop.get('csunit',False)
		if u in ['', 'None',None, False]: u=False
		if not u:
			u=self.active.prop.get('unit',False)
		if u in ['', 'None',None, False]: u=False
		return u
		
	def show_info(self):
		prop=self.active.prop
		print prop
		t='<h1> Option: %s </h1>' % prop.get('name','Object')
		
		for k, v in prop.iteritems():
			t+='<b>{}</b>: {}<br/>'.format(k, v)
			
		info_dialog(t, parent=self)
			
	def mousePressEvent(self, event):
		if event.button() == QtCore.Qt.LeftButton:
			drag=QtGui.QDrag(self)
			mimeData=QtCore.QMimeData()
			mimeData.setData("text/plain", self.active.prop['kid'])
			drag.setMimeData(mimeData)
			drag.exec_()
			
	def set_label(self):
		"""Update label contents"""
		sym=False
		u=self.unit
		if u and isinstance(u, collections.Hashable):
			sym=units.hsymbols.get(u,False)
		msg=unicode(self.mtr(self.active.name))
		if sym:
			msg+=u' ({})'.format(sym)
		self.label.setText(msg)

	def set_unit(self,unit):
		"""Change measurement unit"""
		for u,(act,p) in self.units.iteritems():
			if u!=unit:
				act.setChecked(False)
				continue
			act.setChecked(True)
			print 'Setting csunit to',u
			r=self.active.remObj.setattr(self.active.handle,'csunit',u)
			self.active.prop['csunit']=u
			print 'result', r
		self.set_label()
		self.active.update()
		
	def showMenu(self, pt):
		parent=self.active
		flags=parent.remObj.getFlags(parent.handle)
		print 'remote flags', flags
		for key, act in self.flags.iteritems():
			if not flags.has_key(key):
				print 'Error, key disappeared', key
			act.setChecked(flags[key]*2)
			if key=='enabled':
				self.enable_check.setChecked(flags[key]*2)
		self.menu.popup(self.label.mapToGlobal(pt))
		
	def set_flags(self,foo=0):
		out={}
		for key, act in self.flags.iteritems():
			out[key]=act.isChecked()>0
		if self.enable_check:
			if self.enable_check.isChecked(): out['enabled']=True
			else: out['enabled']=False
		print 'updating flags', out
		r=self.active.remObj.setFlags(self.active.handle, out)
		self.showMenu(QtCore.QPoint())
		self.menu.hide()
		return r
				

class ActiveWidget(Active, QtGui.QWidget):
	"""Graphical representation of an Option object"""
	def __init__(self, server, remObj, prop, parent=None, context='Option'):
		Active.__init__(self, server, remObj, prop, context)
		QtGui.QWidget.__init__(self,parent)
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		self.setFocusPolicy(QtCore.Qt.StrongFocus)
		self.lay=QtGui.QHBoxLayout()
		self.lay.setContentsMargins(0,0,0,0)
		self.lay.setSpacing(0)
		self.setLayout(self.lay)
		self.label=self.tr(self.name)
		self.label_widget=LabelWidget(self)
		self.connect(self, QtCore.SIGNAL('destroyed()'), self.unregister)
		self.connect(self, QtCore.SIGNAL('selfchanged'), self._get)
		self.connect(self, QtCore.SIGNAL('selfchanged()'), self._get)
		self.connect(self, QtCore.SIGNAL('selfhide()'), self.hide)
		self.connect(self, QtCore.SIGNAL('selfshow()'), self.show)
		
	def isVisible(self):
		return QtGui.QWidget.isVisible(self)
	def emit(self, *a, **k):
		return QtGui.QWidget.emit(self, *a, **k)
		
	def enterEvent(self, event):
		"""Update the widget anytime the mouse enters its area.
		This must be overridden in one-shot widgets, like buttons."""
		self.get()
		return 

	def clear(self):
		"""Removes all widgets in this layout"""
		for i in range(self.lay.count()):
			item=self.lay.itemAt(0)
			if item==0: break
			elif item==self.label: continue
			self.lay.removeItem(item)
			w=item.widget()
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
		Active.emitError(self,msg)
		self.emit(QtCore.SIGNAL('error(QString)'), msg)

	def delWg(self, wg):
		"""Demolisce il widget"""
		idx=-1
		wg=getattr(self, wg, False)
		if wg:
			idx=self.lay.indexOf(wg)
			print 'del',idx
			wg.setVisible(False)
			self.lay.removeWidget(wg)
			wg.destroy()
			del wg
		return idx
		
	def showEvent(self, e):
		self.register()
		return QtGui.QWidget.showEvent(self, e)
		
	def hideEvent(self, e):
		self.unregister()
		return QtGui.QWidget.hideEvent(self, e)
		

class Autoupdater(QtCore.QObject):
	#FIXME: Deprecated. This is too slow. Remove dep. on LiveLog.
	def __init__(self, callback=False, menu=False, timer=False):
		if timer:
			self.timer=timer
		else:
			self.timer=QtCore.QTimer(self)
		self.timer.setInterval(3000)
		self.timer.connect(self, QtCore.SIGNAL('timeout()'), QtGui.qApp.processEvents)
		if callback:
			self.timer.connect(self.timer, QtCore.SIGNAL('timeout()'), callback)
		else:
			callback=self.callback
		if menu:
			self.menu=menu
			menu.addAction('Update now',callback)
			menu.addAction('Set update interval',self.interval)
			act=menu.addAction('Autoupdate',self.toggle_run)
			act.setCheckable(True)
			self.autoupdateAct=act
			self.connect(menu, QtCore.SIGNAL('aboutToShow()'), self.updateMenu)

	def callback(self):
		from misura.client import conf
		registry.updateCurves()

	def interval(self):
		from misura.client import conf
		w=QtGui.QInputDialog.getDouble(self, "Update interval","Seconds:", registry.interval, 0.05, 5, 2 )
		if w[1]:
			w=w[0]*1000
			self.timer.setInterval(w)
			self.emit(QtCore.SIGNAL('setInterval(int)'), w)

	def toggle_run(self):
		if confdb.updatingCurves:
			self.emit(QtCore.SIGNAL('stop'))
			confdb.updatingCurves=False
		else:
			self.emit(QtCore.SIGNAL('start'))
			confdb.updatingCurves=True

	def showMenu(self, pt):
		self.menu.popup(self.mapToGlobal(pt))

	def updateMenu(self):
		self.autoupdateAct.setChecked(confdb.updatingCurves)

