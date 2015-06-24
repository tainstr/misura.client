#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Plot persistence on hdf files"""
import cStringIO
import os
import functools

from veusz import document
from veusz.utils import pixmapAsHtml
from misura.canon.logger import Log as logging
from misura.canon.csutil import validate_filename
from .. import _

from PyQt4 import QtGui, QtCore


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
		self.plots={}
		
	@property
	def proxy(self):
		if not self.doc:
			return False
		return self.doc.proxy
		
	def redraw(self):
		self.clear()
		vd=self.proxy.get_plots(render=True)
		self.plots=vd
		if vd is None:
			return
		logging.debug('Current plot %s', self.current_plot_id)
		self.loadActs=[]
		for v,info in vd.iteritems():
			logging.debug('Found plot %s %s', v, info[:2])
			p=functools.partial(self.load_plot,v)
			act=self.addAction(' - '.join(info[:2]),p)
			act.setCheckable(True)
			if info[2]:
				pix=QtGui.QPixmap()
				pix.loadFromData(info[2],'JPG')
				tooltip = "<html>{}</html>".format(pixmapAsHtml(pix))
				act.setToolTip(tooltip)
			if v==self.current_plot_id:
				act.setChecked(True)
			# Keep in memory
			self.loadActs.append((p,act))
		if len(vd)>0:
			self.addSeparator()		
		act=self.addAction(_('Save new plot'),self.new_plot)
		self.loadActs.append((self.new_plot,act))
		act=self.addAction(_('Overwrite current plot'),self.save_plot)
		self.loadActs.append((self.save_plot,act))
		if len(vd)==0:
			act.setEnabled(False)
			
	def preview(self,plot_id):
		print 'PREVIEW',plot_id
		img=self.plots[plot_id][2]
		pix=QtGui.QPixmap()
		pix.loadFromData(img,'JPG')
		self.lbl=QtGui.QLabel()
		self.lbl.setPixmap(pix)
		self.lbl.show()
		
		
	def load_plot(self,plot_id):
		"""Load selected plot"""
		text=self.proxy.get_plot(plot_id)
		#TODO: replace with tempfile
		tmp='tmp_load_file.vsz'
		open(tmp,'w').write(text)
		self.doc.load(tmp)
		os.remove(tmp)
		self.current_plot_id=plot_id
		
	def save_plot(self,name=False,page=1):
		"""Save overwrite plot in current name"""
		if not name:
			plot_id=self.current_plot_id
		else: 
			plot_id=validate_filename(name,bad=[' '])
		text=cStringIO.StringIO()
		self.doc.saveToFile(text)
		text=text.getvalue()
		ci=document.CommandInterface(self.doc)
		tmp='tmp_veusz_render.jpg'
		ci.Export(tmp,page=page)
		render=open(tmp).read()
		r=self.proxy.save_plot(text, plot_id=plot_id, title=name,render=render,render_format='jpg')
		os.remove(tmp)
		return r
		
	def new_plot(self):
		"""Create a new plot"""
		#TODO: ask for render and pagenumber 
		name,st=QtGui.QInputDialog.getText(self, _('Plot name'), _('Choose a name for this plot'))
		if not st: 
			return False
		r=self.save_plot(name)
		if r:
			self.current_plot_id=name
			
	def event(self,ev):
		"""Tooltip handling"""
		if ev.type()==QtCore.QEvent.ToolTip:
			QtGui.QToolTip.showText(ev.globalPos(),self.activeAction().toolTip())
		else:
			QtGui.QToolTip.hideText()
		return QtGui.QMenu.event(self,ev)


		
