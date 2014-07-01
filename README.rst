cppython: bring C++ classes to Python 
######################################

.. contents:: :local:

``cppython`` brings C++ classes to Python world using cython

- Automatically generate C++ wrapper classes and cython files
- Support pure virtual method
- C++ virtual method could be override in Python sub class
  
How to export C++ class  
-------------------------

In order to export a non-pod C++ class ``Foo`` to python:

#. Export forward name ``Foo`` in ``*.pxd`` file
#. Create a C++ proxy class inheriting from ``Foo``. It also links with a python object
#. Override virtual methods in proxy class to make them overrideable in python
#. Export proxy class and its methods in *.pxd file
#. Wrap Foo proxy class in *.pyx file as a normal Cython class
#. Implement proxy call API for each of virtual methods

The steps are tedious and boring. ``cppython`` helps you automation the whole process

Files generated   
------------------

Given a header file ``header_file.hpp`` which contains all symbols need to export to python module foo,
cppython will generate following files:

* ``head_file.pxd``: export C++ symbol to cython
* ``foo.pyx``: the main file for foo module, it will generate foo.h and foo.c through cython to build foo module
* ``foo.pxi``: the public API used for proxy call, will be include by ``foo.pyx``
* ``foo_cppython.hpp``: the proxy classes' defination
* ``foo_cppython.cpp``: the proxy classes' implementation
* ``foo_cppython.pxd``: export C++ proxy class to cython
* ``setup.py``: setup file for build python extension


How to use
-------------

#. write a header file which include all the symbols you would like to export, including
   
   - classes
   - POD structs
   - free functions
   - const int
   - enums
   - marco constants

#. run command ``python cppython.py the-header-files-for-export.hpp <additional c++ source files> path/to/module_name``
#. after that you could find generated ``module_name`` files under ``path/to``. you could review and modify manually
#. run command ``cd path/to && python setup.py`` to actually build the python extension module using cython
  
todo
-----------

* wrap static method as static class method in python, right now it is exported as python instance method
* better support for C++ reference
* better support for C array (using view?)
* forward declaration support
* boost.python support
* support customize C++ entities name
* add include path support
* support more than one constructor,right now it only export the first constructor
