#!/usr/bin/python
"""Misura3 database backup utility"""
from PyQt4 import QtCore, QtGui
import pyodbc
import os, tarfile
import sys
import logging
app=QtGui.QApplication(sys.argv)

path=QtGui.QFileDialog.getOpenFileName(None,"Select Misura3 Database","C:\ESS\Misura3\db")
path=str(path)
dirp=os.path.dirname(path)

driver="{Microsoft Access Driver (*.mdb)}"
cs="DRIVER=%s;DBQ=%s;" % (driver, path)
conn = pyodbc.connect(cs)
cursor=conn.cursor()
cursor.execute("select * from PROVE")
tests=cursor.fetchall()

bkpath=path+'_backup.tar'
bk=tarfile.TarFile(bkpath, 'w')
logging.debug('%s %s', 'Created ', bkpath)
bk.add(path, arcname=os.path.basename(path))
logging.debug('%s %s', 'Added mdb', path)
N=len(tests)
for i, test in enumerate(tests):
	if test[3] not in [0,1,2,3,4,110,111]: 
		logging.debug('%s %s %s', 'No img for ', test[0], test[3])
		continue
	imgd=test[0][:5].upper()
	idt=os.path.join(dirp,imgd)
	if not os.path.exists(idt): 
		logging.debug('%s %s %s', 'No dir for ', test[0], test[3])
		continue
	logging.debug('%s %s %s', 'add', idt, 100*i/N)
	bk.add(idt, arcname=imgd)
bk.close()
logging.debug('%s %s', 'closed', bkpath)

sys.exit(0)
