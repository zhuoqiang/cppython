#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''
import sys
import os

__author__ = 'ZHUO Qiang'
__date__ = '2014-06-26 15:04'
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(i) for i in __version_info__)

from for_test_proxy import *
import unittest

class Test(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_m(self):
        self.assertEqual(EnumType.ENUM_START, 0)
        self.assertEqual(CONST_1, 1)
        self.assertEqual(CONST_2, 10)
        self.assertEqual(DEFINE_1, '1')

if __name__ == '__main__':
    unittest.main()