#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''
import sys
import os
from distutils.core import setup
from Cython.Build import cythonize

HERE = os.path.dirname(__file__)

setup(
    ext_modules = cythonize(os.path.join(HERE, 'for_test_proxy.pyx')),
)

if __name__ == '__main__':
    pass
