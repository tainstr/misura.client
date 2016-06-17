#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.client import iutils
from misura.client import graphics
from misura.client.clientconf import confdb, activate_plugins
import veusz.utils.vzdbus as vzdbus
import veusz.utils.vzsamp as vzsamp


def run():
    activate_plugins(confdb)
    app = graphics.GraphicsApp(sys.argv)
# 	iutils.initApp(qapp=app)
# 	vzdbus.setup()
# 	vzsamp.setup()
# 	iutils.initNetwork()
    iutils.initTranslations(app)
    app.startup()
    iutils.initRegistry()
    app.exec_()
# 	csutil.stop_profiler(mw)

if __name__ == '__main__':
    run()
