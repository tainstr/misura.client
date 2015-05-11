#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Graphical overlay for image analysis"""
from PyQt4 import QtGui, QtCore
from math import sqrt
from hook import HookPoint
from .. import _, widgets

colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 125, 125), (125, 125, 0), (125, 0, 125)]*3


def intraSet(x1, y1, x2, y2, h, w):
	"""Redefine (x1,y1),(x2,y2) points so that both are inside h,w boundaries"""
	if abs(x2 - x1) < 10 ** -12:	return x1, y1, x2, y2
	a = (y2 - y1) / (x2 - x1)	# coeff. angolare
	if abs(a) < 10 ** -12: 		return x1, y1, x2, y2
	b = y1 - a * x1			# costante b, y=ax+b
	if y1 > h:
		y1 = h;	x1 = (h - b) / a
	elif y1 < 0:
		y1 = 0;	x1 = -b / a
	if y2 > h:
		y2 = h;	x2 = (h - b) / a
	elif y2 < 0:
		y2 = 0;	x2 = -b / a
	if x1 > w:
		x1 = w;	y1 = a * w + b
	if x2 > w:
		x2 = w;	y2 = a * w + b
	return x1, y1, x2, y2
	
class CalibrationTool(QtGui.QDialog):
	"""Pixel distance measurement tool"""
	def __init__(self, pixItem, remote, parent=None):
		QtGui.QDialog.__init__(self, parent)
		self.pixItem = pixItem
		self.remote = remote
		self.old_umpx = float(remote['Analysis_umpx'])
		self.factor = self.old_umpx
		self.vfactor = self.old_umpx
		self.setWindowTitle(_('Pixel Calibration'))
		self.lay = QtGui.QFormLayout()
		self.setLayout(self.lay)
		
		# Connect to the sample analyzer calibrationLength property
		self.sample=self.remote.role2dev('smp0')
		self.rpl=widgets.build(self.remote.root,self.sample.analyzer,self.sample.analyzer.gete('calibrationLength'))
		self.lay.addRow(self.rpl.label_widget,self.rpl)
		
		self.pxLen = QtGui.QLabel('', self)
		self.lay.addRow(_('Visual Pixel Length')+':', self.pxLen)
		self.visFactor = QtGui.QLabel('', self)
		self.lay.addRow(_('Visual factor')+':', self.visFactor)	
		
		self.oldFactor = QtGui.QLabel('%.2f' % self.old_umpx, self)
		self.lay.addRow(_('Old factor)')+':', self.oldFactor)
		self.oldUm = QtGui.QLabel('', self)
		self.lay.addRow(_('Old length')+':', self.oldUm)
		self.newUm = QtGui.QDoubleSpinBox(self)
		self.newUm.setMinimum(0.5)
		self.newUm.setMaximum(50000)
		self.newUm.setValue(250)
		self.newUm.setSingleStep(0.5)
		self.newUm.setSuffix(u" \u00b5m")
		self.lay.addRow(_('New length')+':', self.newUm)

		
		self.newFactor = QtGui.QLabel('', self)
		self.lay.addRow(_('New factor')+':', self.newFactor)
		self.okBtn = QtGui.QPushButton(_('Set new factor'), self)
		self.lay.addRow('', self.okBtn)
		
		self.connect(self.okBtn, QtCore.SIGNAL('clicked()'), self.ok)
		self.connect(self.newUm, QtCore.SIGNAL('valueChanged(double)'), self.sync)
		self.connect(self, QtCore.SIGNAL('destroyed(QObject)'), self.cleanUp)
		
	def showEvent(self, e):
		self.old_umpx = float(self.remote['Analysis_umpx'])
		self.sample.analyzer['calibration']=True
		self.factor = self.old_umpx
		self.vfactor = self.old_umpx
		r = self.pixItem.boundingRect()
		w, h = r.width(), r.height()
		self.w, self.h = w, h
		
		self.pt1 = HookPoint(w / 2 - 5, 3 * h / 4 - 5, 10, 10, parent=self.pixItem)
		self.pt1.hook = self.sync
		self.pt2 = HookPoint(w / 2 - 5, 1 * h / 4 - 5, 10, 10, parent=self.pixItem)
		self.pt2.hook = self.sync
		
		self.line = QtGui.QGraphicsLineItem(self.x1, self.y1, self.x2, self.y2, self.pixItem)
		self.line.setPen(self.pt1.pen()); self.line.setZValue(100)
		
		pen = QtGui.QPen(QtGui.QColor(*colors[2]))
		self.stop1 = QtGui.QGraphicsLineItem(0, self.y1, w, self.y1, self.pixItem)
		self.stop1.setPen(pen); self.stop1.setZValue(100)
		self.stop2 = QtGui.QGraphicsLineItem(0, self.y2, w, self.y2, self.pixItem)
		self.stop2.setPen(pen); self.stop2.setZValue(100)
		
		self.sync()
		self.newUm.setValue(self.length * self.old_umpx)
		QtGui.QDialog.showEvent(self, e)
		
	@property
	def x1(self):	return self.pt1.x() + self.w / 2
	@property
	def x2(self):	return self.pt2.x() + self.w / 2
	@property
	def y1(self):	return self.pt1.y() + 3 * self.h / 4
	@property
	def y2(self):	return self.pt2.y() + 1 * self.h / 4
	@property
	def length(self):
		return sqrt((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2)
		
	def ok(self):
		self.remote['Analysis_umpx'] = self.factor
		self.cleanUp()
		self.done(0)
		
	def vis_sync(self):
		# Calculating visual length/factor
		x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2
		self.line.setLine(x1, y1, x2, y2)
		# Coefficiente angolare retta perpendicolare a self.line:
		set1 = [0, 0, 0, 0]
		set2 = [0, 0, 0, 0]
		if abs(x2 - x1) < 10 ** -12:				# Retta parallela all'asse y
			set1 = [0, y1, self.w, y1]
			set2 = [0, y2, self.w, y2]
		elif abs((y2 - y1) / (x2 - x1)) < 10 ** -12:	# Retta parallela all'asse x
			set1 = [x1, 0, x1, self.h]
			set2 = [x2, 0, x2, self.h]
		else:								# Qualsiasi altra inclinazione
			# Coefficiente angolare self.line
			al = (y2 - y1) / (x2 - x1)
			# Coefficiente angolare retta perpendicolare
#			a=tan(atan(al)+pi/2)
			a = -1 / al
			# Costante per retta passante per pt1
			b1 = y1 - a * x1
			# Costante per retta passante per pt2
			b2 = y2 - a * x2
			# Aggiornamento linee
			if a < 0:
				set1 = [0, b1, -b1 / a, 0]
				set2 = [0, b2, -b2 / a, 0]
			else:
				set1 = [0, b1, (self.h - b1) / a, self.h]
				set2 = [0, b2, (self.h - b2) / a, self.h]
		set1 += [self.h, self.w];	set2 += [self.h, self.w]
		self.stop1.setLine(*intraSet(*set1))
		self.stop2.setLine(*intraSet(*set2))
		ln = self.length
		self.pxLen.setText(u'%.2f px' % ln)
		self.oldFactor.setText(u'%.2f \u00b5m/px' % self.old_umpx)
		self.oldUm.setText(u'%.2f \u00b5m' % (ln * self.old_umpx))
		self.vfactor = self.newUm.value() / ln
		self.visFactor.setText(u'%.2f \u00b5m/px' % self.vfactor)
		
	def sync(self, *foo):
		self.rpl.update()
		self.vis_sync()
		self.factor=self.newUm.value()/self.rpl.current
		self.newFactor.setText(u'%.2f \u00b5m/px' % self.factor)
		
		
	def closeEvent(self, e):
		self.cleanUp()
		return QtGui.QDialog.closeEvent(self, e)
		
	def cleanUp(self, *foo):
		self.sample.analyzer['calibration']=False
		s = self.pixItem.scene()
		lst = self.pt1, self.pt2, self.line, self.stop1, self.stop2
		for item in lst:
			s.removeItem(item)
			del item
		