#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tools and plugins for Veusz, providing Misura Thermal Analysis functionality"""
import os
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
from report_plugin_utils import wr, render_meta


class ReportPlugin(OperationWrapper, plugins.ToolsPlugin):
	def __init__(self, sample=None):
		"""Make list of fields."""
		self.fields = [ 
			FieldMisuraNavigator("sample", descr="Target sample:", depth='sample',default=sample),
		]

	def apply(self, cmd, fields, template_file, measure_to_plot):
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

		d=os.path.join(params.pathArt, template_file)
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
		
		
		msg=''
		
		should_draw_shapes = True

		for sh in ('Sintering', 'Softening','Sphere','HalfSphere','Melting'):
			if not sample.has_key(sh):
				should_draw_shapes = False

		if should_draw_shapes:
			for sh in ('Sintering', 'Softening','Sphere','HalfSphere','Melting'):
				pt=sample[sh]
				if pt['time'] in ['None',None,'']:
					msg+='None\\\\'
					continue
				cf={'dataset':smp_path+'/profile',
					'filename':test.params.filename,
	 				'target':pt['time']-zt}
				dict_toset(page.getChild(sh),cf)
				T='{}{{\\deg}}C'.format(int(pt['temp']))
				self.toset(page.getChild('lbl_'+sh),'label',sh+', '+T)
				msg+=T+'\\\\'
			self.toset(page.getChild('shapes'),'label',msg)
			
			self.dict_toset(page.getChild('initial'),{'dataset':smp_path+'/profile',
	 				'filename':test.params.filename,'target':0})
			T=doc.data[test.prefix+'kiln/T'].data[0]
			self.toset(page.getChild('lbl_initial'),'label','Initial, {}{{\\deg}}C'.format(int(T)))

			self.toset(page.getChild('standard'),'label',wr('Standard',sample['preset'],50))

		

		# Thermal cycle plotting
		from ..graphics.thermal_cycle import ThermalCyclePlot, clean_curve
		graph=report_path+'/tc'
		cf={'graph':graph,'xT':'reportxT','yT':'reportyT','xR':'reportxR','yR':'reportyR'}
		#TODO: convert into a plugin, creating a subplot!
		ThermalCyclePlot.setup(cmd,**cf)
		tc = clean_curve(tc, events=False)
		ThermalCyclePlot.importCurve(cmd,tc,**cf)
		cf={'Label/font':'Bitstream Vera Sans','Label/size':'6pt',
			'TickLabels/font':'Bitstream Vera Sans',
			'TickLabels/size':'6pt'}
		self.dict_toset(doc.resolveFullWidgetPath(graph+'/y'),cf)
		self.dict_toset(doc.resolveFullWidgetPath(graph+'/y1'),cf)


		self.ops.append(document.OperationToolsPlugin(PlotPlugin.PlotDatasetPlugin(),
					{'x':[test.prefix+'kiln/T'],
					'y':[smp_path0+'/'+measure_to_plot],
					'currentwidget':report_path+'/temp'}
					))
		self.apply_ops()
		
		self.dict_toset(doc.resolveFullWidgetPath(report_path+'/temp/ax:' + measure_to_plot),cf)
		self.apply_ops()
		
		
