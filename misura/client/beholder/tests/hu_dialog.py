#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests camera ViewerDialog"""
from misura.canon.logger import Log as logging
import unittest
from misura import utils_testing as ut

from misura import client
from PyQt4 import QtGui
from qtreactor import  qt4reactor
qt4reactor.install()
from misura.client.beholder import dialog

from misura.beholder import sim_camera
from misura.morla import sim_motor
from misura.microscope import Hsm
from misura.flex import Flex

logging.debug('%s %s', 'Importing', __name__)

def setUpModule():
	logging.debug('%s %s', 'setUpModule', __name__)
	ut.parallel(True)

def tearDownModule():
	logging.debug('%s', 'Quitting app')
	logging.debug('%s %s', 'tearDownModule', __name__)
	ut.parallel(False)

instr_class=Hsm
template='Hsm:'
#instr_class=Flex
#template='Vertex'

instr_name=instr_class.__name__.lower()
class ViewerDialog(unittest.TestCase):
	N=1
	"""Number of samples"""
	@classmethod
	def setUpClass(cls):
		if instr_name!='hsm':
			cls.N=1
			cls.template=template
		else:
			cls.template=template+str(cls.N)
			
	def setUp(self):
		self.server=ut.dummyServer(instr_class)
		instr=getattr(self.server, instr_name)
		instr['nSamples']=self.N
		instr.sample0.analyzer.autoroi['Hmargin']=25
		instr.sample0.analyzer.autoroi['Vmargin']=25
		self.rem=sim_camera.SimCamera(parent=self.server)
		enc=self.rem.encoder
# 		enc['react']='No Follow'
		vid=self.rem.videoObj
		cam=self.rem
		cam['nSamples']=self.N
		cam['template']=self.template
#   		cam['resolution']=(2240,1680)
		cam['resolution']=(640,480)
		cam.desc.set('xPos',2500)
		cam.desc.set('yPos',2500)
		vid.init_pos(2500,2500)
		cam.desc.set('xAlign',1)
		cam.desc.set('yAlign',1)
		vid.init_align(1,1)
		self.motH=sim_motor.SimMotor(parent=self.server,node='motH')
		self.motH['steps']=5000
		self.motV=sim_motor.SimMotor(parent=self.server,node='motV')
		self.motV['steps']=5000
		self.motF=sim_motor.SimMotor(parent=self.server,node='motF')
		self.motF['steps']=5000
		self.motA=sim_motor.SimMotor(parent=self.server,node='motA')
		self.motA['steps']=5000
		
		enc.x['motor']=[self.motH['fullpath'],'default',False]
		enc.x['align']=1
		enc.x.motor.setattr('streamerPos','options',[self.rem['fullpath'],'default','xPos'])
		
		enc.y['motor']=[self.motV['fullpath'],'default',False]
		enc.y['align']=1
		enc.y.motor.setattr('streamerPos','options',[self.rem['fullpath'],'default','yPos'])
		
		enc.focus['motor']=[self.motF['fullpath'],'default',False]
		enc.angle['motor']=[self.motA['fullpath'],'default',False]
		
#		self.rem['smp0']=[instr.sample0['fullpath'],'default',False]
		
		for s in range(self.N):
			smp=getattr(instr,'sample%i' %s)
			self.rem['smp%i' % s]=[smp['fullpath'],'default',False]
		
		self.rem.parent=lambda: self.server
		self.obj=dialog.ViewerDialog(self.server,self.rem)
		
	def tearDown(self):
		self.obj.close()
	
	def test_show(self):
		self.obj.show()
		QtGui.qApp.exec_()

		

		
if __name__ == "__main__":
	unittest.main()  

