#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
"""Converts from Misura 3 to Misura 4 database formats"""
import tables, numpy
import numpy as np
from copy import deepcopy
import os
import logging
import StringIO
from traceback import print_exc
from datetime import datetime
from time import time
import string
import hashlib

from PIL import Image
from tables.nodes import filenode

from misura.canon import bitmap, csutil, option, reference
from misura.canon.option import ao

import m3db

valid_chars = "-_.: %s%s" % (string.ascii_letters, string.digits)

# Heating curve point
HeatingCyclePoint={
	't': tables.Float32Col(pos=1),
	'T': tables.Float32Col(pos=2),
	'chk': tables.BoolCol(pos=3)
}
	
base_dict={}
ao(base_dict,'name','String')
ao(base_dict,'comment','String')
ao(base_dict,'dev','String')
ao(base_dict,'devpath','String')
ao(base_dict,'fullpath','String')

measure_dict=deepcopy(base_dict)
measure_dict['name']['current']='Measure'
ao(measure_dict,'nSamples','Integer',1)
ao(measure_dict,'id','String')
ao(measure_dict,'date','Date','00:00:00 01/01/2000')
ao(measure_dict,'elapsed','Float',unit='second')
ao(measure_dict,'maxT','Meta')
ao(measure_dict,'end','Meta')
ao(measure_dict,'maxHeatingRate','Meta')
ao(measure_dict,'coolingDuration','Meta')
ao(measure_dict,'maxCoolingRate','Meta')


std_dict=deepcopy(base_dict)
std_dict['name']['current']='Standard'
ao(std_dict,'end','Script',"mi.Point(-1)")
ao(std_dict,'maxT','Script',"""i,t,T=mi.Max('T')
mi.t(t)
mi.T(T)
""")
ao(std_dict,'maxHeatingRate','Script',"""
T1=mi.TimeDerivative('T')	
if len(T1)<10: mi.Exit()
rate=max(T1)
w=mi.Where(T1==rate)
if w<0: mi.Exit()
mi.Value(rate/60)
mi.Point(w,'T')
""",'Maximum Heating Rate')

ao(std_dict,'coolingDuration','Script',"""
if not mi.SelectCooling():
	mi.Exit()
t,T=mi.xy('T')
dT=T[0]-T[-1]
dt=t[-1]-t[0]
mi.T(dT)
mi.t(dt)
""",'Total cooling duration')

ao(std_dict,'maxCoolingRate','Script',"""
if not mi.SelectCooling():
	mi.Exit()
T1=mi.TimeDerivative('T')
if len(T1)<10: mi.Exit()
rate=min(T1)
w=mi.Where(T1==rate)
if w<0: mi.Exit()
mi.Value(-rate/60)
mi.Point(w,'T')
""",'Maximum Cooling Rate')

std_hsm=deepcopy(std_dict)
ao(std_hsm,'Sintering','Script',"""
factor=script.Opt('param_sint')/100.
threshold=obj.At('Sint',0)*factor
ti=obj.Drops('Sint', threshold)
if ti<0: mi.Exit()
mi.t(ti)
mi.T(obj.At('T',ti))
mi.Value(obj.At('Sint',ti))""")
ao(std_hsm,'param_sint','Integer',95,'Height shrinking for Sintering', parent='Sintering')

#ao(std_hsm,'Softening','Script',"""
#min_decrease=script.Opt('param_soft')
#ratio=mi.Ratio('Sint','Width')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
#ratio=(ratio/ratio[0])
#i=mi.Drops(ratio,min_decrease/100.)
#if i<0: mi.Exit()
#v=ratio[i]
#mi.Point(i)
#mi.Value(v)""")
#ao(std_hsm,'param_soft','Integer',5,'Minimum % decrease in h/w ratio for Softening',parent='Softening')

ao(std_hsm,'Softening','Script',"""
threshold=script.Opt('param_soft')
method=script.Opt('param_softMethod')
backward=script.Opt('param_softBackward')
if method=='Relative':
	threshold+=mi.At('Softening',0)
if backward:
	#... ricerca del massimo e poi all'indietro!
	ti=obj.Drops('Softening',threshold)
else:
	ti=obj.Raises('Softening',threshold)
if ti<0: mi.Exit()
mi.t(ti)
mi.T(obj.At('T',ti))
mi.Value(obj.At('Softening',ti))""")

ao(std_hsm,'param_soft','Float',2.5,'Softening parameter threshold',parent='Softening')
ao(std_hsm,'param_softMethod','Chooser','Absolute','Method for softening thresholding',options=['Absolute','Relative'],parent='Softening')
ao(std_hsm,'param_softBackward','Boolean',False,'Search threshold starting from the maximum softening value',parent='Softening')

ao(std_hsm,'Sphere','Script',"""
threshold=script.Opt('param_sphere')
ratio=obj.Ratio('Sint','Width')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
ti=mi.Where(ratio<threshold)
if i<0: mi.Exit()
mi.Point(i)
mi.Value(ratio[i])""")
ao(std_hsm,'param_sphere','Float',1.,'Ratio h/w for Sphere',parent='Sphere')

ao(std_hsm,'HalfSphere','Script',"""
threshold=script.Opt('param_hsphere')
tol=script.Opt('param_hsphereTol')
ratio=obj.Ratio('Sint','Width')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
i=mi.Where(ratio<threshold)
if i<0: mi.Exit()
v=ratio[i]
if abs(threshold-v)>tol:
	mi.Exit()
mi.Point(i)
mi.Value(v)""")
ao(std_hsm,'param_hsphere','Float',0.5,'Ratio h/w for HalfSphere',parent='HalfSphere')
ao(std_hsm,'param_hsphereTol','Float',0.2,'Tolerance for HalfSphere',parent='HalfSphere')

ao(std_hsm,'Melting','Script',"""
threshold=script.Opt('param_melt')
ratio=obj.Ratio('Sint','Width')*obj.Opt('initialDimension')/obj.Opt('initialWidth')
i=mi.Where(ratio<threshold)
if i<0:
	mi.Exit()
mi.Point(i)
mi.Value(ratio[i])""")
ao(std_hsm,'param_melt','Float',0.333,'Ratio h/w for Melting',parent='Melting')

smp_dict=deepcopy(base_dict)
smp_dict['name']['current']='Sample'
ao(smp_dict,'idx','Integer')
ao(smp_dict,'ii','Integer')
ao(smp_dict,'initialDimension','Float',3000.)
ao(smp_dict,'initialWidth','Float',2000.)
ao(smp_dict,'roi','Rect',[0,0,640,480])
ao(smp_dict,'initialDimension','Float')
ao(smp_dict,'profile','Profile',[(),[],[]])
ao(smp_dict,'Sintering','Meta')
ao(smp_dict,'Softening','Meta')
ao(smp_dict,'Sphere','Meta')
ao(smp_dict,'HalfSphere','Meta')
ao(smp_dict,'Melting','Meta')

kiln_dict=deepcopy(base_dict)
kiln_dict['name']['current']='Kiln'
ao(kiln_dict,'Regulation_Kp','Float',0,'Proportional Factor')
ao(kiln_dict,'Regulation_Ki','Float',0,'Integral Factor')
ao(kiln_dict,'Regulation_Kd','Float',0,'Derivative Factor')
ao(kiln_dict,'curve','Hidden',[[0,0,0]],'Heating curve')
ao(kiln_dict,'thermalCycle','ThermalCycle','default')
ao(kiln_dict,'T','Float',0,'Temperature',unit='celsius')
ao(kiln_dict,'P','Float',0,'Power',unit='percent')
ao(kiln_dict,'S','Float',0,'Setpoint',unit='celsius')

instr_dict=deepcopy(base_dict)
ao(instr_dict,'camera','Role',['camerapath','default'])
ao(instr_dict,'devices','Point')

camera_dict=deepcopy(instr_dict)
camera_dict['name']['current']='camera'
camera_dict['devpath']['current']='camerapath'
camera_dict['dev']['current']='camera'
ao(camera_dict,'last_frame','Image',[])
ao(camera_dict,'size','List',[640,480])
ao(camera_dict,'Analysis_sampleIdx','Integer',0)
ao(camera_dict,'Analysis_umpx','Integer',1)
ao(camera_dict,'nSamples','Integer',1)
ao(camera_dict,'Analysis_instrument','String','hsm')
ao(camera_dict,'Analysis_Simulation','Boolean',True)
ao(camera_dict,'Analysis_AutoROI','Boolean',False)
# TODO: define analyzer!
ao(camera_dict,'PreProcessing:BlackWhite','Boolean',True)
ao(camera_dict,'PreProcessing:AdaptiveThreshold','Boolean',False)

server_dict=deepcopy(base_dict)
server_dict['name']['current']='server'
ao(server_dict,'name','String','server')
ao(server_dict,'isRunning','Boolean',False)
ao(server_dict,'runningInstrument','String')
ao(server_dict,'log','String')

empty={'self':deepcopy(camera_dict)}
tree_dict={'self':server_dict,
	'analyzer':{'self':deepcopy(base_dict),'hsm':empty,'odlt':empty,'odht':empty,'flex':empty},
	'hsm':{'self':instr_dict,
			'measure':{'self':measure_dict},
			'sample0':{'self':smp_dict}
			},
	'kiln':{'self':kiln_dict},
	'beholder':{'self':deepcopy(base_dict),
			'idx0':{'self':camera_dict}
			}
			
	}


def create_tree(outFile,tree,path='/'):
	"""Recursive tree structure creation"""
	for key,foo in tree.list():
		logging.debug('%s %s %s', 'Creating group:', path, key)
		outFile.createGroup(path,key,key)
		create_tree(outFile,tree.child(key),path=path+key+'/')

def clear_data(outFile):
	#TODO: fix this!
	return False
	lst=outFile.listNodes('/')
	for n in lst:
		if getattr(outFile.root, n, False):
			outFile.removeNode('/'+n, recursive=True)

def fsignal(*foo,**kwfoo):
	logging.debug('%s %s', 'emit', foo)

def convert(dbpath, tcode=False, outdir=False,img=True,force=True, keep_img=True,format='m3',signal=fsignal):
	"""Extract a Misura 3 test and export into a Misura 4 test file"""
	
	# Open DB and import test data
	signal(0)
	if not tcode: 
		dbpath,tcode=dbpath.split('|')
	conn,cursor=m3db.getConnectionCursor(dbpath)
	cursor.execute("select * from PROVE where IDProve = '%s'" % tcode)
	tests=cursor.fetchall()
	if len(tests)!=1:
		logging.debug('%s %s', 'Wrong number of tests found', tests)
		return False
	signal(5)
	test=tests[0]
	icode=m3db.getImageCode(tcode)
	cursor.execute("select * from IMMAGINI where [IDProve] = '%s' order by Tempo" % icode)
	rows=cursor.fetchall()
	logging.debug('%s %s', 'CONVERT GOT', len(rows))
	if len(rows)<1:
		logging.debug('%s %s', 'No points', rows)
		return False
	signal(10)
	
	###
	# Open Output File
	if not outdir:
		outdir=os.path.dirname(dbpath)
		outdir=os.path.join(outdir,'m4')
		if not os.path.exists(outdir):
			os.mkdir(outdir)
	safeName=''.join(c for c in test[m3db.fprv.Desc_Prova] if c in valid_chars)
	outpath=os.path.join(outdir,safeName+'_'+tcode+'.h5')
	
	# Manage overwriting options
	if os.path.exists(outpath):
		# Keep current images
		if keep_img:
			outFile=tables.openFile(outpath,mode='a')
			found=getattr(outFile.root,'dat',False)
			# If no images: create new file
			if not found:
				outFile.close()
				outFile=tables.openFile(outpath,mode='w')
			# Else, wipe out data points and configuration
			else:
				clear_data(outFile)
				# but keep images!
				img=False
		# If I am forcing overwriting and not caring about current images, 
		# create new file
		elif force:
			outFile=tables.openFile(outpath,mode='w')
		# If I am not forcing neither keeping images, return the current file
		else:
			logging.debug('%s %s', 'Already exported path:', outpath)
			return outpath
	# If it does not exist, create!
	else:
		outFile=tables.openFile(outpath,mode='w')
	
	#TODO: log file handling!
	zt=time()
	log_ref=reference.Binary(outFile,'/',server_dict['log'])
	def log(msg):
		#TODO: check zerotime
		log_ref.commit([[time(),msg]],zt)
	
	log('Importing from %s, id %s\n' % (dbpath,tcode))
	log('Conversion Started at '+datetime.now().strftime("%H:%M:%S, %d/%m/%Y")+'\n')
	log('Conversion Parameters: \n\tImages: %r, \n\tUpdate: %r, \n\tKeep Images: %r, \n\tImage Format: %r\n' % (img,force,keep_img,format))
	
	
	signal(11)
	# Heating cycle table
	cycle=m3db.getHeatingCycle(test)
	for l in cycle:
		if len(l)==2: l.append(False)
		logging.debug('%s', l)
	signal(12)
	
	
	###
	# CONFIGURATION
	tree=deepcopy(tree_dict)
	# Create instrument dict
	instr=m3db.getInstrumentName(test[m3db.fprv.Tipo_Prova])
	if instr!='hsm':
		tree[instr]=deepcopy(tree['hsm'])
		tree[instr]['self']['name']['current']=instr
		tree[instr]['standard']={'self':deepcopy(std_dict)}
		del tree[instr]['sample0']['self']['initialWidth']
	else:
		tree[instr]['standard']={'self':deepcopy(std_hsm)}
	# Get a configuration proxy
	tree=option.ConfigurationProxy(tree)
	instrobj=getattr(tree,instr)
	tree['runningInstrument']=instr
	# Sample 
	smp=instrobj.sample0
	smp['name']=test[m3db.fprv.Desc_Prova]
	
	# Set ROI
	roi=[0,0,640,480]
	if tcode.endswith('L'):
		roi[2]=320.
	elif tcode.endswith('R'):
		roi[0]=320.
		roi[2]=320.
	smp['roi']=roi
	
	# Measure
	tid=dbpath+ '|' + tcode
	tdate=test[m3db.fprv.Data].strftime("%H:%M:%S, %d/%m/%Y")
	logging.debug('%s %s', test[m3db.fprv.Data].strftime("%H:%M:%S, %d/%m/%Y"))
	instrobj.measure['name']=test[m3db.fprv.Desc_Prova]
	instrobj.measure['comment']=test[m3db.fprv.Note]
	instrobj.measure['date']=tdate
	instrobj.measure['id']=tid
	
	# Kiln
	tree.kiln['curve']=cycle
	tree.kiln['Regulation_Kp']=test[m3db.fprv.Pb]
	tree.kiln['Regulation_Ki']=test[m3db.fprv.ti]
	tree.kiln['Regulation_Kd']=test[m3db.fprv.td]

	# Create the hierarchy
	create_tree(outFile,tree)
	
	###
	# GET THE ACTUAL DATA
	header,columns=m3db.getHeaderCols(test[m3db.fprv.Tipo_Prova],tcode)
	rows=np.array(rows)
	logging.debug('%s %s %s %s', header, columns, len(rows[0]), instr)
	instr_path='/' + instr
	smp_path=instr_path+'/sample0'
	
	#TODO: Check conf node (???)
#	if not hasattr(outFile.root,'conf'):
#		outFile.close()
#		os.remove(outpath)
#		return convert(dbpath, tcode, outdir, img,force, keep_img,format,signal)
	
	signal(13)
	
	arrayRef={}
	timecol=rows[:,m3db.fimg.Tempo]
	# Convert data points
	for i, col in enumerate(header):
		data=rows[:,columns[i]].astype('float')
		# Skip invalid data
		if np.isnan(data).all():
			continue
		if col=='t':
			continue
		if col in ['T','P', 'S']:
			arrayRef[col]=reference.Array(outFile,'/kiln',kiln_dict[col])
		else:			
			opt=ao({},col,'Float',col,attr=['History'])[col]
			instrobj.sample0.sete(col,opt)
			arrayRef[col]=reference.Array(outFile,smp_path,opt)
		
		if col in ['Dil', 'Flex'] or 'Percorso' in col: 
			data=data/1000.
		elif col in ['Sint']: 
			data=data/100.
		elif col=='P': 
			data=data/10.
		elif col=='Width':
			logging.debug('%s', data)
			data=data/200.
		ref=arrayRef[col].ref
		ref.append(np.array([timecol,data]).transpose())
		ref.flush()
		
	signal(20)
	### 
	# ASSIGN INITIAL DIMENSION
	dim=set(['Dil','Flex','Sint','Width','camA','camB']).intersection(set(header))
	ini0=test[m3db.fprv.Inizio_Sint]
	initialDimension=0
	for d in dim:
		if not arrayRef.has_key(d): continue
		if d=='Sint': ini1=3000.
		elif d=='Width': ini1=2000.
		elif d in ['Dil','Flex','camA','camB']: ini1=ini0*100.
		arrayRef[d].ref.attrs.initialDimension=ini1
		arrayRef[d].ref.attrs.percent=d not in ['camA','camB','Width']
		arrayRef[d].ref.flush()
		# Sets the sample main initial dimension for future storage
		if d in ['Dil','Flex','Sint']:
			initialDimension=ini1
	smp['initialDimension']=initialDimension
	outFile.flush()
	
	signal(21)
	log('Converted Points: %i\n' % (len(rows)-1)*len(header))
	######
	# Final configuration adjustment and writeout
	######
	
	instrobj.measure['elapsed']=float(timecol[-1]-timecol[0])
	# Get characteristic shapes
	if instr=='hsm':
		sh=m3db.getCharacteristicShapes(test,rows.transpose())
		tree.children[instr]['sample0']['self'].update(sh)
	
	###
	# IMAGES
	imgdir=os.path.join(os.path.dirname(dbpath), icode)
	if os.path.exists(imgdir) and img and (instr in ['hsm','drop','post']):
		omg=append_images(outFile,rows,imgdir,icode,format,signal)
		if not omg: print 'ERROR Appending images'
	
	# Write conf tree
	node=filenode.newNode(outFile,where='/', name='conf')
	node.write(tree.dumps())
	node.close()
	
	# Set attributes
	outFile.root.conf.attrs.version='3.0.0'
	outFile.root.conf.attrs.instrument=instr
	outFile.root.conf.attrs.date=tdate
	outFile.root.conf.attrs.serial=hashlib.md5(dbpath).hexdigest()
	outFile.root.conf.attrs.uid=hashlib.md5(dbpath+'|'+tcode).hexdigest()
	signal(35)

	log('Conversion ended.')
	outFile.close()
	signal(100)
	return outpath


def append_images(outFile,rows,imgdir,icode,format,signal):
	if format=='m4':
		refClass=reference.Image
	else:
		refClass=reference.Binary
	ref=refClass(outFile,'/beholder/idx0',camera_dict['last_frame'])
	ref.ref.attrs.format=format
	sjob=35
	job=(99.-sjob)/len(rows)
	oi=0
	esz=0
	decmap=[]
	for i,r in enumerate(rows[:3]):
		nj=sjob+i*job
		if i // 10 ==0:
			signal(int(nj))
		logging.debug('%s %s', nj, '%')
		
		num=r[m3db.fimg.Numero_Immagine]
		img='%sH.%03i' % (icode, int(num))
		img=os.path.join(imgdir,img)
		if not os.path.exists(img): 
			logging.debug('%s %s', 'Skipping non-existent image', img)
			continue
		
		im,size=decompress(img,format)

		decmap.append((img,'/dat/smp0','img%i'%(num-1)))
		sz=len(im)
		esz+=sz
		ref.commit([[rows[i,m3db.fimg.Tempo],im]])
		oi+=1
		outFile.flush()
	logging.debug('%s %s', 'Included images:', oi)
	logging.debug('%s %s', 'Expected size:', esz/1000000.)
	return True

def decompress(img,format):
	"""Available formats (Storage):
		'm4': misura compression algorithm (Image)
		'm3': legacy Misura3 compression algorithm (Binary)
		other: any PIL supported format (Binary) 
	"""
	fr=open(img,'rb').read()
	if format=='m3':
		return (fr,(640,480))
	try:
		fr=bitmap.decompress(fr)
		if format=='bmp':
			return fr
		fr=fr[::-1]
		im=Image.fromstring('L',(640,480),fr)
		im=im.convert('L')
		if format=='m4':
			return (np.asarray(im),im.size)
		else:
			sio=StringIO.StringIO()
			im.save(sio,format)
			im.save('debug.'+format,format)
			sio.seek(0)
			r=sio.read()
			return (r,im.size)
	except:
		logging.debug('%s', print_exc())
		logging.debug('%s %s', 'Error reading image', img)
		r=('',(0,0))
	return r	

if __name__=='__main__':
	import sys
	fn=sys.argv[1]+'|'+sys.argv[2]
	convert(fn)
