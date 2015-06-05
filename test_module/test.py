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
        
        # keyword parameter
        self.assertEqual(c2.char_pointer_method(p=b("hello"), n=2), b("llo"))        

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
        
        
    def test_keyword_parameter(self):
        test_self = self
        
        call_count = {'d':0}
        
        class Revert(C2):
            def __init__(self):
                super(Revert, self).__init__(10)
            
            def char_pointer_method(self, p, n):
                call_count['d'] = 1
                test_self.assertEqual(p, b"hello")
                test_self.assertEqual(n, 1)
                # TODO
                # could not call base class method
                # super(Revert, self).char_pointer_method(p, n)
                # because, it is proxy class and it will call derived method which cause infinit loop
                # we need to find a way to call super class (the proxy calss's super class)
                # maybe wrapper it in another function, and call explicity: 
                # super(Revert, self).super_char_pointer_method(p, n)
                return p[n+1:]
            
        revert = Revert()
        self.assertEqual(call_c1_char_method(revert, 1, b'hello'), b"llo")
        self.assertEqual(call_count['d'], 1)
        
        class Named(C2):
            def __init__(self):
                super(Named, self).__init__(10)
            
            def char_pointer_method(self, *l, **kw):
                call_count['d'] = 2
                test_self.assertTupleEqual(l, ())
                test_self.assertDictEqual(kw, {'p':b'hello', 'n':1})
                return b'world'
            
        named = Named()
        self.assertEqual(call_c1_char_method(named, 1, b'hello'), b'world')
        self.assertEqual(call_count['d'], 2)
        
        class Partial(C2):
            def __init__(self):
                super(Partial, self).__init__(10)
            
            def char_pointer_method(self, p, *l, **kw):
                call_count['d'] = 3
                test_self.assertEqual(p, b"hello")
                test_self.assertTupleEqual(l, ())
                test_self.assertDictEqual(kw, {'n':1})
                return b'partial'
            
        partial = Partial()
        self.assertEqual(call_c1_char_method(partial, 1, b'hello'), b'partial')
        self.assertEqual(call_count['d'], 3)
        
        
    def test_delete(self):
        c2 = C2(7)
        c1 = C1(c2)
        del c1
        self.assertEqual(c2.a, 1024)
                
if __name__ == '__main__':
    unittest.main()
