#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.client import iutils
from misura.canon import csutil
from misura.client import graphics
import veusz.utils.vzdbus as vzdbus
import veusz.utils.vzsamp as vzsamp


def run():
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
	
if __name__=='__main__':
	run()


