#! /usr/bin/env sh

python test_cppython.py && python ./test_module/setup.py build_ext --inplace && PYTHONPATH=./test_module:$PYTHONPATH python ./test_module/test.py
