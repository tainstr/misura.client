#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Aggiornamento del progetto di traduzione in base al file runtime generato con l'opzione parameters.linguist=True"""

langs = ['it', 'de', 'fr', 'es', 'en']

header = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.0" language="%s">
"""

context_h = """
<context>
    <name>%s</name>
"""

context_f = "</context>"
footer = "</TS>"

entry = """
    <message>
        <source>%s</source>
	<translation>%s</translation>
	<translatorcomment>%s</translatorcomment>
    </message>
"""
u_entry = """
    <message>
        <source>%s</source>
	<translation type="unfinished">%s</translation>
	<translatorcomment>%s</translatorcomment>
    </message>
"""

from misura.canon.logger import Log as logging
from misura.canon.option import Option
from time import time
from sys import argv
import os
import pkgutil
from xml.sax.saxutils import escape, unescape
pathClient = os.path.dirname(__file__)
pathLang = os.path.join(pathClient, 'i18n')


def mescape(s):
    s = escape(s)
# 	s=s.replace('"','&quot;')
    return s


def tag(g, line, o):
    if "<%s>" % g in line:
        return line.split(g + '>')[1][:-2]
    return o


def stats(ctx):
    ct = 0
    done = 0
    undone = 0
    for c, v in ctx.iteritems():
        ct += 1
        for s, m in v.iteritems():
            if m[0] == '':
                undone += 1
            else:
                done += 1
    return [ct, done, undone]


def update(lang, ctx, base='misura'):
    """Add already translated values to the context `ctx`."""
    c = False
    s = False
    t = False
    m = ''
    ctx = ctx.copy()
    filename = os.path.join(pathLang, base + '_' + lang + '.ts')
    # No previous translations: nothing to update!
    if not os.path.exists(filename):
        logging.debug(lang.upper(), '\tOriginal translation not found:', filename)
        return ctx
    # Update from found filename
    for line in open(filename, 'r'):
        if '<context>' in line:
            c = False
            s = False
            t = False
            m = ''
        if '<message>' in line:
            s = False
            t = False
            m = ''
        c = tag('name', line, c)
        s = tag('source', line, s)
        t = tag('translation', line, t)
        m = tag('translatorcomment', line, m)
        if '</message>' in line and c and s:
            if not ctx.has_key(c):
                ctx[c] = {}
            s = mescape(s)
            if not t:
                t = ''
            t = mescape(t)
# 			print '\tfound translation:',c,s,t
            ctx[c][s] = (t, m)
    return ctx


def write_ts(lang, ctx):
    """Output context to .ts formatted file"""
    filename = os.path.join(pathLang, 'misura_' + lang + '.ts')
    out = open(filename, 'w')
    out.write(header % lang)
    for c, ent in ctx.iteritems():
        out.write(context_h % c)
        logging.debug('\tContext:', c)
        for s, e in ent.iteritems():
            if e[0] == '':
                out.write(u_entry % (s, e[0], e[1]))
            else:
                out.write(entry % (s, e[0], e[1]))
        out.write(context_f)
    out.write(footer)

# this is the package we are inspecting -- for example 'email' from stdlib
import inspect
autodoc_dir = "/opt/misura4/misura/client/doc/options"
if not os.path.exists(autodoc_dir):
    os.makedirs(autodoc_dir)

def as_rst(opt):
    """Format option entry dictionary `opt` as restructured text for documentation.
    """
    len_name = len(opt['name']) + 2
    text = ''
    h0 = '=' * len_name + '\n'
    text += h0 + opt['name'] + '\n' + h0
    text += 'The following table lists default values for this Option.\n\n'
    # Build a simple table out of properties
    table = ''
    space = '  '
    # Find max length of fields for table headers
    len_key = 8
    len_val = 5
    for key, val in opt.iteritems():
        if len(key) > len_key:
            len_key = len(key)
        val = repr(val)
        if len(val) > len_val:
            len_val = len(val)
    len_key += 2
    len_val += 4  # includes also ``` engraving
    # table content
    keys = opt.keys()
    keys.sort()
    for key in keys:
        if key == 'name': continue
        val = '`' + repr(opt[key]) + '`'
        table += key.ljust(len_key) + space + val.ljust(len_val) + '\n'

    # Build header
    header0 = '=' * len_key + space + '=' * len_key + '\n'
    header = 'Property'.ljust(len_key) + space + 'Value'.ljust(len_val) + '\n'
    # Compose table
    table = header0 + header + header0 + table + header0
    text += table + '\n\n'
    return text

class_header = '''

Configuration options for  `{}` objects
===============================================

'''

def generate_rst(conf_def, parent_def=[], class_name='', rst=''):
    """Generate rst paragraphs out of conf_def list of options"""
    add_rst = ''
    for el in conf_def:
        # Check valid Option
        if not isinstance(el, dict):
            continue
        if not el.has_key('handle'):
            continue
        # Skip if identical in parent object
        if el in parent_def:
            continue
        # If option label is already present in rst
        anchor = '.. _option_{}_{}:'.format(class_name, el['handle'])
        if  anchor in rst or anchor in add_rst:
            print 'ANCHOR already found', anchor
            continue
        opt = Option(**el)
        opt.validate()
        add_rst += anchor + '\n\n' + as_rst(opt)

    if len(add_rst)>0:
        add_rst = class_header.format(class_name) + add_rst
    return rst + add_rst

start_tag = '.. misura_autodoc_start\n\n'
end_tag = '.. misura_autodoc_end\n\n'

def update_rst(conf_def, rst='', parent_conf=[], class_name=''):
    """Update text in old `rst` from class `obj`"""
    header = ''
    footer = ''
    rst0 = rst
    # Slice text if already edited
    i = rst.find(start_tag)
    if i >= 0:
        header = rst[:i]
        rst = rst[i + len(start_tag):]
    j = rst.find(end_tag)
    if j >= i:
        footer = rst[j + len(end_tag):]
        rst = rst[:j]
    n = len(rst)
    rst = generate_rst(conf_def, parent_conf, class_name, rst)
    if len(rst) == n:
        return rst0
    if not start_tag in header:
        header += start_tag
    if not end_tag in footer:
        footer = end_tag + footer
    # Rebuild full text
    rst = header + rst + footer
    return rst

def autodoc(obj):
    """Autodocument all Options for class `obj`"""
    mro = list(inspect.getmro(obj))
    mro.reverse()
    # Keep parent object in order to write only missing options
    if len(mro) > 1:
        parent_class = mro[-2]
    else:
        parent_class = False
    # Keep only names
    mro = [cls.__name__ for cls in mro]
    # Skip xmlrpc stuff
    if not 'ConfigurationInterface' in mro:
        print 'Object does not inherit from base ConfigurationInterface class. Skipping autodoc.', mro
        return False
    i = mro.index('ConfigurationInterface')
    mro = mro[i:]

    fname = '.'.join(mro) + '.rst'
    path_rst = os.path.join(autodoc_dir, fname)


    if not os.path.exists(path_rst):
        logging.debug('Creating index.rst', path_rst)
        open(path_rst, 'w').close()

    rst = open(path_rst, 'r').read()
    parent_conf = getattr(parent_class, 'conf_def', [])
    rst = update_rst(obj.conf_def, rst, parent_conf, obj.__name__)
    # Write on output file
    if len(rst)>0:
        open(path_rst, 'w').write(rst)
    return True


done = set([])

def collect_conf(module, translations):
    """Scan a module for all classes defining a conf_def iterable attribute."""
    names = dir(module)
    missing = 0
    for name in names:
        obj = getattr(module, name, False)
        if obj is False:
            continue
        if not hasattr(obj, 'conf_def'):
            continue
        conf_def = getattr(obj, 'conf_def', False)
        if not conf_def:
            continue
        # Skip modules defining a conf_def list at their root.
        if getattr(obj, '__bases__', False) is False:
            continue
        if obj in done: continue
        done.add(obj)
        logging.debug('Found conf_def', obj.__name__, conf_def)
        autodoc(obj)
        for el in conf_def:
            if not isinstance(el, dict):
                continue
            tr = el.get('name', False)
            if not tr:
                continue
            h = el.get('handle', False)
            if not h:
                missing += 1
                h = '!!!_missing_handle_{}'.format(missing)
            logging.debug(obj, h, tr)
            translations[h] = tr
            # Get translatable option names
            opt = el.get('options', False)
            if not opt:
                continue
            if not el.has_key('values'):
                continue
            for i, o in enumerate(opt):
                h1 = h + '_opt{}'.format(i)
                translations[h1] = o
    return translations, missing


def iterpackage(package):
    """Scan a package for all subpackages and all modules containing classes defining conf_def attribute.
    Accept an imported module as argument.
    Returns translations dictionary and missing count."""
    prefix = package.__name__ + "."
    translations = {}
    missing = 0
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
        if modname.split('.')[-1] in ('client', 'canon', 'libvideodev', 'utils'):
            logging.debug('skipping', modname)
            continue
        logging.debug("Found submodule %s (is a package: %s)" % (modname, ispkg))
        module = __import__(modname, fromlist="dummy")
        logging.debug("Imported", module)
        translations, ms = collect_conf(module, translations)
        missing += ms
        if ispkg:
            iterpackage(module)
    return translations, missing


def collect():
    """Collect translatable strings from static source code analysis.
    Returns all collected strings."""

    import misura
    from misura.canon.indexer import indexer

    translations, missing = iterpackage(misura)
    logging.debug('Stats', len(
        translations), len(set(translations)), missing)

    for column in indexer.columns_to_translate:
        translations["dbcol:" + column] = "dbcol:" + column

    out = open('static.txt', 'w')
    for h, tr in translations.iteritems():
        out.write('{}\t{}\n'.format(h, tr))
    out.close()



    return translations

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

        if len(obj.args) + len(obj.keywords) not in (1, 2, 3) or len(obj.args) < 1:
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
                    comment=comment))

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
            context = args.defaults[contextidx - 1].s
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
                        gcontext={'_': 'misura'},
                        gargs={'_': ('text', 'disambiguation', 'context')}):
    '''Update output in retn with strings in filename.'''

    if verbose:
        sys.stdout.write('Examining file %s\n' % repr(filename))
    with open(filename) as f:
        source = f.read()

    tree = ast.parse(source, filename)

    v = PythonMessageVisitor(filename, retn, verbose=verbose)
    v.fn2context = gcontext.copy()
    v.fnargs = gargs.copy()
    v.visit(tree)


def scan_client_source(path, out=False):
    retn = {}
    for root, dirs, files in os.walk(path):
        for fn in files:
            if not fn.endswith('.py'):
                continue
            fp = os.path.join(root, fn)
            logging.debug('Scanning', fp)
            python_find_strings(fp, retn)
    # Simplify output
    if not out:
        out = {}
    for ctx, msgs in retn.iteritems():
        if not out.has_key(ctx):
            out[ctx] = {}
        for msg in msgs:
            v = mescape(msg.string)
            out[ctx][v] = ('', '')
#         out[ctx] += [msg.string for msg in msgs]
    return out

######################
# END OF CLIENT CODE ANALYSIS
######################
from misura.client.parameters import pathClient


def language_sync():
    """Merge all translatable strings from runtime requests, code analysis, already translated code."""
    # Translation contexts
    contexts = {'Option': {}}

    # Collect from server code analysis
    trcode = collect()
    for v in trcode.values():
        v = mescape(v)
        contexts['Option'][v] = ('', '')

    # Collect from client code analysis
    contexts = scan_client_source(pathClient, out=contexts)

    statistics = {}
    for l in langs:
        logging.debug('LANGUAGE:', l)
        ctx = update(l, contexts.copy(), base='misura')
        ctx = update(l, ctx)
        write_ts(l, ctx)
        statistics[l] = stats(ctx)
        # cancello tutte le traduzioni, mantenendo però le chiavi
        contexts = {}
        for c, v in ctx.iteritems():
            if not contexts.has_key(c):
                contexts[c] = {}
            for k, e in v.iteritems():
                contexts[c][k] = ('', '')

    logging.debug('Completeness:')
    for l in langs:
        s = statistics[l]
        logging.debug('%s: %.2f %% (missing: %i)' %
                      (l.upper(), 100. * s[1] / (s[1] + s[2]), s[2]))

if __name__ == '__main__':
    language_sync()
