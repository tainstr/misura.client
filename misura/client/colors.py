#!/usr/bin/python
# -*- coding: utf-8 -*-

from numpy import prod

def colorLevels(n):
	"""Determine best number of color levels in order to obtain at least `n` combinations"""
	m=n
	i=-1
	L=int(n**(1./3))+1
	LR,LG,LB=[L]*3
	while m>0:
		i+=1
		vL=[LR,LG,LB]
		vL[i%3]-=1
		m=prod(vL)-n
		if m<0: break
		LR,LG,LB=vL
		if m==0: break
	print 'levels',LR,LG,LB
	return LR,LG,LB

# Conversione da tupla R,G,B a codice HTML compreso da Veusz
hexcolor = lambda rgb: '#%02x%02x%02x' % rgb
		
def colorize(v,LR,LG,LB):
	"""Generate a color for value v in range n """
	R=(v//(LB*LG)) % LR
	G=(v//(LB)) % LG
	B=v % LB
	R=(R*255./LR)
	G=(G*255./LG)
	B=(B*255./LB)
	return '#%02x%02x%02x' % (R,G,B)

colors=['black', 'red', 'green', 'blue', 'magenta','cyan','yellow', 'grey', 'darkred', 'darkgreen']*5