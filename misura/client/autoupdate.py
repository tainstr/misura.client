import os
import urllib2
import tempfile

try:
    import configparser
except:
    import ConfigParser as configparser
    
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from . import widgets
from .clientconf import confdb
from .network import TransferThread


class ServerUpdater(object):
    def __init__(self, server, parent=None):
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

fi = lambda s: int(s.ljust(20, '0'))

def get_packages():
    url = confdb['updateUrl']
    user = confdb['updateUser']
    password = confdb['updatePassword']
    if user:
        protocol, url = url.split('://')
        url = '{}://{}:{}@{}'.format(protocol, user, password, url)
    
    logging.debug('Packages:', url)
    res = urllib2.urlopen(url)
    conf = configparser.SafeConfigParser()
    conf.optionxform = str
    conf.readfp(res)
    return conf

def get_best_client_version(conf):
    """Get best client version compatible with the oldest server 
    appearing in recent cronology"""
    client = conf.get('latest', 'client')
    iclient = fi(client)
    server = conf.get('latest', 'server')
    iserver = fi(server)
    
    # Search latest version available for oldest serial getting an update
    sections = conf.sections()
    oldest_serial = False
    for recent in confdb['recent_server'][1:]:
        serial = recent[4] 
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
    return client, server, oldest_serial
    
    
def check_server_updates(remote, parent=None):
    current = -1
    latest = -1
    # Take current last version
    if 'versionString' in remote.support:
        for line in remote.support['versionString'].splitlines():
            if line.startswith('date'):
                line=line.split('=')[-1].replace(' ','').replace(':','').replace('-','')
                current = fi(line)
    
    serial = remote['eq_sn']
    
    conf = get_packages()
    if conf.has_option(serial, 'server'):
        latest = conf.get(serial, 'server')
        v = fi(latest)
        if v<=current:
            logging.info('No available update was found', current, latest)
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
    from .live import registry
    tt.set_tasks(registry.tasks)
    tt.start()
    return tt
    
def check_client_updates():
    conf = get_packages()
    
    client_url = conf.get('url', str(client))
    if client_url==confdb['updateLast']:
        logging.debug('Last update address matches latest package available')
        return False
    #TODO: client update
    