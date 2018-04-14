import os
import urllib2
import tempfile
from traceback import format_exc
try:
    import configparser
except:
    import ConfigParser as configparser
    
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from . import widgets
from .clientconf import confdb
from .network import TransferThread
from .parameters import pathClient
from .live import registry

class ServerUpdater(object):
    def __init__(self, server, parent):
        self.server = server
        self.parent = parent
        self.pkg = False
        self.outfile = False
        
    def __call__(self, *a):
        self.pkg = widgets.aFileList(self.server, self.server.support, 
                          self.server.support.gete('packages'), parent=self.parent)
        self.pkg.hide()
        if self.pkg.send(filename=self.outfile): 
            self.pkg.transfer.dlFinished.connect(self.apply_update_server)
        
    def apply_update_server(self, *a):
        if self.pkg:
            self.outfile = self.pkg.transfer.outfile
        self.server.support['packages'] = os.path.basename(self.outfile)
        logging.info('Apply server update', self.server.support['packages'], self.outfile)
        
        btn = widgets.aButton(self.server, self.server.support,
                                self.server.support.gete('applyExe'), parent=self.parent)
        btn.hide()
        btn.get()
        btn.show_msg()
        self.server.restart()
        logging.debug('Closing the client while server restarts.')
        self.parent.quit()
        
class ClientUpdater(object):
    def __init__(self, execfile, parent):
        self.execfile = execfile
        self.parent = parent
    
    def __call__(self):
        from PyQt4 import QtCore
        QtCore.QProcess.startDetached(self.execfile)
        from .iutils import app
        app.quit()
        
        
    

fi = lambda s: int(s.ljust(20, '0'))

def get_packages(*filenames):
    url = confdb['updateUrl']
    user = confdb['updateUser']
    password = confdb['updatePassword']
    if user:
        protocol, url = url.split('://')
        url = '{}://{}:{}@{}'.format(protocol, user, password, url)
    while url.endswith('/'):
        url = url[:-1]
    if 'packages.ini' not in filenames:
        filenames=['packages.ini']+list(filenames)
    logging.debug('Update site:', url, filenames)
    conf = configparser.SafeConfigParser()
    conf.optionxform = str
    for f in filenames:
        file_url = url+'/'+f
        logging.debug('Getting:', file_url)
        try:
            res = urllib2.urlopen(file_url)
            conf.readfp(res)
        except:
            if f=='packages.ini':
                raise 
            logging.error(format_exc())
    return conf

def get_best_client_version(conf, serials):
    """Get best client version compatible with the oldest server 
    appearing in recent cronology"""
    client = conf.get('latest', 'client')
    iclient = fi(client)
    server = conf.get('latest', 'server')
    iserver = fi(server)
    
    # Search latest version available for oldest serial getting an update
    sections = conf.sections()
    oldest_serial = False
    for serial in serials:
        if serial  not in sections:
            logging.debug('Serial not found:', serial)
            continue
        new = conf.get(serial, 'server')
        inew = fi(new)
        if inew<iserver:
            server=new
            iserver = inew
            client=conf.get(serial, 'client')
            iclient = fi(client)
            oldest_serial=serial
    logging.debug('Oldest serial:', oldest_serial)
    logging.debug('Found client:', client, iclient)
    logging.debug('Found server:', server, iserver)
    return client, iclient
    
def get_version_date(versionString):
    current = -1
    for line in versionString.splitlines():
        if line.startswith('date'):
            line=line.split('=')[-1].replace(' ','').replace(':','').replace('-','')
            current = fi(line)
    return current
    
def check_server_updates(remote, parent=None):
    current = -1
    latest = -1
    # Take current last version
    if 'versionString' in remote.support:
        current = get_version_date(remote.support['versionString'])
    
    serial = remote['eq_sn']
    
    conf = get_packages(serial+'.ini')
    if conf.has_option(serial, 'server'):
        latest = conf.get(serial, 'server')
        v = fi(latest)
        if v<=current:
            logging.info('No update was found', current, latest)
            return False
    else:
        # Take latest version
        latest = conf.get('latest', 'server')
    
            
    tempdir = tempfile.mkdtemp('misura_updater')    
    server_url = conf.get('url', latest)
    server_out = os.path.join(tempdir, 'misura_pkg_{}.tar'.format(latest))
    logging.debug('Downloading server package', server_url)
    
    updater = ServerUpdater(remote, parent)
    updater.outfile=server_out
    tt = TransferThread(server_url, server_out)
    tt.dlFinished.connect(updater)
    tt.updater = updater
    tt.set_tasks(registry.tasks)
    tt.start()
    return tt
    
def update_from_source():
    from misura.canon import determine_path
    from commands import getstatusoutput as go
    paths = []
    paths.append(os.path.dirname(determine_path(__file__)))
    from misura.canon import __file__ as canonfile
    paths.append(os.path.dirname(determine_path(canonfile)))
    from veusz import __file__ as veuszfile
    paths.append(os.path.dirname(determine_path(veuszfile)))
    for path in paths:
        s,r=go('git -C "{}" status'.format(path))
        logging.debug(s,r)            
        logging.debug('Updating',path)
        s,r=go('git -C "{}" pull --rebase'.format(path))
        logging.debug(s,r)
    return True 
    
def check_client_updates(parent):
    if os.name!='nt':
        return update_from_source()
    serials = []
    for recent in confdb['recent_server'][1:]:
        serials.append(recent[4]+'.ini') 
    conf = get_packages(*serials)
    client, iclient = get_best_client_version(conf, serials)
    
    current = os.path.join(pathClient, 'VERSION')
    current = open(current, 'r').read()
    current = get_version_date(current)
    
    if current>iclient:
        logging.info('No update was found', current, client)
        return False
    tempdir = tempfile.mkdtemp('misura_updater')    
    
    client_out = os.path.join(tempdir, 'misura_client_{}.exe'.format(client))
    url = conf.get('url', str(client))
    updater = ClientUpdater(client_out, parent)
    tt = TransferThread(url, client_out)
    tt.dlFinished.connect(updater)
    tt.updater = updater
    tt.set_tasks(registry.tasks)
    tt.start()
    return tt
    