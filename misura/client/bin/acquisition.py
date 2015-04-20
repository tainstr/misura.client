#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.client import iutils, acquisition


if __name__=='__main__':
	iutils.initApp()
	o=iutils.getOpts()
	print 'Passed options', o
	app=iutils.app
	mw=acquisition.MainWindow()
	if o['-h']:
		m=iutils.from_argv()
		mw.setServer(m)
	mw.show()
	sys.exit(app.exec_())
