#!/usr/bin/python
# -*- coding: utf-8 -*-
"""LICENSING NOTICE
This module should not be distributed in source nor byte-compiled form.
This module imports GPL libraries and thus, it must be considered an internal, unreleased software tool.

""" 

import os, sys
from misura.client import clientconf

def determine_path(root=__file__):
    """Borrowed from wxglade.py"""
    try:
        #       root = __file__
        if os.path.islink(root):
            root = os.path.realpath(root)
        return os.path.dirname(os.path.abspath(root))
    except:
        print("I'm sorry, but something is wrong.")
        print("There is no __file__ variable. Please contact the author.")
        sys.exit()

testdir = determine_path()+'/'  # Executable path
clientconf.activate_plugins(clientconf.confdb)