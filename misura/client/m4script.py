#!/usr/bin/python
# -*- coding: utf-8 -*-
import network

def default(host='localhost', port=3880, user='admin', password='admin'):
	addr='https://{}:{}/RPC'.format(host,port)
	network.getConnection(addr,user,password,smart=True)
	return network.manager.remote

def from_argv():
	import sys, getopt
	print 'from argv', sys.argv
	opts, args=getopt.getopt(sys.argv[1:], 'h:p:u:w:')
	r={'-h':'localhost', '-p':3880,
		'-u':'admin','-w':'admin'}
	for opt, val in opts:
		r[opt]=val
	return default(host=r['-h'],port=r['-p'],user=r['-u'],password=r['-w'])
