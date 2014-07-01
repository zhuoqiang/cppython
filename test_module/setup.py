#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''
import sys
import os
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

HERE = os.path.dirname(__file__)


extensions = [
    Extension(
        "foo",
        sources = ["foo.pyx", 'for_test.cpp', 'foo_cppython.cpp'],
        include_dirs = [],
        libraries = [],
        library_dirs = []),
]


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.append('build_ext')
        sys.argv.append('--inplace')
    
    setup(ext_modules=cythonize(extensions))
    
