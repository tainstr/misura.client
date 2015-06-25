#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import os
from textwrap import wrap, fill
import datetime
from misura.canon.logger import Log as logging

import veusz
import veusz.plugins as plugins
import veusz.document as document
from veusz.document import CommandInterpreter

from .. import parameters as params
from FieldMisuraNavigator import FieldMisuraNavigator
import PlotPlugin
from ThermalCyclePlugin import drawCycleOnGraph
from utils import OperationWrapper
	
def wr(k,v,n=18,inter=' '):
	k=wrap('{}:'.format(k),n)
	for i,e in enumerate(k):
		e='\\bold{{'+e+'}}'
		k[i]=e
	k='\\\\'.join(k)
	k=k.replace('_','\\_')
	
	v=wrap('{}'.format(v),n)
	v='\\\\'.join(v)
	v=v.replace('_','\\_')
	r='{}{}{}'.format(k,inter,v)
	logging.debug('%s %s %s %s', 'wrapped', k, v, r)
	return r

invalid=(None,'None','')

def render_meta(obj,notfound=False,n=30,inter=' ', full=False, zt=0):
	msg=''
	meta=[]
	for k,m in obj.describe().iteritems():
		if m['type']!='Meta':
			continue
		meta.append(m)
	meta=sorted(meta,key=lambda m: m['priority'])
	for m in meta:
		c=m['current']
		if c['temp'] in invalid:
			if not notfound:
				continue
			v=notfound
		else:
			v='{} {{\\deg}}C'.format(int(c['temp']))
			if full:
				if c['value'] not in invalid:
					v+=', {:.2f}'.format(c['value'])
				if c['time'] not in invalid:
					t=c['time']
					if t>zt: t-=zt
					logging.debug('%s %s %s %s', 'render time', c['time'], t, zt)
					v+=', {}'.format(datetime.timedelta(seconds=int(t)))
		w=wr(m['name'],v, n=n,inter=inter)
		msg+='\\\\'+w
	return msg

class HsmReportPlugin(OperationWrapper,plugins.ToolsPlugin):
	"""Show Misura Microscope shapes in graphics"""
	# a tuple of strings building up menu to place plugin on
	menu = ('Misura','Report')
	# unique name for plugin
	name = 'Report'
	# name to appear on status tool bar
	description_short = 'Create Report'
	# text to appear in dialog box
	description_full = 'Create Report on new page'
	
	def __init__(self,sample=None):
		"""Make list of fields."""
		self.fields = [ 
			FieldMisuraNavigator("sample", descr="Target sample:", depth='sample',default=sample),
		]

	def apply(self, cmd, fields):
		doc=cmd.document
		self.doc=doc
		exe=CommandInterpreter(doc)
		smp_path0=fields['sample'].path
		smp_path=smp_path0.split(':')[1]
		vsmp=smp_path.split('/')
		smp_name=vsmp[-1] # sample name
		smp_path='/'+'/'.join(vsmp) # cut summary/ stuff
		report_path='/report'
		logging.debug('%s %s %s', smp_path, smp_name, report_path)
		test=fields['sample'].linked
		from .. import filedata
		if not filedata.ism(test, filedata.LinkedMisuraFile): 
			logging.debug('%s %s', type(test), test)
			raise plugins.ToolsPluginException('The target must be misura test file')
		# Search for test name
		uk=test.prefix+'unknown'
		kiln=getattr(test.conf,'kiln',False)
		if not kiln:
			raise plugins.ToolsPluginException('No Kiln configuration found.')
		instr=getattr(test.conf,test.instrument,False)
		if not instr:
			raise plugins.ToolsPluginException('No measure configuration found.')
		measure=instr.measure
		
		sample=getattr(instr,smp_name)

#		d=list(os.path.split(parameters.pathClient))[:-1]+['client','art','report_hsm.vsz']
#		d=os.path.join(*tuple(d))
		d=os.path.join(params.pathArt,'report_hsm.vsz')
		#TODO: replace report path
		tpl=open(d,'rb').read()
		exe.run(tpl)
				
		page=doc.resolveFullWidgetPath(report_path)
		# Substitutions
		tc=kiln['curve']
		if len(tc)<=8:
			drawCycleOnGraph(cmd,tc,label=False,wdg=report_path+'/lbl_tc',color='black',size='6pt',create=False)
		else:
			self.toset(page.getChild('lbl_tc'),'hide',True)
		msg=wr('Measure',measure['name'])
		msg+='\\\\'+wr('Sample',sample['name'])		
		self.toset(page.getChild('name'),'label',msg)
		
		zt=test.conf['zerotime']
		zd=datetime.date.fromtimestamp(zt)
		dur=datetime.timedelta(seconds=int(measure['elapsed']))
		sdur='{}'.format(dur)
		msg=wr('Date',zd.strftime("%d/%m/%Y"))
		msg+='\\\\'+wr('Duration',sdur)
		msg+=render_meta(measure,inter='\\\\',zt=zt,full=True)
		self.toset(page.getChild('metadata'),'label',msg)
		
# 		msg=render_meta(sample,'None')
# 		self.toset(page.getChild('shapes'),'label',msg)
		
		oname=measure.desc.get('operator', {'current':False})['current']
		if oname:
			self.toset(page.getChild('operator'), 'label',wr('Operator',oname))
		self.toset(page.getChild('uid'),'label',wr('UID',measure['uid'],34))
		self.toset(page.getChild('serial'),'label',wr('Serial',test.conf['eq_sn']))
		self.toset(page.getChild('furnace'),'label',wr('Furnace',kiln['ksn']))
		self.toset(page.getChild('standard'),'label',wr('Standard',sample['preset'],50))
		
		#ImageReference
		msg=''
		for sh in ('Sintering', 'Softening','Sphere','HalfSphere','Melting'):
			pt=sample[sh]
			if pt['time'] in ['None',None,'']:
				msg+='None\\\\'
				continue
			cf={'dataset':smp_path+'/profile',
				'filename':test.params.filename,
 				'target':pt['time']-zt}
			self.dict_toset(page.getChild(sh),cf)
			T='{}{{\\deg}}C'.format(int(pt['temp']))
			self.toset(page.getChild('lbl_'+sh),'label',sh+', '+T)
			msg+=T+'\\\\'
		self.toset(page.getChild('shapes'),'label',msg)
		# initial shape
		self.dict_toset(page.getChild('initial'),{'dataset':smp_path+'/profile',
 				'filename':test.params.filename,'target':0})
		T=doc.data[test.prefix+'kiln/T'].data[0]
		self.toset(page.getChild('lbl_initial'),'label','Initial, {}{{\\deg}}C'.format(int(T)))
		

		# Thermal cycle plotting
		from ..graphics.thermal_cycle import ThermalCyclePlot
		graph=report_path+'/tc'
		cf={'graph':graph,'xT':'reportxT','yT':'reportyT','xR':'reportxR','yR':'reportyR'}
		#TODO: convert into a plugin, creating a subplot!
		ThermalCyclePlot.setup(cmd,**cf)
		ThermalCyclePlot.importCurve(cmd,tc,**cf)
		cf={'Label/font':'Bitstream Vera Sans','Label/size':'6pt',
			'TickLabels/font':'Bitstream Vera Sans',
			'TickLabels/size':'6pt'}
		self.dict_toset(doc.resolveFullWidgetPath(graph+'/y'),cf)
		self.dict_toset(doc.resolveFullWidgetPath(graph+'/y1'),cf)


		# Volume plotting
		self.ops.append(document.OperationToolsPlugin(PlotPlugin.PlotDatasetPlugin(),
					{'x':[test.prefix+'kiln/T'],
					'y':[smp_path0+'/Vol'],
					'currentwidget':report_path+'/temp'}
					))
		self.apply_ops()
		
		self.dict_toset(doc.resolveFullWidgetPath(report_path+'/temp/ax:Vol'),cf)
		self.apply_ops()
		
		
		
		
		
		
		
		

		
plugins.toolspluginregistry.append(HsmReportPlugin)
