#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Esempio di script per i test di elasticità tramite carico/scarico su campione FLEX"""

from misura.canon.logger import Log as logging
from time import sleep
from sys import argv,exit
from numpy import *



def wait(pos):
	"""Attendi che il motore raggiunga una certa posizione"""
	obj['goingTo']=pos
	now=pos+1
	while now!=pos:
		sleep(.1)
		now=obj['position']
		logging.debug('%s %s %s', 'waiting ', pos, now)

def main():
	from m4script import m4
	unload=0		# Posizione di scarico
	load=10000		# Posizione di carico
	obj=m4.morla.idx0.X		# Motore che gestisce l'automatismo
	N=int(argv[1])	# Numero di ripetizioni impostato da riga di comando
	
	# Reimposta sempre accelerazione e velocità
	obj['sloPe']=3500
	obj['Rate']=12000
	for i in range(N):
		wait(unload)
		sleep(2)
		upos=m4.flex.camera['pos']
		wait(load)
		d=upos-m4.flex.camera['pos']
		msg='[%i:%.2f%%] Displacement: %i' % (i,100.*i/N,d)
		m4.send_log(msg)
		logging.debug('%s', msg)
		sleep(1)
	
	wait(unload)
	sleep(10)
	logging.debug('%s', 'Stopping acquisition')
	m4.flex.stop_acquisition()

if __name__=='__main__':
	main()
	
	