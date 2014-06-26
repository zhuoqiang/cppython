#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
'''
import sys
import os
from distutils.core import setup
from Cython.Build import cythonize

setup(
    name = "foo",
    ext_modules = cythonize('for_test_proxy.pyx'),
    sources=["for_test.cpp"],
)

if __name__ == '__main__':
    pass
