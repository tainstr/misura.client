#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from misura.client import iutils, acquisition


if __name__=='__main__':
	iutils.initApp()
	app=iutils.app
	mw=acquisition.MainWindow()
	mw.show()
	sys.exit(app.exec_())