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
        apply(self.tu, mock)

        self.assertListEqual(mock.mock_calls, [
            call.on_file(self.hpp_path),
            call.on_namespace_begin('for_test_namespace'),
            call.on_namespace_begin('inner_namespace'),
            call.on_typedef('IntType', 'int'),
            call.on_enum('EnumType', [
                ('ENUM_START', 0L),
                ('ENUM_MIDDLE', 1L),
                ('ENUM_END', 3L)]),
            call.on_const_int('CONST_1', 1),
            call.on_namespace_end('inner_namespace'),
            call.on_const_int('CONST_2', 10),
            call.on_typedef('CharsType', 'char [7]'),
            call.on_namespace_end('for_test_namespace'),
            call.on_const_int('CONST_3', 3),
        ])

        
    def test_apply_visitor(self):
        v = VisitorGroup([PxdVisitor('test_module'), PyxVisitor('test_module')])
        apply(self.tu, v)

        
if __name__ == '__main__':
    unittest.main()
