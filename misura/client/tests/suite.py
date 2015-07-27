#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Auto-discovery suite"""
import os
import sys
import unittest
from traceback import format_exc
from misura.canon.logger import Log as logging

patterns = ['test_*.py',  # unit tests
            'sim_*.py', 	# large, complete simulations
            'dev_*.py']		# requiring connected peripherals


def determine_path():
    """Borrowed from wxglade.py"""
    try:
        root = __file__
        if os.path.islink(root):
            root = os.path.realpath(root)
        return os.path.dirname(os.path.abspath(root))
    except:
        logging.debug('%s %s', "I'm sorry, but something is wrong.")
        logging.debug(
            '%s', "There is no __file__ variable. Please contact the author.")
        sys.exit()

d = determine_path()


def load_tests(loader, tests, pattern):
    """Discover and load all unit tests"""
    suite = unittest.TestSuite()
    lst = []
    d1, foo = os.path.split(d)
    for dirpath, dirnames, filenames in os.walk(d1):
        # Skip hidden folders
        if dirpath.count('/.') > 0:
            continue
        # Allow only "tests" dirs
        if os.path.sep + 'tests' not in dirpath:
            continue
        # Require an __init__.py file to be present
        if '__init__.py' not in filenames:
            continue
        # Normalize dirpath ending
        if not dirpath.endswith(os.path.sep):
            dirpath = dirpath + os.path.sep
        # if not 'conf/tests' in dirpath:
        # 	continue
        # Remember for future use
        lst.append(dirpath)
    d2 = os.path.split(d1)[0]
    d2 = os.path.split(d2)[0]
    os.chdir(d2)
# 	os.chdir(d1)
    logging.debug('%s %s', 'TESTS from:', d2)
    for i, a in enumerate(lst):
        print i, a
    for dirpath in lst:
        logging.debug('%s %s', 'Adding main dir', dirpath)
        for pattern in patterns:
            for all_test_suite in unittest.defaultTestLoader.discover(dirpath, pattern=pattern, top_level_dir=d2):
                for test_suite in all_test_suite:
                    logging.debug('%s %s %s', 'adding', dirpath, test_suite)
                    try:
                        suite.addTests(test_suite)
                    except:
                        logging.debug(format_exc())
    return suite

if __name__ == '__main__':
    unittest.main(verbosity=1)
    logging.debug('%s', 'DONE')
