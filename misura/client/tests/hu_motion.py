#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Display a list of `end` option for all detected motors and updates it."""
from misura.client import widgets
import sys
import logging
from misura.client import iutils, network
from PyQt4 import QtGui, QtCore

def main():
	iutils.initApp()
	network.getConnection('https://localhost:3880', 'admin', 'admin')
	srv=network.manager.remote
	qb=QtGui.QWidget()
	lay=QtGui.QFormLayout()
	wgs=[]
	for d in srv.morla.devices:
		for m in d.devices:
			wg=widgets.build(srv, m, m.gete('end'))
			wgs.append(wg)
			lay.addRow(m['fullpath']+m['name'], wg)
	#		break
	#	break
			
	do=False
	def up():
		logging.debug('%s', 'up')
		global do
		if do: return
		do=True
		for wg in wgs:
			wg.async_get()
		do=False
			
	clock=QtCore.QTimer()
	clock.connect(clock, QtCore.SIGNAL('timeout()'), up)
	clock.start(250)

	#class Thread(QtCore.QThread):
	#	def run(self):
	#		while True:
	#			up()
			
	#t=Thread()
	#t.start()
	qb.setLayout(lay)
	qb.show()
	sys.exit(QtGui.qApp.exec_())
	
if __name__=='__main__':
	main()
	
