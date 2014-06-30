#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''
import sys
import os
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

HERE = os.path.dirname(__file__)


extensions = [
    Extension(
        "for_test_proxy",
        sources = ["for_test_proxy.pyx", 'for_test.cpp'],
        include_dirs = [],
        libraries = [],
        library_dirs = []),
]


setup(
    ext_modules = cythonize(extensions),
)

if __name__ == '__main__':
    pass
