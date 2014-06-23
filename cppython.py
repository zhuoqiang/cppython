#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''Bring C++ classes to python through the wonderful cython
'''

import sys
import os
import clang
from clang.cindex import *


__author__ = 'ZHUO Qiang'
__date__ = '2014-06-23 21:45'
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(i) for i in __version_info__)

Config.set_library_path(os.path.dirname(clang.__file__))

def parse_cpp_file(file_path):
    tu = TranslationUnit.from_source(
        filename=file_path,
        args=['-x', 'c++'],
        options=TranslationUnit.PARSE_INCOMPLETE|TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
    )
    return tu


def visit(tu, visitor):
    filename = os.path.splitext(tu.spelling)[0]
    visitor.visit_file(filename)
    

if __name__ == '__main__':
    pass
