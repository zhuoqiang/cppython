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


# setup(
#     ext_modules = cythonize(
#         os.path.join(HERE, 'for_test_proxy.pyx'),
#     ),    
# )


setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [
        Extension("foo_test_proxy",
                  sources=[
                      "for_test_proxy.pyx",
                      "for_test.cpp"],
                  language='c++')]
)


if __name__ == '__main__':
    pass
