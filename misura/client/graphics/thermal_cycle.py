#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
import numpy as np
from numpy import array
from .. import _
from .. import widgets
from .. import parameters as params
import plot

from misura.canon.csutil import next_point

from PyQt4 import QtGui, QtCore

def clean_curve(dat,events=True):
	crv=[]
	for irow,ent in enumerate(dat):
		t, T, R, D=ent
		if None in ent: 
			print 'Skipping row', irow
			continue
		if isinstance(T,basestring):
			if events:
				T=str(T)
			else:
				print 'Skipping EVENT',irow
				continue

		crv.append([t*60, T])
	return crv

class ThermalCyclePlot(plot.VeuszPlot):
	"""Simple plot for thermal cycle preview"""
	
	@classmethod
	def setup(cls,cmd,graph='/time/time',
					T='tc',R='tc1',
					xT='x',yT='y',aT='y',
					xR='x1',yR='y1',aR='y1'):
		"""Setup a ThermalCyclePlot on `graph` destination"""
		cmd.SetData(xT, [])
		cmd.SetData(yT, [])
		cmd.SetData(xR, [])
		cmd.SetData(yR, [])
		
		# Temperature
		cmd.To(graph)
		cmd.Add('xy', name=T)
		cmd.Add('axis', name=aT, direction='vertical')
		cmd.Set(aT+'/autoRange','+10%')
		cmd.Set(T+'/xData', xT)
		cmd.Set(T+'/yData', yT)
		cmd.Set(T+'/yAxis', aT)
		
		# Rate
		cmd.To(graph)	
		cmd.Add('xy', name=R)
		cmd.Add('axis', name=aR, direction='vertical')
		cmd.Set(aR+'/autoRange','+10%')
		cmd.Set(R+'/xData', xR)
		cmd.Set(R+'/yData', yR)
		cmd.Set(R+'/yAxis', aR)
		
		# Axis
		cmd.To(graph)	
		cmd.Set('x/label', str(_("Time (min)")))
		cmd.Set(aT+'/label', str(_("Temperature (\deg C)")))
		cmd.Set(aT+'/Label/color', 'red')
		cmd.Set(T+'/MarkerFill/color', 'red')
		cmd.Set(T+'/PlotLine/color', 'red')
		
		cmd.Set(aR+'/label', str(_("Rate (\deg C/min)")))
		cmd.Set(aR+'/Label/color', 'blue')
		cmd.Set(aR+'/otherPosition', 1)
		cmd.Set(R+'/thinfactor', 2)
		cmd.Set(R+'/PlotLine/color', 'blue')
		cmd.Set(R+'/MarkerFill/color', 'blue')	
	
	def __init__(self, parent=None):
		plot.VeuszPlot.__init__(self, parent=parent)
		self.set_doc()
		ThermalCyclePlot.setup(self.cmd)
		self.plot.setPageNumber(2)

	
	@classmethod
	def importCurve(cls,cmd,crv,graph='/time/time',xT='x',yT='y',xR='x1',yR='y1'):
		cmd.To(graph)
		trs=array(crv).transpose()
		x=trs[0].transpose()/60.
		y=trs[1].transpose()
		cmd.SetData(xT, x)
		cmd.SetData(yT, y)
		if len(y)>1:
			y1=np.diff(y)/np.diff(x)
			y1=array([y1,y1]).transpose().flatten()
			x1=array([x,x]).transpose().flatten()[1:-1]
			print 'x1',x1
			print 'y1',y1
			cmd.SetData(yR, y1)
			cmd.SetData(xR, x1)
		else:
			cmd.SetData(yR, [])
			cmd.SetData(xR, [])			
		if len(x)>25: 
			cmd.Set('/time/time/tc/marker', 'none')
			cmd.Set('/time/time/tc1/marker', 'none')			
		
	def setCurve(self, crv):
		if len(crv)==0:
			self.hide()
			return False
		ThermalCyclePlot.importCurve(self.cmd,crv)
		self.fitSize()
		self.plot.actionForceUpdate()
		return True
			
class TimeSpinBox(QtGui.QDoubleSpinBox):
	"""SpinBox for time values editing (hours, minutes, seconds)"""
	def __init__(self, parent=None):
		QtGui.QDoubleSpinBox.__init__(self,parent)
		self.setRange(0, 10**7)
	
	def textFromValue(self, s):
		print 'textFromValue',s
		s=s*60
		h, s=divmod(s, 3600)
		m, s=divmod(s, 60)
		return '%i : %i : %.2f' % (h, m, s)
		
	def valueFromText(self, qstr):
		qstr=str(qstr).replace(' ','')
		print 'valueFromText',qstr
		if len(qstr)==0:
			print 'valueFromText: empty',qstr
			return 0.
		if ':' in qstr:
			h, m, s=qstr.split(':')
			r=int(h)*3600+int(m)*60+float(s)
		else:
			r=float(qstr)
		return r/60
		
	def setTime(self, t):
		print 'setTime',t
		self.setValue(t)
		
	def setText(self, txt):
		print 'setText',txt
		val=self.valueFromText(txt)
		self.setValue(val)
		
	def validate(self,inp,pos):
		print 'validate',inp,pos
		try: 
			self.valueFromText(inp)
			return (QtGui.QValidator.Acceptable,inp,pos)
		except:
			print 'invalid',inp,pos
			return (QtGui.QValidator.Intermediate,inp,pos)
		
# Nota: colCHK deve sempre essere l'ultima colonna (indice + alto)
colTIME=0; colTEMP=1; colRATE=2; colDUR=3; colCHK=4
class ThermalCurveModel(QtCore.QAbstractTableModel):
	"""Data model for thermal cycle editing"""
	sigModeChanged=QtCore.pyqtSignal()
	
	def __init__(self, crv=None):
		QtCore.QAbstractTableModel.__init__(self)
		self.dat=[]
		header=[]
		for s in ['Time', 'Temperature', 'Heating Rate', 'Duration', 'Checkpoint']:
			header.append(_(s))
		self.header=header
		self.mode='ramp'
		self.editable=(colTEMP, colCHK)
		
	def rowCount(self, index=QtCore.QModelIndex()):
		return len(self.dat)
		
	def columnCount(self, index=QtCore.QModelIndex()):
		return colCHK #+1 for chk
		
	def data(self, index, role=QtCore.Qt.DisplayRole):
		if not index.isValid() or not (0<= index.row()<self.rowCount()):
			return 0
		row=self.dat[index.row()]
		if role==QtCore.Qt.DisplayRole:
			return row[index.column()]
			
	def flags(self, index):
		row=index.row()
		col=index.column()
		if not index.isValid():
			return QtCore.Qt.ItemIsEditable
		# TCEv are editable only on T column
		if self.dat[row][0]<0 and col!=1:
			return QtCore.Qt.ItemIsEditable
		if row==0 and col!=colTEMP:
			return QtCore.Qt.ItemIsEditable
		if col not in self.editable:
			return QtCore.Qt.ItemIsEditable
		return QtCore.Qt.ItemFlags(QtCore.QAbstractTableModel.flags(self, index)|QtCore.Qt.ItemIsEditable)

	def setData(self, index, value, role=QtCore.Qt.EditRole):
		irow=index.row()
		icol=index.column()
		if not index.isValid() or irow<0 or irow>self.rowCount() or icol<0 or icol>colCHK:
			print 'setData: invalid line',irow,icol
			return False
		if isinstance(value,basestring) and (not value.startswith('>')):
			value=float(value)
		row=self.dat[irow]
		print 'setData:',irow,icol,value,row[icol]
		row[icol]=value
		self.dat[irow]=row
		for ir in range(irow, self.rowCount()):
			self.updateRow(ir)
		self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(irow, 0), 
		                                     self.index(self.rowCount(), self.columnCount()))
		# Emetto la durata totale del ciclo termico
		self.emit(QtCore.SIGNAL("duration(float)"), self.dat[-1][colTIME] )
		return True
		
	def insertRows(self, position, rows=1, index=QtCore.QModelIndex(),ini=False):
		print 'insertRows',position,rows,index.row()
		self.beginInsertRows(QtCore.QModelIndex(), position, position+rows-1)
		if not ini:
			ini=[0]*self.columnCount()
		for row in range(rows):
			self.dat.insert(position+row, ini)
		self.endInsertRows()
		return True
		
	def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
		self.beginRemoveRows(QtCore.QModelIndex(), position, position+rows-1)
		self.dat=self.dat[:position]+self.dat[position+rows:]
		self.endRemoveRows()
		return True
		
	def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
		if orientation!=QtCore.Qt.Horizontal:
			return 
		if role==QtCore.Qt.DisplayRole:
			return self.header[section]
		elif role==QtCore.Qt.BackgroundRole: #and section!=colCHK:
			if section in self.editable:
				return QtGui.QBrush(QtGui.QColor(10, 200, 10))
			else:
				return QtGui.QBrush(QtGui.QColor(180, 180, 180))
				
	def mode_points(self):
		self.editable=(colTIME, colTEMP)
		self.mode='points'
		self.emit(QtCore.SIGNAL("headerDataChanged(Qt::Orientation,int,int)"), QtCore.Qt.Horizontal, 0, colCHK-1)
		self.sigModeChanged.emit()
	def mode_ramp(self):
		self.editable=(colRATE, colTEMP)
		self.mode='ramp'
		self.emit(QtCore.SIGNAL("headerDataChanged(Qt::Orientation,int,int)"), QtCore.Qt.Horizontal, 0, colCHK-1)
		self.sigModeChanged.emit()
	def mode_dwell(self):
		self.editable=(colDUR, colTEMP)
		self.mode='dwell'
		self.emit(QtCore.SIGNAL("headerDataChanged(Qt::Orientation,int,int)"), QtCore.Qt.Horizontal, 0, colCHK-1)
		self.sigModeChanged.emit()
		
	def setCurve(self, crv, progressBar=False):
		self.removeRows(0, self.rowCount())
		self.insertRows(0, len(crv))
		for i, row in enumerate(crv):
			t, T=row
			# Detect TCEv
			if isinstance(T,basestring):
				self.dat[i]=[t/60.,T,0,0]
				continue
			D=0; R=0
			if i>0:
				idx, ent=next_point(crv,i-1,-1)
				if ent is False: ent=row
				t0,T0=ent
				D=(t-t0)/60.
				if T==T0: 
					R=0
				else: 
					R=(T-T0)/D
			self.dat[i]=[t/60., T, R, D]
			if progressBar:
				progressBar.setValue(i)
				#QtGui.QApplication.processEvents()
		# Segnalo che l'intera tabella è cambiata:
		self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(0, 0), 
		                                     self.index(self.rowCount(), self.columnCount()))
	
	def updateRow(self, irow):
#		if irow<1: 
#			return
		if isinstance(self.dat[irow][1],basestring):
			print 'skipping event ', irow, self.dat[irow]
			return 
		print 'updateRow',self.mode, irow
		t, T, R, D=self.dat[irow]
		pt0,ent0=next_point(self.dat,irow-1,-1)
		if ent0 is False:
			print 'skipping empty', irow, pt0, ent0
			return
		t0, T0, R0, D0=ent0
		print ent0
		if self.mode=='points':
			D=(t-t0)
			if D==0: R=0
			else:
				R=(T-T0)/D
		elif self.mode=='ramp':
			if R==0: D=0
			else:
				D=(T-T0)/R
			t=t0+D
		elif self.mode=='dwell':
			if D==0: R=0
			else:
				R=(T-T0)/D
			t=t0+D
		if D<0 or t<t0:
			print 'Impossible duration!'
			self.dat[irow]=[t0+1, T0, 0, 1]
		else:
			self.dat[irow]=[t, T, R, D]
		
	def curve(self,events=True):
		"""Format table for plotting or transmission"""
		return clean_curve(self.dat,events)



class ThermalPointDelegate(QtGui.QItemDelegate):
	"""Delegate for thermal cycle table cells"""
	def __init__(self, parent=None):
		QtGui.QItemDelegate.__init__(self, parent)
		
	def timeLimits(self, index):
		pre=index.model().index(index.row()-1, colTIME)
		pre=index.model().data(pre)
		post=index.model().index(index.row()+1, colTIME)
		post=index.model().data(post)
		if post==0: post=params.MAX
		return pre, post
		
	def createEditor(self, parent, option, index):
		mod=index.model()
		val=mod.data(index)
		wg=QtGui.QItemDelegate.createEditor(self, parent, option, index)
		if index.column()==colTIME:
			if index.row()==0:
				return QtGui.QLabel('Initial Time', parent)
			wg=TimeSpinBox(parent)
			pre, post=self.timeLimits(index)
			if val<0:
				wg.setReadOnly()
			else:
				wg.setRange(pre, post)
		elif index.column()==colTEMP:
			if isinstance(val,basestring):
				return wg

			wg=QtGui.QDoubleSpinBox(parent)
			wg.setRange(0, 1750)
			wg.setSuffix(u' \xb0C')
		elif index.column()==colRATE:
			if index.row()==0:
				return QtGui.QLabel('undefined', parent)
			wg=QtGui.QDoubleSpinBox(parent)
			wg.setRange(-500, 80)
			wg.setSuffix(u' \xb0C/min')
		elif index.column()==colDUR:
			if index.row()==0:
				return QtGui.QLabel('undefined', parent)
			wg=TimeSpinBox(parent)
			wg.setRange(0, params.MAX)
			
		return wg
			
	def setEditorData(self, editor, index):
		# First row is not editable
		col=index.column()
		if index.row()==0 and col in [colTIME,colCHK]:
			print 'row0 is not editable'
			return 
		mod=index.model()
		val=mod.data(index)
		if colTIME<=col<=colDUR:
			if hasattr(editor, 'setValue'):
				editor.setValue(val)
			else:
				editor.setText(val)
		else:
			QtGui.QItemDelegate.setEditorData(self, editor, index)
	
	def setModelData(self, editor, model, index):
		col=index.column()
		# first row is not editable
		if index.row()==0 and col!=colTEMP: 
			print 'setModelData: First row is not editable',index.row(),index.column()
			return	
		val=None
		if hasattr(editor,'value'):
			val=editor.value()
			print 'editor value',val
		elif hasattr(editor,'text'):
			val=editor.text()
			print 'editor text',val
			if hasattr(editor,'valueFromText'):
				val=editor.valueFromText(val)
				print 'editor valueFromText',val
		if val is not None:
			print 'setModelData',val,index.row(),index.column()
			model.setData(index, val, QtCore.Qt.DisplayRole)
		else:
			QtGui.QItemDelegate.setModelData(self, editor, model, index)
			

class ThermalCurveTable(QtGui.QTableView):
	"""Table view of a thermal cycle."""
	def __init__(self, parent=None):
		QtGui.QTableView.__init__(self, parent)
		self.curveModel=ThermalCurveModel()
		self.setModel(self.curveModel)
		self.setItemDelegate(ThermalPointDelegate(self))
		self.selection=QtGui.QItemSelectionModel(self.model())
		self.setSelectionModel(self.selection)
		
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.connect(self, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showMenu)
		self.menu=QtGui.QMenu(self)
		m=self.menu
		m.addAction(_('Insert point'), self.newRow)
		m.addAction(_('Insert checkpoint'), self.newCheckpoint)
		m.addAction(_('Insert movement'), self.newMove)
		a=m.addAction(_('Insert parametric heating'), self.newParam)
		a.setEnabled(False)
		m.addAction(_('Remove current row'), self.delRow)
		m.addSeparator()
		self.rti=m.addAction(_('Rate/Temperature mode'), self.curveModel.mode_ramp)
		self.tti=m.addAction(_('Time/Temperature mode'),self.curveModel.mode_points)
		self.dti=m.addAction(_('Duration/Temperature mode'), self.curveModel.mode_dwell)
		self.curveModel.sigModeChanged.connect(self.updateMenu)
		self.connect(self.menu, QtCore.SIGNAL('aboutToShow()'), self.updateMenu)
		for act in self.rti, self.tti, self.dti:
			act.setCheckable(True)
		self.curveModel.mode_ramp()
		
	def showMenu(self, pt):
		self.menu.popup(self.mapToGlobal(pt))
	def updateMenu(self):
		mode=self.model().mode
		if mode=='ramp':
			self.rti.setChecked(True)
			self.tti.setChecked(False)
			self.dti.setChecked(False)
		elif mode=='points':
			self.rti.setChecked(False)
			self.tti.setChecked(True)
			self.dti.setChecked(False)
		elif mode=='dwell':
			self.rti.setChecked(False)
			self.tti.setChecked(False)
			self.dti.setChecked(True)		
	def setCurve(self, crv, progressBar=False):
		self.model().setCurve(crv, progressBar)
	def curve(self):
		return self.model().curve()
		
	### ADD/DEL ####
	def newRow(self):
		crow=self.selection.currentIndex().row()
		if crow<=1: crow=1
		self.model().insertRows(crow+1)
			
	
	def insert_event(self,event):
		"""Insert new `event` at current row"""
		crow=self.selection.currentIndex().row()
		# Find latest valid time from crow
		t=0
		idx,ent=next_point(self.model().dat,crow,-1)
		if ent is not False:
			t=ent[0]
		self.model().insertRows(crow+1,ini=[t,event,0,0])	
		
	def newMove(self):
		items=['>move,close','>move,open']
		labels=[_('Close furnace'),_('Open furnace')]
		item,ok=QtGui.QInputDialog.getItem(self,_('Select furnace movement event'),_('Event type:'),labels,0,False)
		if not ok:
			return
		val=labels.index(item)
		val=items[val]
		self.insert_event(val)
		
	def newCheckpoint(self):
		delta,ok=QtGui.QInputDialog.getDouble(self,_('Define a setpoint tolerance'),
											_('Temperature-Setpoint tolerance:'),
											3,0.1)
		if not ok:
			return
		event='>checkpoint,{:.1f}'.format(delta)
		self.insert_event(event)
	
	def newParam(self):
		#TODO: param window
		assert False,'TODO'
		
	def delRow(self):
		crow=self.selection.currentIndex().row()
		if crow<=1: crow=1
		self.model().removeRows(crow)
		
		
class ThermalCycleDesigner(QtGui.QSplitter):
	"""The configuration interface widget. It builds interactive controls to deal with a misura configuration object (options, settings, peripherals configurations, etc)."""
	def __init__(self, remote, parent=None):
#		QtGui.QWidget.__init__(self, parent)
		QtGui.QSplitter.__init__(self, parent)
		self.setOrientation(QtCore.Qt.Vertical)
		self.remote=remote
		self.main_layout=self
#		self.main_layout=QtGui.QVBoxLayout()
#		self.setLayout(self.main_layout)
		menuBar=QtGui.QMenuBar(self)
		menuBar.setNativeMenuBar(False)
		self.main_layout.addWidget(menuBar)
		
		self.table=ThermalCurveTable()
		self.model=self.table.model()
		self.table.updateMenu()
		
		self.fileMenu=menuBar.addMenu('File')
		self.fileMenu.addAction('Import from CSV', self.loadCSV)
		self.fileMenu.addAction('Export to CSV', self.exportCSV)
		self.fileMenu.addAction('Clear table', self.clearTable)
		self.editMenu=menuBar.addMenu('Edit')
		self.editMenu.addAction('Insert point', self.table.newRow)
		self.editMenu.addAction('Insert checkpoint', self.table.newCheckpoint)
		self.editMenu.addAction('Insert movement', self.table.newMove)
		a=self.editMenu.addAction('Insert parametric heating', self.table.newParam)
		a.setEnabled(False)
		self.editMenu.addAction('Remove current row', self.table.delRow)
		self.modeMenu=menuBar.addMenu('Mode')
		self.modeMenu.addAction(self.table.rti)
		self.modeMenu.addAction(self.table.tti)
		self.modeMenu.addAction(self.table.dti)
		self.addButtons()
		

		
		self.plot=ThermalCyclePlot()
		self.connect(self.model, QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.replot)
		self.addTable()
		
		self.main_layout.addWidget(self.table)
		self.main_layout.addWidget(self.plot)
		
	def replot(self, *args):
		crv=self.model.curve(events=False)
		print 'replotting',crv
		self.plot.setCurve(crv)
		
	def addButtons(self):
		# General buttons:
		self.buttonBar=QtGui.QWidget()
		self.buttons=QtGui.QHBoxLayout()
		self.buttonBar.setLayout(self.buttons)

		self.bRead=QtGui.QPushButton("Read")
		self.connect(self.bRead,  QtCore.SIGNAL('clicked(bool)'), self.refresh)
		self.buttons.addWidget(self.bRead)
		
		self.bApp=QtGui.QPushButton("Apply")
		self.connect(self.bApp,  QtCore.SIGNAL('clicked(bool)'), self.apply)
		self.buttons.addWidget(self.bApp)
		self.tcc=widgets.ThermalCycleChooser(self.remote, parent=self)
		self.tcc.label_widget.hide()
		self.buttons.addWidget(self.tcc)
		self.connect(self.tcc.combo,  QtCore.SIGNAL('currentIndexChanged(int)'), self.refresh)
		self.connect(self.tcc,  QtCore.SIGNAL('changed()'), self.refresh)
		# Disconnect save button from default call
		self.tcc.disconnect(self.tcc.bSave, QtCore.SIGNAL('clicked(bool)'), self.tcc.save_current)
		# Connect to apply_and_save
		self.connect(self.tcc.bSave, QtCore.SIGNAL('clicked(bool)'), self.apply_and_save)
		# Remove edit button
		self.tcc.lay.removeWidget(self.tcc.bEdit)
		self.tcc.bEdit.hide()
		self.main_layout.addWidget(self.buttonBar)
		
	def addTable(self, crv=None):
		if crv==None:
			crv=self.remote.get('curve')
			print 'got remote curve', crv
		if len(crv)==0: 
			crv=[[0,0]] 
# 			self.plot.hide()
		if not self.plot.isVisible():
			self.plot.show()
		pb=QtGui.QProgressBar(self)
		pb.setMinimum(0); pb.setMaximum(len(crv))
		self.main_layout.addWidget(pb)
		self.table.setCurve(crv, progressBar=pb)
		self.replot()
		pb.hide()
		pb.close()
		del pb
		
	def clearTable(self):
		self.addTable([])
		
		
	def refresh(self, *args):
		print 'ThermalCycleDesigner.refresh'
		self.addTable()
		
	def apply(self):
		crv=self.table.curve()
		self.remote.set('curve', crv)
		self.refresh()
		
	def apply_and_save(self):
		self.apply()
		self.tcc.save_current()
		
	def loadCSV(self):
		fname=QtGui.QFileDialog.getOpenFileName(self, 'Choose a *.csv file containing a time-temperature curve', '', "CSV Files (*.csv)")
		print fname
		f=open(fname, 'r')
		crv=[]
		for row in f:
			if row[0]=='#': continue
			row=row.replace(',','.')
			row=row.split(';')
			t=float(row[0])
			T=row[1]
			if not T.startswith('>'):
				T=float(T)
			crv.append([t, T])
		self.addTable(crv)
		
	def exportCSV(self):
		fname=QtGui.QFileDialog.getSaveFileName(self, 'Choose destination file name', '', "CSV Files (*.csv)")
		f=open(fname, 'w')
		f.write('#time ; temp ; checkpoint\n')
		for row in self.model.curve(events=True):
			tpl="{:.3f} ; {:.3f} \n"
			if isinstance(row[1],basestring):
				tpl="{:.3f} ; {} \n"
			f.write(tpl.format(*row))
		
