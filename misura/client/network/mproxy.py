# -*- coding: utf-8 -*-
#from transport import MisuraTransport
from misura.canon.logger import Log as logging
import xmlrpclib
from xmlrpclib import ServerProxy, ProtocolError
from time import time
import urllib
import httplib
from traceback import format_exc
import threading
from misura.canon.csutil import lockme

# Disable ssl cert verification (Misura certs are self-signed)
import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

sep = '/'


def urlauth(url):
    """Decode and strip away the auth part of an url.
    Returns user, password and clean url"""
    url = urllib.unquote(url)
    i = url.find('://') + 3
    e = url.find('@', i) + 1
    auth = url[i:e][:-1]
    user, passwd = auth.split(':')
    url_start = url[:i]
    url_end = url[e:].split('/')
    # Take the address
    url_start += url_end.pop(0)
    if not url_start.endswith('/'):
        url_start += '/'
    # Quote the item location part of the url
    url_end = '/'.join(url_end)
    url = url_start + urllib.quote(url_end) 
    
    return user, passwd, url


def remote_dbdir(server):
    """Calc remote database directory path"""
    # Filter away the misura.sqlite filename
    p = server.storage.get_dbpath().split('/')[:-1]
    r = '/'.join(p)
    logging.debug('%s %s', 'remote_dbdir', r)
    return r


def dataurl(server, uid):
    """Calc HTTPS/data url for test file `uid` on `server`"""
    t = getattr(server.storage.test, uid)
    if not t:
        return False
    p = t.get_path()
    # Remove remote db path from file path
    dbdir = remote_dbdir(server)
    if p.startswith(dbdir):
        p = p[len(dbdir):]
    if not p.startswith('/'):
        p = '/' + p
    # Prepend remote HTTPS/data path
    url = server.data_addr + urllib.quote(p.encode('utf8'))
    logging.debug('dataurl %s %s --> %s',server.data_addr,p,url)
    return url, p


class _Method:

    """Override xmlrpclib._Method in order to introduce our own separator"""

    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _Method(self.__send, "%s%s%s" % (self.__name, sep, name))

    def __call__(self, *args):
        return self.__send(self.__name, args)

xmlrpclib._Method = _Method


class AutoDict(object):

    """A special dictionary-like class with automatic recursive creation of missing keys."""

    def __init__(self, autoclass=['self']):
        self.autoclass = autoclass
        self.cache = {}

    def __getitem__(self, k):
        if not self.cache.has_key(k):
            cls = self.autoclass[0]
            if cls == 'self':
                cls = AutoDict
            kw = {}
            if cls == AutoDict and len(self.autoclass) > 1:
                kw['autoclass'] = self.autoclass[1:]
            self.cache[k] = cls(**kw)
        return self.cache[k]

    def __setitem__(self, k, v):
        q = self[k]
        self.cache[k] = v

    def has_key(self, k):
        return self.cache.has_key(k)

    def get(self, k, *arg):
        if self.cache.has_key(k):
            return self.cache[k]
        elif len(arg) == 1:
            return arg[0]
        return self[k]


def reconnect(func):
    """Decorator function for automatic reconnection in case of failure"""

    def reconnect_wrapper(self, *a, **k):
        try:
            r = func(self, *a, **k)
        except (xmlrpclib.ProtocolError, httplib.CannotSendRequest, httplib.BadStatusLine, httplib.ResponseNotReady):
            logging.debug('RECONNNECTING', func)
            self.connect()
            return func(self, *a, **k)
        except:
            logging.debug('UNHANDLED EXCEPTION', func)
            logging.debug(format_exc())
            if self._reg:
                self._reg.connection_error()
            raise
        return r
    return reconnect_wrapper


class MisuraProxy(object):

    """Classe wrapper per ServerProxy. Introduce le funzioni __getitem__ e __setitem__."""
    _Method__name = 'MAINSERVER'
    _parent = False
    _error = ''
    _rmodel = False
    """Cached remote recursive model dictionary"""
    _recursiveModel = False
    """Cached recursive item model"""
    remObj = False
    """Remote ServerProxy object"""
    addr = False
    """Remote server address"""
    user = False
    """User name"""
    password = False
    """User password"""
    _readLevel = 0
    """Read level"""
    _writeLevel = 0
    """Write level"""
    _remoteDict = {}
    """Remote methods and object paths"""
    _refresh_interval = 0
    """Wait time between getting again the same option"""
    _refresh_last = AutoDict(autoclass=['self',  int])
    """Last refresh times"""
    _desc = {}
    _cache = AutoDict()
    """Local representation of remote description"""
    _dtime = time()
    """Client-server time delta"""
    _ctime = time()
    """Time of last remote call - use for logging"""
    _smartnaming = False
    _reg = False
    """Triggers remote get/set requests when accessing to un-protected local attributes"""
    _protect = set(['remObj', 'conn_addr', 'data_addr', 'to_root', 'toPath', 'root', 'connect', 'paste', 'copy', 'describe',
                    'info', 'lastlog', 'get', 'from_column', 'parent', 'child', 'call', 'devices', 'roledev'])
    """Local names which must not be accessed remotely"""
    sep = '/'

    def __init__(self, addr='', user='', password='', proxy=False, reg=False):
        self._lock = threading.Lock()
        # Copy existing object
        if proxy:
            self.paste(proxy)
        # Create new connection
        else:
            self._reg = reg
            self.addr = addr
            self.user = user
            self.password = password
            self.connect()
            self._protect.update(dir(self))

    @property
    def conn_addr(self):
        auth = 'https://{}:{}@'.format(self.user, self.password)
        return self.addr.replace('https://', auth)

    @property
    def data_addr(self):
        return self.conn_addr.replace('/RPC', '/data')

    def __str__(self):
        return '%r %s@%s /%s (%s)' % (self, self.user, self.addr, self._Method__name, self.remObj._Method__name)

    def _to_root(self):
        """Create new HTTP connection"""
        oldname = self._Method__name
        self.remObj = ServerProxy(
            self.conn_addr, allow_none=True, verbose=False)
        self.remObj.allow_none = True
        self.remObj._ServerProxy__allow_none = True
        self.remObj._Method__name = 'MAINSERVER'
        self._Method__name = 'MAINSERVER'
        a = self.remObj.echo('').split('=')
        self._readLevel, self._writeLevel = int(
            a[1].split(',')[0]), int(a[2].split(',')[0])
        # Compile a list of both remote callable methods and remote walkable
        # objects
        d = {'MAINSERVER': []}
        # FIXME: this will cause memory leak on labor2...
        if self._smartnaming:
            for entry in self.remObj.system.listMethods():
                if entry.count(self.sep) == 0:
                    d['MAINSERVER'].append(entry)
                    continue
                entry = entry.split(self.sep)
                part = entry[0]
                if part not in d['MAINSERVER']:
                    d['MAINSERVER'].append(part)
                if len(entry) == 1:
                    continue
                for e in entry[1:]:
                    if not d.has_key(part):
                        d[part] = []
                    if e not in d[part]:
                        d[part].append(e)
                    part += self.sep + e
        self._remoteDict = d
        self._dtime = self.remObj.time() - time()
        return oldname

    @lockme
    def to_root(self):
        """Locked call for _to_root."""
        return self._to_root()

    def _toMethodName(self, name):
        """Changes current method name in-place"""
        if name in ['MAINSERVER', '']:
            return
        if isinstance(name, str):
            lst = name.split(self.sep)
        else:
            lst = name
        for p in lst:
            if p == 'MAINSERVER':
                continue
            self.remObj = getattr(self.remObj, p)
        self._Method__name = self.remObj._Method__name

    @lockme
    def connect(self):
        oldname = self._to_root()
        # Restore object path's
        self._toMethodName(oldname)

    @property
    def root(self):
        """Return the root object"""
        r = self.copy()
        r.to_root()
        return r

    @property
    def _remoteNames(self):
        return self._remoteDict.get(self._Method__name, [])

    @lockme
    def paste(self, obj):
        """Paste foreign MisuraProxy settings into current instance"""
        oldsmart = obj._smartnaming  # remember smartnaming status
        # Stop smartnaming in order to make attribute definition quicker
        self._smartnaming = False
        obj._smartnaming = False
        self.remObj = obj.remObj
        self.user = obj.user
        self.password = obj.password
        self.addr = obj.addr
        self._reg = obj._reg
        self._Method__name = obj.remObj._Method__name
        self._parent = obj.parent()
        self._remoteDict = obj._remoteDict
        self._refresh_interval = obj._refresh_interval
        self._cache = obj._cache
        self._desc = obj._desc
        self._refresh_last = obj._refresh_last
        self._error = obj._error
        self._dtime = obj._dtime
        self._protect = obj._protect
        self._smartnaming = obj._smartnaming
        self._readLevel = obj._readLevel
        self._writeLevel = obj._writeLevel
        # Restore smartnaming, if it was enabled
        if oldsmart:
            self._smartnaming = True
            obj._smartnaming = True

    def copy(self, reconnect=False):
        """Return a copy of this object with a new HTTP connection."""
        if not reconnect:
            reconnect = self
        obj = self.__class__(
            self.addr, self.user, self.password, proxy=reconnect)
        obj.paste(self)
        return obj

    def __nonzero__(self):
        return 1

    @lockme
    def describe(self, *args):
        if self._refresh_interval <= 0:
            return self.remObj.describe(*args)
        t = time()
        key = '::describe::'
        if t - self._refresh_last[self._Method__name].get(key, 0) > self._refresh_interval or \
                (self._desc.get(self._Method__name, False) is False):
            # Need to refresh
            self._refresh_last[self._Method__name][key] = t
            self._desc[self._Method__name] = self.remObj.describe(*args)
            self._ctime = time()
        return self._desc[self._Method__name]

    @lockme
    def info(self, key):
        """Pretty print information about `key`"""
        logging.debug('%s %s', 'Option:', key)
        e = self.remObj.gete(key)
        for k, v in e.iteritems():
            logging.debug('%s %s %s %s', '\t', k, ':', v)

    @lockme
    def lastlog(self):
        """Retrieve log messages near the last remote procedure call"""
        t = self._ctime + self._dtime
        r = self.remObj.get_log(t - 1, t + 1)
        return r

    @reconnect
    @lockme
    def get(self, key):
        """Cached get function"""
        t = time()
        if t - self._refresh_last[self._Method__name][key] > self._refresh_interval:
            self._refresh_last[self._Method__name][key] = t
            r = self.remObj.get(key)
            self._ctime = time()
            if not self._cache.has_key(key):
                self._cache[key] = r
            else:
                self._cache[key] = r
        else:
            pass
        return self._cache[key]

    def __getitem__(self, key):
        return self.get(key)

    @reconnect
    @lockme
    def __setitem__(self, key, val):
        self._refresh_last[self._Method__name][key] = 0
        self._ctime = time()
        if isinstance(val, self.__class__):
            val = val.get('fullpath')
        return self.remObj.set(key, val)

    def __setattr__(self, key, val):
        if key.startswith('_') or (not self._smartnaming) or (key in self._protect):
            return object.__setattr__(self, key, val)
        if isinstance(val, self.__class__):
            val = val.get('fullpath')
        if self.remObj is not False:
            return self.__setitem__(key, val)
        elif key in self._remoteNames:
            logging.debug(
                '%s %s', 'Overwrite of a remote object name is forbidden!', key)
            return False
        else:
            return object.__setattr__(self, key, val)

    @lockme
    def _has_key(self, path):
        r = self.remObj.has_key(path)
        return r

    def __getattr__(self, path):
        """Override standard ServerProxy in order to provide useful shortcuts."""
        # Protect local names
        if (path in self._protect) or path.startswith('_'):
            return object.__getattribute__(self, path)
        # Detect option retrieval request
        if self._smartnaming:
            if self._Method__name == 'MAINSERVER':
                cpath = path
            else:
                cpath = self._Method__name + self.sep + path
            if (cpath not in self._remoteNames):
                if self._has_key(path):
                    return self.get(path)
        return self.child(path)

    @lockme
    def toPath(self, lst):
        """Returns a copy of the object at the path expressed in list/string lst"""
        if type(lst) == type(''):
            if lst.endswith(self.sep):
                lst = lst[:-1]
            if lst.startswith(self.sep):
                lst = lst[1:]
            lst = lst.split(self.sep)
            if lst[0] == 'server':
                lst.pop(0)
        obj = self.copy()
        obj._toMethodName(self.sep.join(lst))
        return obj

    def from_column(self, col0):
        """Returns the object able to return the column `col` and the column option name"""
        sp = self.sep
        # Remove ':' prefix
        col = col0.split(':')
        col = col[0] if len(col) == 1 else col[1]
        if col.startswith(sp + 'summary' + sp):
            col = col[9:]
        v = col.split(sp)
        if v[0] == '':
            v.pop(0)
        name = v.pop(-1)
        logging.debug('%s %s %s %s', 'from_column', col0, v, name)
        obj = self.toPath(v)
        return obj, name

    def parent(self):
        """Get the parent object handling this one"""
        if not self._parent:
            return False
        obj = self._parent.copy()
        return obj

    def child(self, name):
        obj = self.toPath([name])
        obj._parent = self
        return obj

    @reconnect
    @lockme
    def __call__(self, *args, **kwargs):
        self._ctime = time()
        return self.remObj.__call__(*args, **kwargs)

    @reconnect
    @lockme
    def call(self, path, *args, **kwargs):
        self._ctime = time()
        f = getattr(self.remObj, path)
        return f(*args, **kwargs)

    @property
    def devices(self):
        """List available devices retrieved via list() as MisuraProxy objects"""
        r = []
        for name, path in self.list():
            r.append(self.child(path))
        return r

    def role2dev(self, opt):
        """Return the device object associated with role option `opt`"""
        p = self[opt]
        if not p:
            return False
        p = p[0]
        if p in ('None', None):
            return False
        obj = self.root.toPath(p)
        if not obj:
            return False
        return obj
