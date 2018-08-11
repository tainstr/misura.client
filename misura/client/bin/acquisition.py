#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import sys
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client import acquisition, from_argv, iutils, configure_logger
import multiprocessing
    
    
def run_acquisition_app():
    iutils.initApp()
    o = iutils.getOpts()
    logging.debug('Passed options', o)
    app = iutils.app
    mw = acquisition.MainWindow()
    if o['-h']:
        m = from_argv()
        mw.succeed_login(m)
    mw.show()
    configure_logger('acquisition.log')
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    multiprocessing.freeze_support()
    run_acquisition_app()