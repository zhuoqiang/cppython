#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''

import sys
import os
import unittest
from cppython import *
from mock import MagicMock, call

__author__ = 'ZHUO Qiang'
__date__ = '2014-06-23 22:00'
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(i) for i in __version_info__)

class Test(unittest.TestCase):
    def setUp(self):
        self.hpp_path = 'test_module/for_test.hpp'
        self.tu = parse_cpp_file(self.hpp_path)

    def tearDown(self):
        pass

    def test_apply_mock(self):
        mock = MagicMock()
        apply([self.tu.cursor], mock)

        self.assertListEqual(mock.mock_calls, [
            call.on_file_begin(self.hpp_path),
            call.on_macro_value('DEFINE_1', "'1'"),
            call.on_namespace_begin('for_test_namespace'),
            call.on_namespace_begin('inner_namespace'),
            call.on_typedef('IntType', 'int'),
            call.on_enum('EnumType', [
                ('ENUM_START', 0L),
                ('ENUM_MIDDLE', 1L),
                ('ENUM_END', 3L)]),
            call.on_const_int('CONST_1', '1'),
            call.on_namespace_end('inner_namespace'),
            call.on_const_int('CONST_2', '0x0A'),
            call.on_typedef('CharsType', 'char [7]'),
            call.on_namespace_begin('bar'),            
            call.on_namespace_end('bar'), 
            
            call.on_pod_begin('struct', 'S1', False),
            call.on_field('a', 'int'),
            call.on_field('b', 'CharsType'),
            call.on_pod_end('S1'),
            
            call.on_pod_begin('struct', 'S2', True),
            call.on_field('a', 'int'),
            call.on_pod_end('S2'),
            
            call.on_function('build_s1', 'for_test_namespace::S1', [('int', 'a'), ('const char *', 'b')]),
            call.on_function('use_s1', 'void', [('for_test_namespace::S1 &', 's1')]),
            call.on_function('use_s1_pointer', 'void', [('for_test_namespace::S1 *', 's1')]),
            
            call.on_class_begin('class', 'C2', False),
            call.on_constructor('C2', [('int', 'a')]),
            call.on_method('pure_virtual_method', 'int', [], 'public', 'pure'),
            call.on_method('normal_method', 'int', [('int', 'n')], 'public', ''),
            call.on_method('static_method', 'int', [], 'public', 'static'),
            call.on_class_end('C2'),
            
            call.on_class_begin('class', 'C1', False),
            call.on_constructor('C1', [('for_test_namespace::C2 *', 'c2')]),
            call.on_method('virtual_method', 'int', [], 'public', 'virtual'),
            call.on_method('virtual_method_call_other', 'int', [], 'public', 'virtual'),            
            call.on_method('on_struct', 'int', [('for_test_namespace::S1 &', 's1')], 'public', 'virtual'),
            call.on_method('on_struct_pointer', 'int', [('for_test_namespace::S1 *', 's1')], 'public', 'virtual'),
            # call.on_method('get_c2', 'for_test_namespace::C2 *', [], 'public', 'virtual'),
            
            call.on_class_end('C1'),

            call.on_function('call_c1_virtual_method', 'int', [('for_test_namespace::C1 *', 'c1')]),
            
            call.on_namespace_end('for_test_namespace'),
            call.on_const_int('CONST_3', '3'),
            call.on_file_end(),
        ])

        
    def test_apply_visitor(self):
        directory = 'test_module'
        v = VisitorGroup(v('foo', directory) for v in
                         (PxdVisitor, PyxVisitor, CppVisitor, HppVisitor, PxiVisitor, PxdProxyVisitor))
        apply([self.tu.cursor], v)

        
if __name__ == '__main__':
    unittest.main()
