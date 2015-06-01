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

from foo import *
import unittest

try:
    unicode
except:
    unicode = str

def b(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return s


if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

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

    def test_struct(self):
        s1 = build_s1(1, b("ab"))
        self.assertEqual(s1.a, 1)        
        self.assertEqual(s1.b, b("ab"))

        s1.b = b("123456789")
        self.assertEqual(s1.b, b("1234567"))        
        self.assertTrue(s1.b[0] in (b('1'), ord('1')))

        use_s1(s1)
        self.assertEqual(s1.a, 1024)
        
        use_s1_pointer(s1)
        self.assertEqual(s1.a, 777)
        
    def test_class(self):
        c2 = C2(1)
        self.assertEqual(c2.normal_method(1), 3)
        self.assertEqual(c2.char_pointer_method(1, b("hello")), b("ello"))

        with self.assertRaisesRegex(RuntimeError, str('.*?::pure_virtual_method not implemented')):
            c2.pure_virtual_method()

        self.assertEqual(c2.static_method(), 4)
        # TODO make C++ static method a python static method
        # self.assertEqual(C2.static_method(), 4)        
            
        class D2(C2):
            def __init__(self):
                super(D2, self).__init__(10)
            
            def pure_virtual_method(self):
                return self.normal_method(10) + 10
            
        d2 = D2()
        self.assertEqual(d2.pure_virtual_method(), 31)
        
        c1 = C1(d2)
        self.assertEqual(c1.virtual_method(), 1)
        self.assertEqual(c1.virtual_method_call_other(), 32)
        s1 = build_s1(1, b("ab"))
        self.assertEqual(s1.a, 1)
        self.assertEqual(c1.on_struct(s1), 1)
        self.assertEqual(s1.a, 111)

        self.assertEqual(c1.on_struct_pointer(s1), 111)
        self.assertEqual(s1.a, 222)
        
        class D1(C1):
            def __init__(self):
                super(D1, self).__init__(d2)
            
            def virtual_method(self):
                return 100

        d1 = D1()
        self.assertEqual(d1.virtual_method(), 100)
        self.assertEqual(call_c1_virtual_method(d1), 100)
        self.assertEqual(d1.virtual_method_call_other(), 32)
                
if __name__ == '__main__':
    unittest.main()
