#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Classes representing datasets in the DocumentModel."""
from misura.canon.logger import Log as logging
from veusz import document
from compiler.ast import flatten
import collections

sep = '/'
# Statuses
dstats = collections.namedtuple(
    'DocumentModelEntryStatus', ('available loaded'))(0, 1)


def iterpath(name, parent=False, splt=sep):
    v = name.split(splt)
    # Split the prefix, if found
    if ':' in v[0]:
        g = v[0].split(':')
        v = g + v[1:]

    # Recursively build the path
    isLeaf = False
    for i, sub in enumerate(v):
        if not parent and i == 1:
            parent = v[0]
        elif parent:
            parent = v[0] + ':' + splt.join(v[1:i])
        if i == len(v) - 1:
            isLeaf = True
        yield sub, parent, isLeaf


def find_pos(dslist, p=0):
    for d in dslist:
        if hasattr(d, 'm_pos'):
            p = max(p, d.m_pos)
        else:
            d.m_pos = p + 1
            logging.debug('%s %s %s', 'Assign pos', d.path, p + 1)
        p += 1
    for d in dslist:
        p = find_pos(d.children.keys(), p)
    return p


class AllDocDataAccessor(object):

    """Simulates a document with access to all data, comprising loadable datasets not in the document."""

    def __init__(self, doc):
        self.doc = doc

    @property
    def data(self):
        return self.doc.data

    @property
    def available_data(self):
        return self.doc.available_data

    def has_key(self, k, ret=False):
        if self.data.has_key(k):
            if ret:
                return self.data[k]
            return True
        if self.available_data.has_key(k):
            if ret:
                return self.available_data[k]
            return True
        return False

    def get(self, k, *a):
        val = self.has_key(k)
        if not val:
            if len(a) == 1:
                return a[0]
            raise KeyError("Key not found: {}".format(k))
        val = self.has_key(k, ret=True)
        return val

    def __getitem__(self, k):
        return self.get(k)

    def items(self):
        return [(k,self.get(k)) for k in self.keys()]

    def keys(self):
        k = self.data.keys() + self.available_data.keys()
        return sorted(k)

    def iteritems(self):
        for item in self.data.iteritems():
            yield item
        for item in self.available_data.iteritems():
            yield item


class NodeEntry(object):

    """Generic node representation for the document model"""
    _status = 1
    """Accessibility status"""
    statuses = {v: [] for v in range(-1, 4)}
    """Children accessibility status"""
    idx = -1
    name = 'root'
    """Node base name"""
    _path = False  # auto calc
    """Node full path or dataset key in doc.data"""
    _model_path =False
    parent = False
    """Parent node"""
    parents = []
    """Multiple parents"""
    splt = sep
    """Hierarchy splitter symbol"""
    _linked = False
    """Linked file for first-level nodes"""

    def __init__(self, doc=False, name='', parent=False, path=False, model_path=False, splt=sep):
        self.splt = splt
        self.doc = doc
        self.alldoc = AllDocDataAccessor(doc)
        self._name = name
        self._children = collections.OrderedDict()
        self._path = path
        self._model_path = model_path
        if parent is not False:
            parent.append(self)
        if doc is not False:
            if not hasattr(doc, 'ent'):
                doc.ent = {}
            doc.ent[id(self)] = self

    def name(self):
        return self._name

    def copy(self):
        c = self.__class__()
        c.doc = self.doc
        c._name = self._name
        c._children = self._children.copy()
        c._path = self.path
        c.parent = self.parent
        c._linked = self.linked
        c.splt = self.splt
        return c

    @property
    def path(self):
        """Node full path/dataset name"""
        if self._path:
            return self._path
        # Root and file entries
        if not self.parent:
            self._path = self._name
            logging.debug('%s %s', 'Root entry', self._name)
        # File entry
        elif not self.parent.parent:
            self._path = self._name
            logging.debug('%s %s', 'File entry', self._name)
        # First level entries (t, groups)
        elif not self.parent.parent.parent:
            self._path = self.parent.path + ':' + self._name
            logging.debug('%s %s', 'First level', self._path)
        # Normal entries
        else:
            self._path = self.splt.join([self.parent.path, self._name])
        return self._path

    @property
    def model_path(self):
        if not self._model_path:
            return self.path
        return self._model_path

    @path.setter
    def path(self, nval):
        self._path = nval

    @property
    def ds(self):
        return False

    @property
    def unit(self):
        if not self.ds:
            return False

        return getattr(self.ds, 'unit', False)

    @property
    def data(self):
        if not self.ds:
            return []
        return self.ds.data

    @property
    def mid(self):
        return id(self)

    @property
    def children(self):
        return self._children

    @property
    def mtype(self):
        return self.__class__.__name__

    @property
    def status(self):
        s = [c.status for c in self._children.itervalues()]
        if not len(s):
            return 0
        return max(s)

    def __len__(self):
        return len(self._children)

    def __nonzero__(self):
        return True

    def keys(self, status=1):
        """List keys based on status.
        `status` 1 = Visible; 0 = Hidden ; -1 = Available"""
        r = []
        for sub, item in self.children.iteritems():
            if item.status == status:
                r.append(sub)
        return r

    def __repr__(self):
        return '%s.%i.%i.(%s):%i' % (self._name, self.idx, len(self.children), self.parent, self.status)

    def append(self, item):
        self._children[item._name] = item
        item.parent = self

    def get(self, *a):
        return self.children.get(*a)

    def traverse(self, path):
        item = self
        for sub, parent, isLeaf in iterpath(path):
            item = item.get(sub, False)
            if isLeaf:
                break
            if item is False:
                return False
        return item

    @property
    def root(self):
        """Retrieve the root node of the tree"""
        item = self
        while item.parent is not False:
            item = item.parent
        return item

    @property
    def linked(self):
        """Recursive downward search for a valid linked file"""
        if self._linked:
            return self._linked
        for c in self.children.itervalues():
            if c.linked:
                return c.linked
        return False

    @linked.setter
    def linked(self, LF):
        self._linked = LF

    # ROOT ENTRY METHODS


    def insert(self, path, status=1):
        """Insert a pure node"""
        if self.doc.data.has_key(path) and isinstance(self.doc.data[path], document.datasets.Dataset1DPlugin):
            return False
        splt = self.splt
        if self.parent:
            assert self.path.startswith(path)
            # Cut away the common part
            path = path[len(self.path) + len(splt):]
        item = self
        linked = False
#		logging.debug('%s %s', 'going to insert', path)
        for sub, parent, leaf in iterpath(path):
            #			logging.debug('%s %s %s %s %s %s %s', 'iterating', sub, parent, leaf, repr(item.path), repr(item._name), id(parent))
            # Remember the first part of the path (0:summary, etc)
            if not parent:
                linked = sub
            if leaf or self.alldoc.get(sub, False):
                item = DatasetEntry(doc=self.doc, name=sub, parent=item)
                # Propagate the linked file to the first part of the path
                if item.ds and item.ds.linked:
                    linked_item = self.root.get(linked, None)
                    if linked_item.linked == False:
                        linked_item.linked = item.ds.linked
                break
            new = item.get(sub, False)
            if not new:
                # Existing dataset
                if parent and self.alldoc.get(parent+'/'+sub,False):
                    new = DatasetEntry(doc=self.doc, name=sub, parent=item)
                else:
                    new = NodeEntry(doc=self.doc, name=sub, parent=item)
            item = new

    def remove(self, child):
        k = child._name
#		logging.debug('%s %s %s', 'removing ', k, self.path)
        if not self._children.has_key(k):
            #			logging.debug('%s %s %s %s', 'Asking to remove non existent node', k, 'from', self.path)
            return False
        self._children.pop(k)
        return True

    @property
    def available(self):
        return self.recursive_status(dstats.available, cls=DatasetEntry)

    @property
    def hidden(self):
        return self.recursive_status(dstats.hidden, cls=DatasetEntry)

    @property
    def visible(self):
        return self.recursive_status(dstats.visible, cls=DatasetEntry)

    def recursive_status(self, st=1, depth=-1, cls=False):
        """Recursively list children with status in `st`. `st` can be an iterable (ideally a set()), an integer or a status name.
        `depth`<0: infinite recursion
        `depth`==0: only direct children
        `cls` restrict results pertaining to this node class
        """
        r = []
        # Get the status by name
        if isinstance(st, str):
            st = getattr(dstats, st)
        # Build an iterable
        if isinstance(st, int):
            st = set([st])
        m = min(st)
        for child in self.children.itervalues():
            if isinstance(child, DatasetEntry):
                if child.status not in st:
                    continue
            if child.status >= m:
                if (not cls) or isinstance(child, cls):
                    r.append(child)
                else:
                    logging.debug(
                        '%s %s %s %s', 'rec skip', child, child.status, st)
            if depth > 0 or depth < 0:  # depth=0 will block!
                r += child.recursive_status(st, depth=depth - 1)
        return r

    def set_doc(self, doc, default_status=0):
        """Build a Hierarchy out of `doc`
        `status`: default status"""
        old = self.copy()
        self._children = collections.OrderedDict()
        self.linked = False
        self.parent = False
        doc.ent = {}
        self.doc = doc
        self.alldoc = AllDocDataAccessor(doc)
        self.names = {}
        for dn, d in self.alldoc.items():
            dn1 = dn
            if hasattr(d, 'm_var'):
                dn1 = d.m_var
            elif dn.startswith('summary' + self.splt):
                dn1 = dn[7 + len(self.splt):]
            self.names[dn] = dn1
            status = default_status
            if len(d) == 0 and default_status >= 0:
                status = 0  # put on available
            else:
                status = default_status
            oldentry = old.traverse(dn)
            if oldentry:
                oldst = oldentry.status
                # if it was and still is loaded, keep the old status
                if status >= 0 and oldst >= 0:
                    status = oldst

            self.insert(dn, status)




class DatasetEntry(NodeEntry):

    """A wrapper object to represent a dataset by name and document,
    without actually keeping any reference to it."""
    _parents = []

    @property
    def ds(self):
        """Retrieve the original dataset from the document,
        not keeping any reference to it"""
        return self.alldoc.get(self.path, False)

    @property
    def status(self):
        ds = self.alldoc.get(self.path, False)
        if ds is False:
            self.parent.remove(self)
            return 0
        return int(len(ds) > 0)

    @property
    def children(self):
        """Scan the document for other datasets depending on itself."""
        for name, ds in self.alldoc.iteritems():
            if name == self.path:
                continue
            if not isinstance(ds, document.datasets.Dataset1DPlugin):
                continue
            involved = flatten(ds.pluginmanager.fields.values())
            if self.path in involved:
                sub = name.replace('/','-').replace(':','_')
                model_path = self.model_path+'/'+sub
                entry = self._children.get(sub, False)
                if entry is False:
                    entry = DatasetEntry(doc=self.doc, name=sub, path=name, model_path=model_path, parent=self)
        return self._children

    @property
    def parents(self):
        """Scan the document for all possible parents of this dataset"""
        if len(self._parents) > 0:
            return self._parents
        if not isinstance(self.ds, document.datasets.Dataset1DPlugin):
            return []
        involved = flatten(self.ds.pluginmanager.fields.values())
        self._parents = []
        for name in involved:
            if name == self._name:
                continue
            if not self.alldoc.has_key(name):
                continue
            self._parents.append(name)
        return self._parents

    @property
    def m_smp(self):
        return getattr(self.ds, 'm_smp', False)

    @property
    def vars(self):
        vars = []
        for p in self.parents:
            ds = self.alldoc[p]
            if p==self.path:
                continue
            if hasattr(ds, 'm_var'):
                vars.append(ds.m_var)
            else:
                vars.append(p)
        return vars

    @property
    def m_var(self):
        ds = self.ds
        if getattr(ds, 'm_smp', False) is not False:
            return ds.m_var

        pm = ds.pluginmanager

        if len(self.parents) == 1 or pm.plugin.name == 'SmoothData':
            return self.parent.m_var
        if not isinstance(self.ds, document.datasets.Dataset1DPlugin):
            return getattr(ds, 'm_var', self.path)

        vars = ','.join(self.vars)
        if pm.plugin.name == 'Coefficient':
            v = 'Coeff(%i,%s\degC) ' % (pm.fields['start'],vars)
        elif pm.plugin.name == 'Derive':
            v = 'Der(%i\deg,%s)' % (pm.fields['order'],vars)
        else:
            v = getattr(ds, 'm_var', vars)
        return v

    @property
    def legend(self):
        if getattr(self.ds, 'm_smp', False) is not False:
            return self.ds.m_var
        if not isinstance(self.ds, document.datasets.Dataset1DPlugin):
            return getattr(self.ds, 'm_var', self.path)
        pm = self.ds.pluginmanager
        if pm.plugin.name == 'SmoothData':
            name = getattr(self.parent, 'm_var', self.parent.path)
            return 'Smooth(%s,%ipts)' % (name, pm.fields['window'])
        else:
            return '%s(%s)' % (pm.plugin.name, ','.join(self.vars))

    @property
    def m_name(self):
        return getattr(self.ds, 'm_name', self._name)

    @property
    def m_col(self):
        return self.ds.m_col

    @property
    def m_keep(self):
        return getattr(self.ds, 'm_keep', False)

    @m_keep.setter
    def m_keep(self, b):
        self.ds.m_keep = b

    @property
    def m_pos(self):
        if hasattr(self.ds, 'm_pos'):
            return self.ds.m_pos
        if self.linked is None:
            return -1
        p = find_pos(self.linked.children.keys())
        return p

    @property
    def m_percent(self):
        return getattr(self.ds, 'm_percent', False)

    @m_percent.setter
    def m_percent(self, b):
        self.ds.m_percent = b

    @property
    def linked(self):
        """Recursive upward search for a linked file"""
        entry = self
        while True:
            ds = entry.ds
            if ds is False:
                entry = entry.parent
                if entry is False:
                    break
                continue
            if ds.linked is not None:
                return ds.linked
            if entry.parent is False:
                return None
            entry = entry.parent
