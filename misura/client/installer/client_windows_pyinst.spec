# -*- mode: python -*-
"""SPEC File for PyInstaller - Windows Binary"""
from glob import glob
import os.path
from misura.client.parameters import pathClient
from veusz import utils as vutils

# Check cv is installed
import cv2 

console = False
debug = False
cli=pathClient+'\\'
bin=cli+'bin\\'
res=vutils.resourceDirectory+'\\'
vzd=res+'..\\'


rthooks=[cli+'\\installer\\rthook_pyqt4.py']
# Hidden imports
him=['misura.canon','misura.canon.csutil','misura.client','cv2','scipy.special._ufuncs_cxx',
'astropy', 'scipy.odr' ,'scipy.odr.odrpack','veusz.helpers.qtloops' ,'veusz.helpers.qtmml', 
'veusz.helpers.recordpaint', 'veusz.helpers._nc_cntr' ]
# Excluded imports
exim=['Tkinter']

# VEUSZ ANALYSIS

a = Analysis([ bin+'main.py'],
             pathex=[bin],
             excludes=exim,
             hiddenimports=him,
             runtime_hooks=rthooks)


	
exename = os.path.join('build','misura.exe')

print 'Building PYZ',exename
pyz = PYZ(a.pure)
print 'Creating EXE',exename
exe = EXE(pyz,
		  a.scripts,
		  exclude_binaries=1,
		  name=exename,
		  debug=debug,
		  strip=None,
		  upx=False,
		  console=console,
		  icon=cli+'art\\' + 'misura.ico')
		  
# get rid of debugging binaries
a.binaries = [b for b in a.binaries if b[0][-6:] != 'd4.dll']

# don't want kernel32, etc
a.binaries = [b for b in a.binaries if not (os.path.basename(b[0]) in
              ('kernel32.dll', 'Qt3Support4.dll',
               'QtNetwork4.dll', 'QtOpenGL4.dll', 'QtSql4.dll'))]

# remove unneeded plugins
for pdir in ('accessible', 'codecs', 'graphicssystems'):
    a.binaries = [b for b in a.binaries if b[1].find(os.path.join(vzd,'plugins', pdir)) == -1]

# add necessary documentation, licence
for fn in ('VERSION', 'ChangeLog', 'AUTHORS', 'README', 'INSTALL', 'COPYING'):
    a.binaries += [ (fn, cli+fn, 'DATA') ]

# add various required files to distribution
for name in ['icons/*.png','icons/*.ico','icons/*.svg','examples/*.vsz',
			'examples/*.dat','examples/*.csv','examples/*.py','ui/*.ui','widgets/data/*.dat']:
	basedir=os.path.dirname(name)
	for source_path in glob(os.path.join(res,name)):
		fname=os.path.basename(source_path)
		installed_path=os.path.join(basedir,fname)
		a.binaries.append( (installed_path, source_path, 'DATA') )

# misura4 specific data dirs

def add_binaries(fdir, ddir):
    for fname in os.listdir(fdir):
        source_path=os.path.join(fdir,fname)
        installed_path=os.path.join(ddir,fname)
        if os.path.isdir(source_path):
            add_binaries(source_path, os.path.join(ddir, fname))
        else:
            a.binaries.append( (installed_path,source_path,'DATA') )
        
for ddir in ['art','i18n','ui']:
    fdir=os.path.join(cli,ddir)
    add_binaries(fdir, ddir)

print 'BINARIES', a.binaries


		  
print 'Collecting',exename
coll = COLLECT( exe,
			   a.binaries,
			   a.zipfiles,
			   a.datas,
			   strip=None,
			   upx=False,
			   name=os.path.join('main'))
