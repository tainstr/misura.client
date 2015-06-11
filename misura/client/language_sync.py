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

import logging
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
		logging.debug('%s %s %s', lang.upper(), '\tOriginal translation not found:', filename)
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
		logging.debug('%s %s', '\tContext:', c)
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
		logging.debug('%s %s %s', 'Found conf_def', obj.__name__, conf_def)
		for el in conf_def:
			if not isinstance(el,dict): continue
			tr=el.get('name',False)
			if not tr: continue
			h=el.get('handle',False)
			if not h:
				missing+=1
				h='!!!_missing_handle_{}'.format(missing)
			logging.debug('%s %s %s', obj, h, tr)
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
			logging.debug('%s %s', 'skipping', modname)
			continue
		logging.debug('%s %s', "Found submodule %s (is a package: %s)" % (modname, ispkg))
		module = __import__(modname, fromlist="dummy")
		logging.debug('%s %s', "Imported", module)
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
	logging.debug('%s %s %s %s', 'Stats', len(translations), len(set(translations)), missing)
	
	out=open('static.txt','w')
	for h,tr in translations.iteritems():
		out.write('{}\t{}\n'.format(h,tr))
	out.close()
	return translations.values()

######################
# CLIENT CODE ANALYSIS - From Veusz pyqt_find_translatable
######################
import ast
import sys
import os


class Message(object):
	'''A translatable string.'''
	def __init__(self, string, filename=None, lineno=None, comment=None):
		self.string = string
		self.filename = filename
		self.lineno = lineno
		self.comment = comment

class PythonMessageVisitor(ast.NodeVisitor):
	'''A visitor which visits function calls and definitions in source.'''

	def __init__(self, filename, outmessages, verbose=True):
		'''filename is file being read
		If set, mapping of context to Messages will be returned in
		outmessages.'''

		self.filename = filename

		# map translation functions to contexts
		self.fn2context = {}
		# arguments for functions
		self.fnargs = {}

		self.messages = outmessages
		self.verbose = verbose

	def visit_Call(self, obj):
		'''Function call made.'''

		# this needs to be called to walk the tree
		self.generic_visit(obj)

		try:
			fn = obj.func.id
		except AttributeError:
			# no name known
			return

		if fn not in self.fn2context:
			return

		if len(obj.args)+len(obj.keywords) not in (1,2,3) or len(obj.args) < 1:
			sys.stderr.write(
				'WARNING: Translatable call to %s in %s:%i '
				'requires 1 to 3 parameters\n' %
				(repr(fn), self.filename, obj.lineno))
			return

		# convert arguments to text
		try:
			args = [a.s for a in obj.args]
			keywords = dict([(a.arg, a.value.s) for a in obj.keywords])
		except AttributeError:
			sys.stderr.write(
				'WARNING: Parameter to translatable function '
				'%s in %s:%i is not string\n' %
				(repr(fn), self.filename, obj.lineno))
			return

		# defaults
		text = args[0]
		context = self.fn2context[fn]
		comment = None

		# examine any unnamed arguments
		ctxidx = self.fnargs[fn].index('context')
		if len(args) > ctxidx:
			context = args[ctxidx]
		disidx = self.fnargs[fn].index('disambiguation')
		if len(args) > disidx:
			comment = args[disidx]

		# now look at named arguments which override defaults
		context = keywords.get('context', context)
		comment = keywords.get('disambiguation', comment)

		# create new message
		if context not in self.messages:
			self.messages[context] = []
		self.messages[context].append(
			Message(text, filename=self.filename, lineno=obj.lineno,
					comment=comment) )

		if self.verbose:
			sys.stdout.write(
				'Found text %s (context=%s, disambiguation=%s) in %s:%i\n' %
				(repr(text), repr(context), repr(comment),
				 self.filename, obj.lineno))

	def visit_FunctionDef(self, obj):
		'''Function definition made.'''

		# this needs to be called to walk the tree
		self.generic_visit(obj)

		try:
			name = obj.name
		except AttributeError:
			return

		args = obj.args
		# want a three-parameter function with two default values
		if len(args.args) != 3 or len(args.defaults) != 2:
			return

		argids = [a.id.lower() for a in args.args]
		# only functions with disambiguation and context as optional arguments
		if 'disambiguation' not in argids or 'context' not in argids:
			return

		contextidx = argids.index('context')
		try:
			context = args.defaults[contextidx-1].s
		except AttributeError:
			sys.stderr.write(
				"WARNING: Translation function definition %s in "
				"%s:%i does not have default string for 'context'\n" %
				(repr(name), self.filename, obj.lineno))
			return

		if name in self.fn2context:
			sys.stderr.write(
				'WARNING: Duplicate translation function %s '
				'in %s:%i\n' % (repr(name), self.filename, obj.lineno))
			return

		if self.verbose:
			sys.stdout.write(
				'Found translation function %s with default '
				'context %s in %s:%i\n' %
				(repr(name), repr(context), self.filename, obj.lineno))

		# map function name to default context
		self.fn2context[name] = context
		self.fnargs[name] = argids
		
def python_find_strings(filename, retn, verbose=True,
					gcontext={'_':'misura'},
					gargs={'_':('text','disambiguation','context')}):
	'''Update output in retn with strings in filename.'''

	if verbose:
		sys.stdout.write('Examining file %s\n' % repr(filename))
	with open(filename) as f:
		source = f.read()

	tree = ast.parse(source, filename)

	v = PythonMessageVisitor(filename, retn, verbose=verbose)
	v.fn2context=gcontext.copy()
	v.fnargs=gargs.copy()
	v.visit(tree)
	
def scan_client_source(path,out=False):
	retn={}
	for root, dirs, files in os.walk(path):
		for fn in files:
			if not fn.endswith('.py'): continue
			fp=os.path.join(root,fn)
			logging.debug('%s %s', 'Scanning', fp)
			python_find_strings(fp,retn)
	# Simplify output
	if not out: out={}
	for ctx, msgs in retn.iteritems():
		if not out.has_key(ctx): out[ctx]=[]
		out[ctx]+=[msg.string for msg in msgs]
	return out

######################
# END OF CLIENT CODE ANALYSIS 
######################
from misura.client.parameters import pathClient

def language_sync():
	"""Merge all translatable strings from runtime requests, code analysis, already translated code."""
	# Translation contexts
	contexts={'Option':{}}

	# Collect from server code analysis
	trcode=collect()
	for v in trcode:
		v=mescape(v)
		contexts['Option'][v]=('','')
	
	# Collect from client code analysis
	scan_client_source(pathClient)
	
	statistics={}
	for l in langs:
		logging.debug('%s %s', 'LANGUAGE:', l)
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
	
	logging.debug('%s', 'Completeness:')
	for l in langs:
		s=statistics[l]
		logging.debug('%s %s %s', '%s: %.2f %% (missing: %i)' % (l.upper(), 100.*s[1]/(s[1]+s[2]), s[2]))

if __name__=='__main__':
	language_sync()
