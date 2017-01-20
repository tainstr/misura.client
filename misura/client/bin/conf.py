#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client import iutils, conf
from misura.client.clientconf import confdb
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    logging.debug('initApp')
    iutils.initApp()
    logging.debug('done initApp', confdb['recent_server'])
    o = iutils.getOpts()
    logging.debug('Passed options', o)
    fp = o['-o']
    mc = conf.MConf(fixed_path=fp)
    if o['-h']:
        mc.setAddr(o['-h'])
    mc.menu.show()
    mc.show()
    sys.exit(iutils.app.exec_())
