#! /usr/bin/env sh

python test_cppython.py && cd test_module; python setup.py && python test.py; cd -
