# -*- mode: python -*-
"""SPEC File for PyInstaller - Windows Binary"""
from glob import glob
import os.path
from misura.client.parameters import pathClient
from veusz import utils as vutils

console=True
debug=False
cli=pathClient+'\\' 
bin=cli+'bin\\'
res=vutils.resourceDirectory+'\\' 
vzd=res+'..\\' 


rthooks=[cli+'\\installer\\rthook_pyqt4.py']
# Hidden imports
him=['misura.canon','misura.canon.csutil','misura.client','cv2','scipy.special._ufuncs_cxx','astropy'  ]
# Excluded imports
exim=['Tkinter']
Analyses=[]

# VEUSZ ANALYSIS

a = Analysis([ bin+'graphics.py'],
             pathex=[bin],
             excludes=exim,
             hiddenimports=him,
             runtime_hooks=rthooks)

# get rid of debugging binaries
a.binaries = [b for b in a.binaries if b[0][-6:] != 'd4.dll']

# don't want kernel32, etc
a.binaries = [b for b in a.binaries if not (os.path.basename(b[0]) in
              ('kernel32.dll', 'Qt3Support4.dll',
               'QtNetwork4.dll', 'QtOpenGL4.dll', 'QtSql4.dll'))]

# remove unnedded plugins
for pdir in ('accessible', 'codecs', 'graphicssystems'):
    a.binaries = [b for b in a.binaries if b[1].find(os.path.join(vzd,'plugins', pdir)) == -1]

# add necessary documentation, licence
binaries = a.binaries
for fn in ('VERSION', 'ChangeLog', 'AUTHORS', 'README', 'INSTALL', 'COPYING'):
    binaries += [ (fn, res+fn, 'DATA') ]

# add various required files to distribution
for name in ['icons/*.png','icons/*.ico','icons/*.svg','examples/*.vsz',
			'examples/*.dat','examples/*.csv','examples/*.py','ui/*.ui','widgets/data/*.dat']:
	basedir=os.path.dirname(name)
	for source_path in glob(os.path.join(res,name)):
		fname=os.path.basename(source_path)
		installed_path=os.path.join(basedir,fname)
		binaries.append( (installed_path, source_path, 'DATA') )

# misura4 specific data dirs
for ddir in ['art','i18n']:
	fdir=os.path.join(cli,ddir)
	for fname in os.listdir(fdir):
		source_path=os.path.join(fdir,fname)
		installed_path=os.path.join(ddir,fname)
		binaries.append( (installed_path,source_path,'DATA') )

Analyses.append( (a,'misura4', os.path.join('build','graphics.exe')) )

# MISURA 4 ANALYSIS
AppNames=['acquisition.py','archive.py' ,'conf.py']
BaseNames=['acquisition','archive','configuration']
ExeNames=['acquisition.exe','archive.exe','conf.exe']

for i,name in enumerate(AppNames):
	print 'Analyzing ',bin+name
	a = Analysis([bin+name],
				 pathex=[bin],
				 excludes=exim,
				 hiddenimports=him,
				 runtime_hooks=rthooks)
	Analyses.append((a,BaseNames[i],os.path.join('build',ExeNames[i])))

print 'Merging analyses',Analyses
MERGE(*Analyses)

for an, basename, exename in Analyses:
	print 'Building PYZ',basename,exename
	pyz = PYZ(an.pure)
	print 'Creating EXE',basename,exename
	exe = EXE(pyz,
	          an.scripts,
	          exclude_binaries=1,
	          name=exename,
	          debug=debug,
	          strip=None,
	          upx=False,
	          console=console,
	          icon=cli+'art\\favicon.ico')
	print 'Collecting',basename,exename
	coll = COLLECT( exe,
	               an.binaries,
	               an.zipfiles,
	               an.datas,
	               strip=None,
	               upx=False,
	               name=os.path.join('dist',basename))
