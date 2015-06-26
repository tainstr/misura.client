#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Libreria per il plotting semplice durante l'acquisizione."""
from misura.canon.logger import Log as logging
from traceback import format_exc
from exceptions import BaseException
import numpy as np
from copy import deepcopy
import re
from scipy.interpolate import InterpolatedUnivariateSpline

import veusz.dataimport.base as base
import veusz.dataimport.capture as capture


from dataset import MisuraDataset, Sample
import linked
from proxy import getFileProxy, RemoteFileProxy

from entry import iterpath

from .. import iutils, live
from .. import clientconf

from misura.canon.csutil import profile 
from .. import units

from PyQt4 import QtCore

sep='/'

class EmptyDataset(BaseException):
	pass

def getUsedPrefixes(doc):
	p={}
	for ds in doc.data.values():
		lf=ds.linked
		if lf is None:
			logging.debug('%s %s', 'no linked file for ', ds.name)
			continue
#		print 'found linked file',lf.filename,lf.prefix
		p[lf.filename]=lf
	logging.debug('%s %s %s', 'getUsedPrefixes', p, doc.data.keys())
	return p


def get_linked(doc, params):
		opf=getUsedPrefixes(doc)
		# Find if the filename already has a prefix
		lf=opf.get(params.filename,False)
		if lf is not False:
			return lf
		# Find a new non-conflicting prefix
		prefix=params.prefix
		used=[lf.prefix for lf in opf.values()]
		while prefix in used:
			base, n, pre=iutils.guessNextName(prefix[:-1])
			prefix=pre+':'
		params.prefix=prefix
		LF = linked.LinkedMisuraFile(params)
		LF.prefix=prefix
		logging.debug('%s %s', 'get_linked', prefix)
		return LF

class ImportParamsMisura(base.ImportParamsBase):
	"""misura import parameters.

	additional parameters:
	 reduce: reduce the number of points.
	 reducen: target number of points
	"""
	defaults=deepcopy(base.ImportParamsBase.defaults)
	defaults.update( {
		'prefix':'0:', 
		'version': -1, # means latest
		'reduce': False,
		'reducen': 1000,
		'time_interval': 2,	# interpolation interval for time coord
		'rule_exc': clientconf.rule_exc,
		'rule_inc': clientconf.rule_inc,
		'rule_load': clientconf.rule_load,
		'rule_unit': clientconf.rule_unit,
		})

def not_interpolated(proxy,col,startt,endt):
	"""Retrieve `col` from `proxy` and extend its time range from `startt` to `endt`"""
	logging.debug('%s %s %s %s', 'not interpolating col', col, startt, endt)
	# Take first point to get column start time
	zt=proxy.col(col,0)
	if zt is None or len(zt)==0:
		logging.debug('%s %s %s', 'Skipping column: no data', col, zt)
		return False, False
	zt=zt[0]
	data0=np.array(proxy.col(col,(0,None)))
	#FIXME: now superfluous?
	data=data0.view(np.float64).reshape((len(data0),2))
	# Extend towards start
	s=data[0][0]
	if s>startt:
		d=s-startt
		apt=np.linspace(0,d-1,d)
		vals=np.ones(d)*data[0][1]
		ap=np.array([apt,vals]).transpose()
		logging.debug('%s %s', 'extend towards start', ap.shape)
		data=np.concatenate((ap,data))
	# Extend towards end
	s=data[-1][0]
	d=int(endt-s)
	if d>2:
		logging.debug('%s %s %s %s', 'Extending towards end', s, endt, d)
		apt=np.linspace(s+1,endt+1,d)
		vals=np.ones(d)*data[-1][1]
		ap=np.array([apt,vals]).transpose()
		logging.debug('%s %s %s %s %s %s', 'extend towards end', data.shape, ap.shape, ap, apt, vals)
		data=np.concatenate((data,ap))
	return data.transpose()

def interpolated(proxy,col,ztime_sequence):
	"""Retrieve `col` from `proxy` and interpolate it around `ztime_sequence`"""
	logging.debug('%s %s', 'interpolating col', col)
	tdata=not_interpolated(proxy,col,ztime_sequence[0],ztime_sequence[-1])
	if tdata is False:
		return False
	t,val=tdata[0],tdata[1]
	if val is False or len(val)==0:
		logging.debug('%s %s', 'INTERPOLATING EMPTY COLUMN', col)
		return val
	f=InterpolatedUnivariateSpline(t,val,k=1)
	r=f(ztime_sequence)
	return r


tasks=lambda: getattr(live.registry,'tasks',False)

class OperationMisuraImport(QtCore.QObject,base.OperationDataImportBase):
	"""Import misura HDF File format. This operation is also a QObject so it can send signals to other objects."""
	descr = 'import misura hdf file'
	proxy=False
	rule_exc=False
	rule_inc=False
	rule_load=False
	_rule_load=False
	rule_unit=False
	def __init__(self, params):
		"""Create an import operation on the filename. Update defines if keep old data or completely wipe it."""
		
		QtCore.QObject.__init__(self)
		base.OperationDataImportBase.__init__(self, params)
		
		self.linked = True
		self.filename = params.filename
		
		self.rule_exc=False
		if len(params.rule_exc)>0:
			r=params.rule_exc.replace('\n','|')
			logging.debug('%s %s', 'Exclude rule', r)
			self.rule_exc=re.compile(r)
		self.rule_inc=False
		if len(params.rule_inc)>0:
			r=params.rule_inc.replace('\n','|')
			logging.debug('%s %s', 'Include rule', r)
			self.rule_inc=re.compile(r)			
		self.rule_load=False
		if len(params.rule_load)>0:
			r=params.rule_load.replace('\n','|')
			self._rule_load=r
			logging.debug('%s %s', 'Load rule', r)
			self.rule_load=re.compile(r)
		self.rule_unit=clientconf.RulesTable(params.rule_unit)
					
	def do(self,document):
		"""Override do() in order to get a reference to the document!"""
		self._doc=document
		base.OperationDataImportBase.do(self,document)
		
	def jobs(self,n,pid="File import"):
		t=tasks()
		if not t: return
		t.jobs(n,pid)
		
	def job(self,n,pid="File import",label=''):
		t=tasks()
		if not t: return
		t.job(n,pid,label)
	
	def done(self,pid="File import"):
		t=tasks()
		if not t: return	
		t.done(pid)
		
	def doImport(self):
		"""Import data.  Returns a list of datasets which were imported."""
		# Linked file
		logging.debug('%s', 'OperationmisuraImport')
		doc=self._doc
		if not self.filename:
			logging.debug('%s', 'EMPTY FILENAME')
			return []
		# Get a the corresponding linked file or create a new one with a new prefix
		LF = get_linked(doc,self.params)
		# Remember linked file configuration
		self.params.prefix=LF.prefix
		self.prefix=LF.prefix
		self.jobs(3,'Reading file')
		# open the file
		fp=getattr(doc,'proxy',False)
		logging.debug('%s %s %s %s', 'FILENAME', self.filename, type(fp), fp)
		if fp is False or not fp.isopen():
			logging.debug('%s', 'CREATING NEW FILE PROXY')
			self.proxy=getFileProxy(self.filename)
		else:
			logging.debug('%s', 'COPY FILE PROXY')
			#self.proxy=fp.copy()
			self.proxy=fp
		self.job(1,'Reading file','Configuration')
		if not self.proxy.isopen():
			self.proxy.reopen()
		if self.proxy.conf is False:
			self.proxy.load_conf()
		# Load required version
		self.proxy.set_version(self.params.version)
		conf=self.proxy.conf	#ConfigurationProxy
		LF.conf=conf
		instr=conf['runningInstrument']
		logging.debug('%s %s', 'got runningInstrument', instr)
		LF.instrument=instr
		instrobj=getattr(conf,instr)
		LF.instr=instrobj
		# get the prefix from the test title
		LF.title=instrobj.measure['name']
		self.measurename=LF.title
		
		###
		# Set available curves on the LF
		logging.debug('%s', 'getting header')
		self.job(2,'Reading file','Header')
		header=self.proxy.header(['Array'],'/summary') # Will list only Array-type descending from /summary
		autoload=[]
		excluded=[]
		logging.debug('%s %s', 'got header', len(header))
		# Match rules
		for h in header[:]:
			exc=False
			if self.rule_exc and self.rule_exc.search(h) is not None:
				# Force inclusion?
				if (not self.rule_inc) or (self.rule_inc.search(h) is None):
					exc=True 
			# Force loading?
			if self.rule_load and self.rule_load.search(h) is not None:
				autoload.append(h)
				exc=False
			# Really exclude (no load, no placeholder)
			if exc:
				header.remove(h)
				excluded.append(h)
		logging.debug('%s %s', 'got autoload', autoload)
		logging.debug('%s %s', 'got excluded', len(excluded))
		logging.debug('%s %s', 'got header clean', len(header))
		LF.header=header
		self.jobs(len(header))
		names=[]
		#TODO: Samples are no longer needed?
		refsmp=Sample(linked=LF)
		LF.samples.append(refsmp)
		# build a list of samples
		for idx in range(instrobj.measure['nSamples']):
			smp=getattr(instrobj,'sample'+str(idx), False)
			if not smp: break
			LF.samples.append(Sample(conf=smp, linked=LF, ref=False,idx=idx))
		logging.debug('%s %s %s %s', 'build', idx+1, 'samples', LF.samples)
		elapsed=int(instrobj.measure['elapsed'])+1
		zerotime=int(instrobj['zerotime'])
		end=0
		# Correct elapsed time
		#FIXME: SLOW. Elapsed should be correct!
		for p, col in enumerate(header[:]):
			if isinstance(self.proxy, RemoteFileProxy):
				break
			try:
				if not self.proxy.len(col):
					raise EmptyDataset(col)
				e=self.proxy.col_at(col,-1,raw=True)[0]
				if e>end: end=e
				z=self.proxy.col_at(col,0,raw=True)[0]
				# Update also zerotime, but only if absolute (>zerotime/10.)
				if zerotime/10.<z<zerotime or zerotime<=0: 
					zerotime=z 
			except:
				logging.debug(format_exc())
				logging.debug('%s %s', 'removing column', col)
				header.remove(col)
				continue
			
		if end>zerotime:
			delta=end-zerotime
		else:
			delta=end
		elapsed=int(max(delta,elapsed))+1
		logging.debug('%s %s', 'got elapsed', elapsed)
		# Create time dataset
		time_sequence=[]
		interpolating=True
		if doc.data.has_key(self.prefix+'t'):
			logging.debug('%s %s', 'Document already have a time sequence for this prefix', self.prefix)
			ds=doc.data[self.prefix+'t']
			try:
				ds=units.convert(ds, 'second')
			except:
				pass
			time_sequence=ds.data
		if len(time_sequence)==0:
			time_sequence=np.linspace(0,elapsed-1,elapsed)
		else:
			interpolating=True
		if len(time_sequence)==0:
			logging.debug('%s %s', 'No time_sequence! Aborting.', instrobj.measure['elapsed'])
			return []
		# Detect if time sequence needs to be translated or not.
		if end>zerotime:
			ztime_sequence=time_sequence+zerotime # translated time sequence
		else:
			ztime_sequence=time_sequence
		startt=ztime_sequence[0]
		endt=ztime_sequence[-1]
		outds={}
		availds={}
		for p, col0 in enumerate(['t']+header):
			logging.debug('%s %s %s %s', 'Importing column', p, col0, elapsed)
			col=col0.replace('/summary/', '/')
			mcol=col
			if mcol.startswith(sep): mcol=mcol[1:]
			if mcol.endswith(sep): mcol=mcol[:-1]
			pcol=self.prefix + mcol
			m_var=col.split('/')[-1]
			# Set m_update 
			if m_var=='t' or col0 in autoload:
				logging.debug('%s %s', 'Set for update', col)
				m_update=True
			else:
				logging.debug('%s %s', 'Set for no-update', col)
				m_update=False	
			# Configure dataset
			if not m_update:
				# completely skip processing if dataset is already in document
				if doc.data.has_key(pcol):
					logging.debug('%s %s', 'Skipping column: Document already has this non-autoload dataset', pcol)
					continue
				# data is not loaded anyway
				data=[]
			elif col=='t':
				data=time_sequence
			elif not interpolating:
				logging.debug('%s %s', 'not interpolating', pcol)
				data=not_interpolated(self.proxy,col,startt,endt)[1] # Take values column
			else:
				logging.debug('%s %s', 'interpolating', pcol)
				data=interpolated(self.proxy,col,ztime_sequence)
				
			if data is False:
				logging.debug('%s %s %s', 'Skipping column: no data', p, col)
				data=[]
# 				continue
			# Get meas. unit
			u='None'
			if col=='t':
				u='second'
			else:
				logging.debug('%s %s', 'getting unit', col)
				u=self.proxy.get_node_attr(col,'unit')
				if u in ['','None',None,False,0]: 
					u=False
				# Correct missing celsius indication
				if not u and m_var=='T':
					u='celsius'
				logging.debug('%s %s %s', 'got unit', col, u)
				
			
			logging.debug('%s', 'building the dataset')
			ds=MisuraDataset(data=data, linked=LF)
			ds.m_name=pcol
			ds.tags=set([])
			ds.m_pos=p
			ds.m_smp=refsmp
			ds.m_var=m_var
			ds.m_col=col
			ds.m_update=m_update
			ds.m_conf=self.proxy.conf
			ds.unit=str(u) if u else u
			
			
			# Try to read column metadata
			if len(data)>0 and col!='t':
				for meta in ['percent', 'initialDimension']:
					val=0
					if self.proxy.has_node_attr(col, meta):
						val=self.proxy.get_node_attr(col, meta)
						if type(val)==type([]): 
							val=0
					setattr(ds, 'm_'+meta, val)
				# Units conversion
				nu=self.rule_unit(col)
				if u and nu:
					logging.debug('%s %s %s %s', 'Converting to unit', col, ds.unit, nu)
					ds=units.convert(ds,nu[0])
				
			
			# Find out the sample index to which this dataset refers
			var, idx=iutils.namingConvention(col)
			logging.debug('%s %s %s %s %s', 'Naming convention', col, var, idx, LF.samples)
			if '/sample' in col:
				parts=col.split(sep)
				for q in parts: 
					if q.startswith('sample'): break
				i=int(q[6:])+1
				smp=LF.samples[i]
				logging.debug('%s %s %s %s %s %s', 'Assigning sample', i, 'to curve', col, smp, smp.ref)
				ds.m_smp=smp
				ds.m_var=var
				# Retrieve initial dimension from sample
				if var=='d' and smp.conf.has_key('initialDimension'):
					ds.m_initialDimension=smp.conf['initialDimension']
			if ds.m_smp is False:
				ds.m_smp=refsmp
			# Add the hierarchy tags
			for sub,parent,leaf in iterpath(pcol):
				if leaf:
					ds.tags.add(parent)
			# Actually set the data
# 			LF.children.append(pcol)
			if len(data)>0:
				names.append(pcol)
				outds[pcol]=ds
			else:
				availds[pcol]=ds
			logging.debug('%s %s %s', 'created', col, len(ds.data))
			self.job(p+1)
		logging.debug('%s', 'emitting done')
		self.done()
		self.done('Reading file')
		logging.debug('%s %s', 'imported names:', names)
		self._doc.available_data.update(availds)
		self.outdatasets=outds
		return names


class MisuraCaptureStream(capture.CaptureStream):
	"""CaptureStream object receiving data from a remote Misura file."""
	descr = 'import misura hdf file'
	
	def __init__(self, obj, doc):
		"""Create an import operation on the filename. Update defines if keep old data or completely wipe it."""
		capture.CaptureStream.__init__(self)
		self.doc=doc
		self.obj=obj
		
	def getMoreData(self):
		pass
	
	def close(self):
		pass
		
	def doImport(self):
		"""Import data.  Returns a list of datasets which were imported."""
		logging.debug('%s', 'OperationmisuraImport')
		doc=self._doc
		if not self.filename:
			logging.debug('%s', 'EMPTY FILENAME')
			return []
		# Get a the corresponding linked file or create a new one with a new prefix
		LF = get_linked(doc,self.params)
		self.params.prefix=LF.prefix
		self.prefix=LF.prefix
		
		# open the file
		fp=getattr(doc,'proxy',False)
		logging.debug('%s %s', 'FILENAME', self.filename)
		if fp is False:
			logging.debug('%s', 'CREATING NEW FILE PROXY')
			self.proxy=getFileProxy(self.filename)
		else:
			logging.debug('%s', 'COPY FILE PROXY')
			self.proxy=fp.copy()
		self.proxy.set_version('/conf',self.params.meta_version)
		conf=self.proxy.conf	#ConfigurationProxy
		LF.conf=conf
		instr=self.proxy.get_node_attr('/conf','instrument')
		logging.debug('%s %s', 'got attribute', instr)
		LF.instrument=instr
		instrobj=getattr(conf,instr)
		LF.instr=instrobj
		# get the prefix from the test title
		LF.title=instrobj.measure['name']
		self.measurename=LF.title
		
		
		lastt=self.data['0:t'].data[-1]
		elp=self.proxy.get_node_attr('/conf','elapsed')
		# interval rounding
		elp=(elp//self.interval)*self.interval
		if (elp-lastt)<self.interval:
			logging.debug('%s %s %s', 'Update not needed', elp, lastt)
			return []
		logging.debug('%s %s', 'Update needed: %.2f>%.2f doc' % (elp, lastt))
		nt=list(np.arange(lastt+self.interval,elp,self.interval))
		k=[]
		for col in self.data.iterkeys():
			ds=self.data[col]
			# Skip non-marked
			if not ds.m_update:
				continue
			if col=='t': 
				updata=nt
			else:
				# Ask for interpolated data, from lastt to the end
				updata=self.proxy.interpolated_col(ds.m_col,time_sequence=nt)
			Nu=len(updata)
			if Nu==0:
				continue
			N=len(ds.data)
			ds.insertRows(N,Nu,{'data':updata})
#			print 'Updated',col,N,Nu
			k.append(col)
		self.emit(QtCore.SIGNAL('updated()'))
		return k			
