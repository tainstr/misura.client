#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Aggiornamento del progetto di traduzione in base al file runtime generato con l'opzione parameters.linguist=True"""

langs=['it', 'de', 'fr', 'es','en']

header="""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.0" language="%s">
"""

context_h="""
<context>
    <name>%s</name>
"""

context_f="</context>"
footer="</TS>"

entry="""
    <message>
        <source>%s</source>
	<translation>%s</translation>
	<translatorcomment>%s</translatorcomment>
    </message>
"""
u_entry="""
    <message>
        <source>%s</source>
	<translation type="unfinished">%s</translation>
	<translatorcomment>%s</translatorcomment>
    </message>
"""

from time import time
from sys import argv
import os
from xml.sax.saxutils import escape,unescape
pathClient=os.path.dirname(__file__)
pathLang=os.path.join(pathClient, 'i18n')
def mescape(s):
	s=unescape(s)
	s=s.replace('"','&quot;')
	return s

def tag(g,line,o):
	if "<%s>" % g in line:
		return line.split(g+'>')[1][:-2]
	return o

def stats(ctx):
	ct=0; done=0; undone=0
	for c, v in ctx.iteritems():
		ct+=1
		for s, m in v.iteritems():
			if m[0]=='': undone+=1
			else: done+=1
	return [ct, done, undone]
	
def update(lang,ctx,base='misura'):
	"""Aggiungi al contexts tutti valori già tradotti"""
	c=False; s=False; t=False; m=''
	ctx=ctx.copy()
	filename=os.path.join(pathLang, base+'_'+lang+'.ts')
	if not os.path.exists(filename):
		print lang.upper(),'\tOriginal translation not found:',filename
		return ctx
	for line in open(filename,'r'):
		if '<context>' in line: 
			c=False; s=False; t=False; m=''
		if '<message>' in line: 
			s=False; t=False; m=''
		c=tag('name',line,c)
		s=tag('source',line,s)
		t=tag('translation',line,t)
		m=tag('translatorcomment',line,m)
		if '</message>' in line and c and s:
			if not ctx.has_key(c):
				ctx[c]={}
			s=mescape(s)
			if not t: t=''
			t=mescape(t)
#			print '\tfound translation:',c,s,t
			ctx[c][s]=(t, m)
	return ctx

def write_ts(lang,ctx):
	filename=os.path.join(pathLang, 'misura_'+lang+'.ts')
	out=open(filename,'w')
	out.write(header % lang)
	for c, ent in ctx.iteritems():
		out.write(context_h % c)
		print '\tContext:',c
		for s, e in ent.iteritems():
			if e[0]=='': out.write(u_entry % (s, e[0], e[1]))
			else: out.write(entry % (s, e[0], e[1]))
		out.write(context_f)
	out.write(footer)

def language_sync():
	# Raccogli tutte le richieste di traduzione lanciate a runtime
	runtime=open(os.path.join(pathLang,'runtime.dat'),'r').read().splitlines()
	# creo un insieme (elimino tutti i duplicati)
	runtime=list(set(runtime))
	# Contestualizza tutte le richieste 
	contexts={}
	for e in runtime:
		c,e=e.split('::')
		e.replace('$newline$', '\n')
		if not contexts.has_key(c):
			contexts[c]={}
		contexts[c][mescape(e)]=('', '')
	
	statistics={}
	from copy import deepcopy
	for l in langs:
		print 'LANGUAGE:',l
		ctx=update(l,contexts.copy(),base='misura')
		ctx=update(l,ctx)
		write_ts(l,ctx)
		statistics[l]=stats(ctx)
		# cancello tutte le traduzioni, mantenendo però le chiavi
		contexts={}
		for c,  v in ctx.iteritems():
			if not contexts.has_key(c): 
				contexts[c]={}
			for k, e in v.iteritems():
				contexts[c][k]=('', '')
		
				
	
	print 'Completeness:'
	for l in langs:
		s=statistics[l]
		print '%s: %.2f %% (missing: %i)' % (l.upper(), 100.*s[1]/(s[1]+s[2]), s[2])

if __name__=='__main__':
	language_sync()
