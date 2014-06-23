#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''

import sys
import os
import unittest
from cppython import *
from mock import MagicMock

__author__ = 'ZHUO Qiang'
__date__ = '2014-06-23 22:00'
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(i) for i in __version_info__)

class Test(unittest.TestCase):
    def setUp(self):
        self.tu = parse_cpp_file('for_test.cpp')

    def tearDown(self):
        pass

    def test_visit_file(self):
        mock = MagicMock()
        visit(self.tu, mock)
        mock.visit_file.assert_called_once_with('for_test')


if __name__ == '__main__':
    unittest.main()
