#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import logging
from misura.client import acquisition, from_argv, iutils


if __name__=='__main__':
	iutils.initApp()
	o=iutils.getOpts()
	logging.debug('%s %s', 'Passed options', o)
	app=iutils.app
	mw=acquisition.MainWindow()
	if o['-h']:
		m=iutils.from_argv()
		mw.setServer(m)
	mw.show()
	sys.exit(app.exec_())
