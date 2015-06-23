#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Plot persistence on hdf files"""
from misura.canon.logger import Log as logging
from .. import _
import functools
from PyQt4 import QtGui, QtCore
import cStringIO

class SavePlotMenu(QtGui.QMenu):
	"""Available object versions menu"""
	plotChanged=QtCore.pyqtSignal(('QString'))
	current_plot_id=False
	doc=False
	
	def __init__(self, doc, parent=None):
		QtGui.QMenu.__init__(self,parent=parent)
		self.setTitle(_('Plots'))
		self.doc=doc
		self.redraw()
		self.connect(self,QtCore.SIGNAL('aboutToShow()'),self.redraw)
		
	@property
	def proxy(self):
		if not self.doc:
			return False
		return self.doc.proxy
		
	def redraw(self):
		self.clear()
		vd=self.proxy.get_plots()
		logging.debug('Got info %s', vd)
		if vd is None:
			return
		logging.debug('Current plot %s', self.current_plot_id)
		self.loadActs=[]
		for v,info in vd.iteritems():
			logging.debug('Found plot %s %s', v, info)
			p=functools.partial(self.load_plot,v)
			act=self.addAction(' - '.join(info),p)
			act.setCheckable(True)
			if v==self.current_plot_id:
				act.setChecked(True)
			# Keep in memory
			self.loadActs.append((p,act))		
		act=self.addAction(_('Save new plot'),self.new_plot)
		self.loadActs.append((self.new_plot,act))
		act=self.addAction(_('Overwrite current plot'),self.save_plot)
		self.loadActs.append((self.save_plot,act))
		if len(vd)==0:
			act.setEnabled(False)
		
	def load_plot(self,v):
		"""Load selected plot"""
		text=self.proxy.get_plot(v)
		print text
		return True
		
	def save_plot(self,name=False):
		"""Save overwrite plot in current name"""
		if not name:
			name=self.current_plot_id
		text=cStringIO.StringIO()
		self.doc.saveToFile(text)
		text=text.getvalue()
		print 'saving',text
		r=self.proxy.save_plot(text)
		return r
		
	def new_plot(self):
		"""Create a new plot"""
		name,st=QtGui.QInputDialog.getText(self, _('Plot name'), _('Choose a name for this plot'))
		if not st: 
			return False
		r=self.save_plot(name)
		if r:
			self.current_plot_id=name


		
