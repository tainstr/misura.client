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
import pkgutil
from xml.sax.saxutils import escape,unescape
pathClient=os.path.dirname(__file__)
pathLang=os.path.join(pathClient, 'i18n')


def mescape(s):
	s=escape(s)
# 	s=s.replace('"','&quot;')
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
	"""Add already translated values to the context `ctx`."""
	c=False; s=False; t=False; m=''
	ctx=ctx.copy()
	filename=os.path.join(pathLang, base+'_'+lang+'.ts')
	# No previous translations: nothing to update!
	if not os.path.exists(filename):
		print lang.upper(),'\tOriginal translation not found:',filename
		return ctx
	# Update from found filename
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
	"""Output context to .ts formatted file"""
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

# this is the package we are inspecting -- for example 'email' from stdlib
def collect_conf(module,translations):
	"""Scan a module for all classes defining a conf_def iterable attribute."""
	names=dir(module)
	missing=0
	for name in names:
		obj=getattr(module,name,False)
		if obj is False: continue
		if not hasattr(obj,'conf_def'): continue
		conf_def=getattr(obj,'conf_def')
		if not conf_def: continue
		print 'Found conf_def',obj.__name__,conf_def
		for el in conf_def:
			if not isinstance(el,dict): continue
			tr=el.get('name',False)
			if not tr: continue
			h=el.get('handle',False)
			if not h:
				missing+=1
				h='!!!_missing_handle_{}'.format(missing)
			print obj,h,tr
			translations[h]=tr
			# Get translatable option names
			opt=el.get('options', False)
			if not opt: 
				continue
			if not el.has_key('values'):
				continue
			for i,o in enumerate(opt):
				h1=h+'_opt{}'.format(i)
				translations[h1]=o
	return translations,missing
		
def iterpackage(package):
	"""Scan a package for all subpackages and all modules containing classes defining conf_def attribute.
	Accept an imported module as argument. 
	Returns translations dictionary and missing count."""
	prefix = package.__name__ + "."
	translations={}
	missing=0
	for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
		if modname.split('.')[-1] in ('client','canon','libvideodev','utils'):
			print 'skipping', modname
			continue
		print "Found submodule %s (is a package: %s)" % (modname, ispkg)
		module = __import__(modname, fromlist="dummy")
		print "Imported", module
		translations,ms=collect_conf(module,translations)
		missing+=ms
		if ispkg:
			iterpackage(module)
	return translations, missing


def collect():
	"""Collect translatable strings from static source code analysis.
	Returns all collected strings."""

	import misura
	translations,missing=iterpackage(misura)
	print 'Stats',len(translations),len(set(translations)), missing
	
	out=open('static.txt','w')
	for h,tr in translations.iteritems():
		out.write('{}\t{}\n'.format(h,tr))
	out.close()
	return translations.values()
		

from misura.client.linguist import context_separator
def language_sync():
	"""Merge all translatable strings from runtime requests, code analysis, already translated code."""
	# Translation contexts
	contexts={'Option':{}}
	# Collect from runtime
	rt=os.path.join(pathLang,'runtime.dat')
	if os.path.exists(rt):
		runtime=open(rt,'r').read().splitlines()
		# purge duplicates
		runtime=list(set(runtime))

		for e in runtime:
			c,e=e.split(context_separator)
			e.replace('$newline$', '\n')
			if not contexts.has_key(c):
				contexts[c]={}
			contexts[c][mescape(e)]=('', '')
	# Collect from code analysis
	trcode=collect()
	out=open(os.path.join(pathLang,'static.dat'),'w')
	for v in trcode:
		v=mescape(v)
		out.write('{}\n'.format(v))
		contexts['Option'][v]=('','')
	out.close()
	
	statistics={}
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
