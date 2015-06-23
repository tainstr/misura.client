#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tests aButton widget."""
import unittest
from misura.canon.logger import Log as logging
from misura.client.tests import iutils_testing
from misura.client import widgets
from misura.canon import option
from PyQt4 import QtGui

logging.debug('%s %s', 'Importing', __name__)
main=__name__=='__main__'

#TODO: generalize a widget testing  framework

def setUpModule():
    logging.debug('%s %s', 'setUpModule', __name__)

def tearDownModule():
    logging.debug('%s', 'Quitting app')
    logging.debug('%s %s', 'tearDownModule', __name__)
    
class aButton(unittest.TestCase):
    def setUp(self):
        self.root=option.ConfigurationProxy()
        
    def wgGen(self):
        self.assertTrue(self.root.has_key('test'))
        w=widgets.build(self.root, self.root, self.root.gete('test'))
        # The current value is not initialized (gete() returns {current:None} )
        self.assertTrue(w is not False)
        return w
        
    def test(self):
        self.root.sete('test', option.ao({}, 'test', 'Button')['test'])
        # Test with short reply
        self.root['test']='test text'
        w=self.wgGen()
        msgBox=w._msgBox()
        self.assertEqual(msgBox.informativeText(),'test text')
        # Try with long reply
        self.root['test']='test text\n'*100
        w.current = self.root['test']
        msgBox=w._msgBox()
        self.assertTrue(str(msgBox.informativeText()).startswith('test text'))
        self.assertEqual(msgBox.detailedText(),self.root['test'])
        if __name__=='__main__':
            w.show()
            QtGui.qApp.exec_()
                  
            
if __name__ == "__main__":
    unittest.main(verbosity=2)  
    
    
