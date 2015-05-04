#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Translation utilities"""
from PyQt4 import QtGui
from traceback import print_exc

# maskmap={u'-': '.$line$.',
# 		u'_': '.$unsc$.',
# 		u'°': '.$deg$.',
# 		u'\u03bc':'.$micro$.',
# 		u'\u2030':'.$permille$.',
# 		u'²':'.$^2$.',
# 		u'³':'.$^3$.',
# 		}
# unmaskmap={}
# for k,v in maskmap.iteritems():
# 	unmaskmap[v]=k
# 
# def tr_mask(s):
# 	return s.replace('-', '.|line|.').replace('_', '.|unsc|.').replace('\uc9f8', '.|deg|.')
# 
# def tr_unmask(s):
# 	return s.replace('.|line|.', '-').replace('.|unsc|.', '_').replace('.|deg|.', '\uc9f8')


context_separator=':$ctx$:'

class Linguist(object):
	def __init__(self, context='Main'):
		self.context=context
		# funzione mtr() per mascherare a pylupdate4 le stringhe da non tradurre
		self.mtr=self.tr
	def tr(self, ostr, context='Undefined'):
		if QtGui.qApp==None: return ostr
		mstr=ostr
#		mstr=tr_mask(ostr)
		try:
			tr=QtGui.qApp.translate(self.context, mstr)
		except:
			print_exc()
			tr=mstr
# 		tr=tr_unmask(tr)
		#If linguist is active, annotate any untranslated sting
		from misura.client import iutils
		if iutils.linguist and tr==ostr:
			ostr=ostr.replace('\n', '$newline$')
			print 'writing',self.context+context_separator+ostr
			iutils.linguist.write(self.context+context_separator+ostr+'\n')
			iutils.linguist.flush()
		return tr
	
