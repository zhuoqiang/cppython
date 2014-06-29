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

    def test_constant(self):
        self.assertEqual(EnumType.ENUM_START, 0)
        self.assertEqual(EnumType.ENUM_MIDDLE, 1)        
        self.assertEqual(EnumType.ENUM_END, 3)                
        self.assertEqual(CONST_1, 1)
        self.assertEqual(CONST_2, 10)
        self.assertEqual(DEFINE_1, '1')

        # self.assertEqual(build_s1(1, "ab"), (1, "ab"))
        s1 = build_s1(1, "ab")
        self.assertEqual(s1.a, 1)        
        self.assertEqual(s1.b, "ab")

        s1.b = "123456789"
        self.assertEqual(s1.b, "1234567")        

        use_s1(s1)
        self.assertEqual(s1.a, 1024)
        
if __name__ == '__main__':
    unittest.main()
