cppython: bring C++ classes to Python 
######################################

.. contents:: :local:

``cppython`` brings C++ classes to Python world using cython

- Automatically generate C++ wrapper classes and cython files
- Support pure virtual method
- C++ virtual method could be override in Python sub class
  
To wrap a non-pod c++ class Foo:

#. export forward name "Foo" in *.pxd file
#. make Foo proxy class inheriting from class Foo in C++
#. override each virtual member function in proxy class to support override in python   
#. export Foo proxy class and its methods in *.pxd file
#. wrapper Foo proxy class in *.pyx file
#. write proxy api for each of the Foo proxy's virtual methods in *.pxi
