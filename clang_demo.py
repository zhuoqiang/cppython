#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''
from __future__ import print_function

import sys
import os

__author__ = '卓强'
__date__ = '2014-07-10 09:58'
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(i) for i in __version_info__)


from clang.cindex import *
import clang
 
Config.set_library_path(os.path.dirname(clang.__file__))

tu = TranslationUnit.from_source(
        filename='clang_demo.hpp',
        args=['-x', 'c++'],
    )
        
def print_cpp_entity(cursor, indent=''):
    # print(dir(cursor))
    print(indent, cursor.kind, cursor.type.spelling, cursor.spelling, 'definition' if cursor.is_definition() else 'declaration')
    for child in cursor.get_children():
        print_cpp_entity(child, indent+'  ')
 
print_cpp_entity(tu.cursor)    


if __name__ == '__main__':
    pass
