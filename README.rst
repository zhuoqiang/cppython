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

#. run command ``python cppython.py -t header-file-for-export.hpp -s <C++ source files> -m path/to/module_name``
#. after that you could find generated ``module_name`` files under ``path/to``. you could review and modify manually
#. run command ``cd path/to && python setup.py`` to actually build the python extension module using cython
#. For detail command line argument list, run ``python cppython.py -h``
  
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


How to run test
------------------

*  ubuntu 64 and Mac are supported out of the box
*  ``mock``, ``enum34`` and ``cython`` need to be installed first
*  run ``./test.sh``   


Python GIL
-----------------

if C extension spawn threads, you must call ``PyEval_InitThreads`` at least once in the main thread. 
What it does is init GIL and aquire it. So that python itself could be thread safe running any python code.

In child thread any time you want to manipulate Python objects, make sure to call pair ``PyGILState_Ensure(), PyGILState_Release()`` to get GIL and release it. There API is safe to call recursively.

If you would like to call some non-Python/c blocking code (like ``Join()``), you could use ``PyEval_SaveThread() PyEval_RestoreThread()`` pair to release GIL and re get it

In general situations, the C library needs to call ``PyEval_InitThreads()`` to gain GIL before spawning any thread that invokes python callbacks. And the callbacks need to be surrounded with ``PyGILState_Ensure()`` and ``PyGILState_Release()`` to ensure safe execution.

However, if the C library is running within the context of, say, a python C extension, then there are special cases where it is safe to omit GIL manipulation at all if the sub thread execuation is enclosed by the main thread.


Cython GIL
____________________

export C/C++ all marked as ``nogil`` to tell cython that they are safe to call ``with nogil``

There are 3 ways to mark ``nogil``, they are identical

* ``cdef extern from "export.hpp" nogil:`` nogil for all entity inside ``export.hpp``

* ``cdef cppclass SomeClass(BaseClass) nogil:`` nogil for all class members

* ``void some_member_function(const char * arg) nogil except +`` nogil for a single member

When calling, it could be invoke without gil explicitly:

        with nogil:
            self._this.register_front(address)

            
Notice that without ``with nogil:``, the function still called with GIL wheather or not it has been marked as ``nogil``            
if you call non ``nogil`` quanlifier member inside ``with nogil:`` scope, cython will report error message

``Calling gil-requiring function not allowed without gil``

When called ``with nogil:``, the generated code will have ``PyEval_SaveThread() PyEval_RestoreThread()`` pair enclosed the call.
