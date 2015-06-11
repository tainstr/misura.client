#!/usr/bin/python 
# -*- coding: utf-8 -*-
import sys
import logging
from misura.client import iutils, conf
from misura.client.clientconf import confdb



if __name__=='__main__':
	logging.debug('%s', 'initApp')
	iutils.initApp()
	logging.debug('%s %s', 'done initApp', confdb.recent_server)
	o=iutils.getOpts()
	logging.debug('%s %s', 'Passed options', o)
	fp=o['-o']
	mc=conf.MConf(fixed_path=fp)
	if o['-h']:
		mc.setAddr(o['-h'])
	mc.menu.show()
	mc.show()
	sys.exit(iutils.app.exec_())
