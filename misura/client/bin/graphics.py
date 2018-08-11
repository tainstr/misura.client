#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.client import iutils, configure_logger
from misura.client import graphics
from misura.client.clientconf import confdb, activate_plugins
#import veusz.utils.vzdbus as vzdbus 
#import veusz.utils.vzsamp as vzsamp
import multiprocessing

def run_graphics_app():
    activate_plugins(confdb)
    app = graphics.GraphicsApp(sys.argv)
# 	iutils.initApp(qapp=app)
# 	vzdbus.setup()
# 	vzsamp.setup()
# 	iutils.initNetwork()
    iutils.initTranslations(app)
    app.startup()
    iutils.initRegistry()
    configure_logger('browser.log')
    app.exec_()
# 	csutil.stop_profiler(mw)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    run_graphics_app()
