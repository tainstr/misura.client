#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.canon.logger import get_module_logging
logging = get_module_logging(__name__)
from misura.client import acquisition, from_argv, iutils
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    iutils.initApp()
    o = iutils.getOpts()
    logging.debug('%s %s', 'Passed options', o)
    app = iutils.app
    mw = acquisition.MainWindow()
    if o['-h']:
        m = from_argv()
        mw.succeed_login(m)
    mw.show()
    sys.exit(app.exec_())
