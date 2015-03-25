#!/usr/bin/python
from veusz.plugins import *
#import pkg_resources
#pkg_resources.require('tables')
import tables
import os
print 'Importing misura Plugin'
class ImportPluginmisura(ImportPlugin):
	"""misura Import Plugin"""
	
	name = "misura Hierarchical Data Format Plugin"
	author = "Daniele Paganelli"
	description = "Reads a misura test file in hdf5 format"
	
	def __init__(self):
		ImportPlugin.__init__(self)
		self.fields = [ImportFieldText("name", descr="Dataset name", default="name")]
	
	def doImport(self, params):
		"""Actually import data
		params is a ImportPluginParams object.
		Return a list of ImportDataset1D, ImportDataset2D objects
		"""
		f = tables.openFile(params.filename, 'r')
		sum=f.root.summary
		name=params.field_results["name"]
		out=[]
		for col in sum.colnames:
			if col.endswith('_img'): continue
			ds=ImportDataset1D(name+':'+col, sum.col(col)[:])
			out.append(ds)
		f.close()
		return out
		
	def getPreview(self, params):
		if not os.path.exists(params.filename):
			return 'File does not exist.', False
		try:
			f=tables.openFile(params.filename, 'r')
		except:
			return 'Error opening the file.', False
		msg='Successfully opened misura File with %i summary points.\n' % f.root.summary.attrs.NROWS
		msg+='Available fields:\n'
		msg+='\n'.join(f.root.summary.colnames)
		return msg, True
		

importpluginregistry.append(ImportPluginmisura())
	
