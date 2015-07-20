#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Auto configuration script for standard Misura4 full-optional"""



import numpy as np
from cPickle import loads
from misura.client import from_argv
from time import sleep


m=from_argv()

left_cam_serial='s61443500'
right_cam_serial= 's61443503'
flex_cam_serial='s61450503'
micro_cam_serial='s191447500'

# Motor names
b0=m.morla.idx0
m_focus=b0.X
m_micro=b0.Y
left_x=b0.board1.X
left_y=b0.board1.Y
left_ang=b0.board2.X
m_flash=b0.board2.Y
right_x=b0.board3.X
right_y=b0.board3.Y
right_ang=b0.board4.X


# Camera names
assert len(m.beholder.list())==4, 'Wrong camera identification'
left_cam=getattr(m.beholder, left_cam_serial)
left_cam['name']='Left'
left_cam['autocrop']='Never'
left_cam['clock']=26
left_cam.save('default')
right_cam=getattr(m.beholder, right_cam_serial)
right_cam['name']='Right'
right_cam['autocrop']='Never'
right_cam['clock']=26
right_cam.save('default')
flex_cam=getattr(m.beholder, flex_cam_serial)
flex_cam['name']='Flex'
flex_cam['autocrop']='Never'
flex_cam['clock']=26
flex_cam.save('default')
micro_cam=getattr(m.beholder, micro_cam_serial)
micro_cam['name']='Microscope'
micro_cam['clock']=92
micro_cam.save('default')

######
## Motors configuration
######

def send_to_zero(motor):
	print 'sending to zero:', motor['fullpath']
	motor['micro']='lower step'
	print motor['limits']
	motor.wait()
#	assert motor['goingTo']==0
#	assert motor['position']==0

def board_send_to_zero(board):
	motors=board['motors']
	for dev in board.devices:
		if dev['devpath'] in motors:
			send_to_zero(dev)
			continue
		board_send_to_zero(dev)

def find_limits(motor, name):
#	if motor['sloPe']==8000:
#		motor['sloPe']==3000
	motor['sloPe']==100000
	if motor['Rate']==800:
		motor['Rate']=2000
	motor['name']=name
	print 'finding limits:', motor['fullpath']
	motor['micro']='both ends'
	print motor['limits']
	motor.wait()
	print 'found steps:', motor['steps']
	send_to_zero(motor)
	motor.save('default')
	
def board_find_limits(board, xname=False, yname=False):
	motors=[]
	names=[]
	if xname:
		motors.append('X')
		names.append(xname)
	if yname:
		motors.append('Y')
		names.append(yname)
	board.name='/'.join(names)
	board.motors=', '.join(motors)
	board.save('default')
	if xname:
		find_limits(board.X, xname)
	if yname:
		find_limits(board.Y, yname)
	
def starting_position(motor, steps, config_name):
	motor['goingTo']=steps
	motor.wait()
#	assert motor['position']==steps
	motor.save(config_name)
	motor['goingTo']=0
	motor.wait()

def configure_motors():
	assert len(m.morla.list())==1, 'Motion board detection failed'
	assert len(m.morla.idx0.list())==6,  'Wrong daisy chain detection'

	b0.maxDaisy=5
	# High speed motors
	m_micro['Rate']=3000
	m_micro['sloPe']=8000
	m_flash['Rate']=3000
	m_flash['sloPe']=100000
	 
	# Angulars  in full power
	left_ang['mOde'] = 2
	left_x['mOde']  = 2
	right_ang['mOde']  = 2
	right_x['mOde']  = 2
	# Safety zero positioning
	board_send_to_zero(b0)
	board_find_limits(b0, 'Focus', 'Microscope')
	
	board_find_limits(b0.board1, 'Left X', 'Left Y')
	
	board_find_limits(b0.board2, 'Left Angle', 'Kiln')

	board_find_limits(b0.board3, 'Right X', 'Right Y')
	
	board_find_limits(b0.board4, 'Right Angle')


	# Starting positions....
	print 'Microscope motors'
	starting_position(m_micro, m_micro['steps']*3/4., 'hsm')

	print 'Horizontal motors'
	starting_position(left_x, left_x['steps']/2, 'horizontal')
	starting_position(right_x, right_x['steps']/2, 'horizontal')
	starting_position(left_y, left_y['steps']/10, 'horizontal')
	starting_position(right_y, right_y['steps']/4, 'horizontal')

	print 'Vertical motors'
	starting_position(left_x, left_x['steps'], 'vertical')
	starting_position(left_ang, left_ang['steps'], 'vertical')
	starting_position(right_x, right_x['steps'], 'vertical')
	starting_position(right_ang, right_ang['steps'], 'vertical')
	starting_position(left_y, left_y['steps']*9/10, 'vertical')
	starting_position(right_y, right_y['steps']/6, 'vertical')

	print 'Flex motors'
	starting_position(m_micro, m_micro['steps']/2, 'flex')
	

######
## CAMERAS
######
def configure_cameras():
	print 'Configure cameras'
	m.beholder['servedClasses']=['']
	m.beholder.save('default')
	# Instruments association
	m.hsm['camera']=micro_cam
	m.hsm.save('default')

	m.horizontal['cameraLeft']=left_cam
	m.horizontal['cameraRight']=right_cam
	m.horizontal.save('default')

	m.vertical['cameraBase']=left_cam
	m.vertical['cameraHeight']=right_cam
	m.vertical.save('default')

	m.flex['camera']=flex_cam
	m.flex['cameraLeft']=left_cam
	m.flex['cameraRight']=right_cam
	m.flex.save('default')

	# Samples association
	# Microscope camera
	m.hsm['nSamples']=1
	micro_cam['name']='Left'
	micro_cam['smp0']=[m.hsm.sample0['fullpath'], 'default']
	micro_cam.save('default')

	# Horizontal left/right
	m.horizontal['nSamples']=1
	left_cam['smp0']=m.horizontal.sample0.Left
	left_cam.save('horizontal')
	right_cam['smp0']=m.horizontal.sample0.Right
	right_cam.save('horizontal')

	# Vertical 
	m.vertical['nSamples']=1
	left_cam['smp0']=m.vertical.sample0.Base
	left_cam.save('vertical')
	right_cam['smp0']=m.vertical.sample0.Height
	right_cam.save('vertical')

def configure_encoders():
	print 'Configure encoders'
	for cam in m.beholder.devices:
		cam.encoder.focus.motor=m_focus
		cam.encoder.focus.save('default')
	
	micro_cam.encoder.y.motor=m_micro
	micro_cam.encoder.y.save('default')
	
	flex_cam.encoder.y.motor=m_micro
	flex_cam.encoder.y.save('default')
	
	left_cam.encoder.x.motor=left_x
	left_cam.encoder.x.align=-2
	left_cam.encoder.x.save('default')
	
	left_cam.encoder.y.motor=left_y
	left_cam.encoder.y.save('default')
	
	left_cam.encoder.angle.motor=left_ang
	left_cam.encoder.angle.save('default')

	right_cam.encoder.x.motor=right_x
	right_cam.encoder.x.align=2
	right_cam.encoder.x.save('default')

	right_cam.encoder.y.motor=right_y
	right_cam.encoder.y.save('default')
	
	right_cam.encoder.angle.motor=right_ang
	right_cam.encoder.angle.save('default')

tc_hitemp=None
tc_termostat=None
power_out=None

def configure_kiln():
	global power_out
	print 'Configure kiln'
	assert len(m.smaug.list())==3, 'Wrong number of thermal control devices'
#	m.smaug['servedClasses']=['Eurotherm_ePack', 'DatExel']
	m.smaug['epack']='10.0.8.88:502'
	m.smaug['rescan']
	m.smaug.save('default')
	m.kiln.motor=m_flash
	m.kiln['motorStatus']=2
	def process_datexel(dev):
		global tc_hitemp, tc_termostat
		if dev['model']=='3016':
			dev['name']='High Temperature'
			dev['inputch0']=13
			dev['inputch1']=13
			dev['inputch2']=14
			dev['inputch3']=14
			dev.save('default')
			tc_hitemp=dev
		elif dev['model']=='3014':
			dev['name']='Termostat'
			dev['input']=23
			dev.save('default')
			tc_termostat=dev
			
			
	for dev in m.smaug.devices:
		if dev['mro'][0]=='DatExel':
			process_datexel(dev)
		if dev['mro'][0]=='Eurotherm_ePack':
			power_out=dev
			
	assert tc_hitemp!=None, 'High temperature thermocouple reader not found'
	assert tc_termostat!=None, 'Low temperature thermocouple reader not found'
	assert power_out!=None, 'Power controller not found'
	
	ht=tc_hitemp['fullpath']
	ts=tc_termostat['fullpath']
	pw=power_out['fullpath']
	m.kiln.setattr('Ts', 'options',[ht, 'default', 'ch0'])
	m.kiln.setattr('Ts2', 'options',[ht, 'default', 'ch1'])
	m.kiln.setattr('Tk', 'options',[ht, 'default', 'ch2'])
	m.kiln.setattr('Th', 'options',[ht, 'default', 'ch3'])
	
	m.kiln.setattr('Te', 'options',[ts, 'default', 'ch1'])
	
	m.kiln.setattr('P', 'options', [pw, 'default', 'power'])
	m.kiln.setattr('powerSwitch', 'options', [pw, 'default', 'enabled'])
	
	m.kiln.save('default')


configure_motors()
configure_cameras()
configure_encoders()
configure_kiln()

