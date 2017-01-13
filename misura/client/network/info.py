#!/usr/bin/python
# -*- coding: utf-8 -*-
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)


class ServerInfo(object):

    def __init__(self, fullname='._', hosttarget='', port=0, txt='SERIAL=0; =; ='):
        self.query_sdRef = False
        self.resolve_sdRef = False
        self.user = ''
        self.password = ''
        self.fullname = fullname
        self.name = fullname.split('._')[0]
        self.host = hosttarget
        self.port = port
        # Depending on the platform, the txt record must be reverted...
        if txt.endswith('LAIRES'):
            txt = txt[::-1]
        self.txt = txt
        v = self.txt.split('; ')
        logging.debug('%s %s %s', txt, self.txt, v)
        self.serial = v[0].split('=')[1]
        self.cap = []
        if len(v) > 1:
            for c in v[1:]:
                cp, val = c.split('=')
                if val == '1':
                    self.cap.append(cp)
        self.ip = False
        self._addr = False

    @property
    def addr(self):
        if self._addr:
            return self._addr
        if not self.ip:
            return False
        return 'https://%s:%i/RPC' % (self.ip, self.port)

    def __str__(self):
        r = '  fullname   =' + self.fullname + '\n'
        r += '  hosttarget =' + self.host + '\n'
        if self.ip:
            r += '  IP =' + self.ip + '\n'
        r += '  port	  =%i' % self.port + '\n'
        r += '  txt	   =' + self.txt
        return r

    def fromAddr(self, addr):
        """Builds itself from an address string like 192.168.0.1:3880/RPC"""
        addr = str(addr)
        self._addr = addr
        if addr.startswith('https://'):
            addr = addr[7:]
        sp = addr.split(':')
        if len(sp) == 2:
            self.port = int(sp[1])
            self.host = ''
            self._addr = addr
        self.user = ''
        self.password = ''
