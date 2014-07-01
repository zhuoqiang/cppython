cppython: bring C++ classes to Python 
######################################

.. contents:: :local:

``cppython`` brings C++ classes to Python world using cython

- Automatically generate C++ wrapper classes and cython files
- Support pure virtual method
- C++ virtual method could be override in Python sub class
  
How to export C++ class  
-------------------------

To wrap a non-pod C++ class ``Foo``:

#. Export forward name ``Foo`` in a ``*.pxd`` file
#. Make a C++ proxy class inheriting from class ``Foo`` and also links with python object
#. Override virtual methods in proxy class to make them overrideable in python world as well
#. Export proxy class and its methods in *.pxd file
#. Wrapper Foo proxy class in *.pyx file as a normal Cython class
#. Implement proxy call api for each of the proxy class's virtual methods

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

todo
-----------

* wrap static method as static class method in python, right now it is exported as python instance method
* better support for C++ reference
* better support for C array (using view?)
* forward declaration support
* boost.python support
* support customize C++ entities name
