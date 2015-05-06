#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Elementi grafici avanzati per la modifica delle proprietà di configurazione sul server misura"""
from PyQt4 import QtGui,QtCore
from active import Active, ActiveObject, ActiveWidget,Autoupdater, info_dialog, RunMethod
import os

from .. import _
from traceback import print_exc
from aBoolean import aBoolean,  aBooleanAction
from aButton import aButton
from aChooser import aChooser
from aDict import aDict
from aMeta import aMeta
from aMaterial import aMaterial
from aNumber import aNumber,  aNumberAction
from aProgress import aProgress, RoleProgress
from aString import aString
from aScript import aScript
from aTable import aTable
from aProfile import aProfile
from aTime import aTime, aDelay
from presets import PresetManager
from role import Role,  RoleEditor,  RoleDialog
from cycle import ThermalCycleChooser
from motorslider import MotorSlider, MotorSliderAction

def build(server, remObj, prop, parent=None):
	"""Build a property widget based on a property dict"""
	arg=(server, remObj, prop, parent)
	A=prop['attr']
	T=prop['type']
	if 'Hidden' in A+[T]:
#		print 'Hidden property',prop
		return False
	obj=False
	try:
		if T in ['String', 'ReadOnly', 'Date','FilePath']:
			if prop['handle']=='material':
				obj=aMaterial(*arg)
			else:
				obj=aString(*arg)
		elif T=='TextArea':
			obj=aString(server, remObj, prop, parent, extended=True)
		elif T=='Script':
			print 'starting script',prop
			obj=aScript(server, remObj, prop, parent)
		elif T=='Boolean':
			obj=aBoolean(*arg)
		elif T in ['Chooser', 'Menu']:
			obj=aChooser(*arg)
		elif T=='Preset':
			obj=PresetManager(remObj)
		elif T in ['Integer', 'Float', 'Number']:
			obj=aNumber(*arg)
		elif T=='Time':
			if prop['kid']=='/delay':
				obj=aDelay(*arg)
			else:
				obj=aTime(*arg)
		elif T=='Progress':
			obj=aProgress(*arg)
		elif T in ['Point2D', 'Vector', 'Dict']:
			obj=aDict(*arg)
		elif T=='Meta':
			obj=aMeta(*arg)
		elif T=='Button':
			obj=aButton(*arg)
		elif T=='ThermalCycle':
			obj=ThermalCycleChooser(server.kiln, parent=parent)
		elif T.startswith('Role'):
			obj=Role(*arg)
		elif T=='Table':
			obj=aTable(*arg)
		elif T=='Profile':
			obj=aProfile(*arg)
		elif prop['kid']=='/progress':
				obj=RoleProgress(*arg)
	except:
		print 'Building ', prop, 'of', remObj, 'error:'
		print_exc()
		if obj:
			obj.hide()
			obj.close()
			del obj
		return False
	return obj



if __name__=='__main__':
	import sys
	from misura.client import iutils, network

	iutils.initApp()
	network.getConnection('localhost:3880')
	srv=network.manager.remote
	qb=QtGui.QWidget()
	lay=QtGui.QFormLayout()
	wgs=[]
#	wgs.append(build(srv, srv.hsm, srv.hsm.gete('comment')))
#	wgs.append(aString(srv, srv.hsm, srv.hsm.describe()['comment'], extended=True))
#	wgs.append(aBoolean(srv, srv, srv.describe()['eq_hsm']))
#	wgs.append(aChooser(srv, srv.beholder.idx0, srv.beholder.idx0.gete('Pre-Processing:Flip')))
#	wgs.append(aNumber(srv, srv.beholder.idx0, srv.beholder.idx0.gete('brightness')))
#	wgs.append(aDict(srv, srv.hsm,srv.hsm.gete('Test_Softening')))
#	wgs.append(Role(srv, srv.hsm,srv.hsm.gete('camera')))
#	wgs.append(PresetManager(srv))
#	wgs.append(ThermalCycleChooser(srv.kiln))
#	wgs.append(ServerSelector())
#	wgs.append(ConnectionStatus())
#	wgs.append(aTable(srv, srv.simulator.flexion,srv.simulator.flexion.gete('MultiLayer_material')))
	wgs.append(aProfile(srv, srv.hsm.sample0, srv.hsm.sample0.gete('profile')))
	for wg in wgs:
		print wg
		lay.addRow(wg.label, wg)
	qb.setLayout(lay)
	qb.show()
	sys.exit(QtGui.qApp.exec_())









