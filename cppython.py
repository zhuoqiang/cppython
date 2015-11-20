#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''Bring C++ classes to python
'''
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import re
import datetime
import argparse
from datetime import datetime
from contextlib import contextmanager
from io import BytesIO

from clang.cindex import *
import clang

__author__ = 'ZHUO Qiang'
__date__ = '2014-06-23 21:45'
__version_info__ = (0, 3, 0)
__version__ = '.'.join(str(i) for i in __version_info__)


try:
    unicode
except:
    unicode = str

def u(s):
    if isinstance(s, unicode):
        return s
    return s.decode('utf-8')


def parse_type(t):
    types = t.split()
    pointer = ''
    quanlify = ''
    if types[-1] == '*':
        pointer = '*'
        types.pop()
    if len(types) > 1:
        quanlify = ''.join(types[:-1])
    # base_type, quanlify, pointer
    return types[-1], quanlify, pointer
    
    

# Assume clang lib is beside clang package
Config.set_library_path(os.path.dirname(clang.__file__))

def parse_cpp_file(file_path, include_paths=None):
    # TODO add include path
    tu = TranslationUnit.from_source(
        filename=file_path,
        args=['-x', 'c++'],
        options=(
            TranslationUnit.PARSE_INCOMPLETE
            | TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
            | TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD # for Macro definition
            | TranslationUnit.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION # for comment doc
        ),
    )
    return tu

    
def get_proxy_name(name):
    return name + '_proxy'
    
    
def pairwise(iterable):
    iterable = iter(iterable)
    last = next(iterable)
    for i in iterable:
        yield last, i
        last = i
    yield last, None
    
def get_brief_comment(cursor, encoding='utf-8'):
    # TODO add docstring from comment
    return cursor.brief_comment.decode(encoding).strip().strip('/').strip()
    
def get_raw_comment(cursor, encoding='utf-8'):
    # TODO add docstring from comment
    try: 
        comment = cursor.raw_comment.decode(encoding)
    except UnicodeDecodeError:
        comment = cursor.raw_comment.decode('gbk')
    return '\n'.join(line.strip().strip('/').strip() for line in comment.split('\n'))

    
def get_literal(cursor):
    for t in cursor.get_tokens():
        if t.kind == TokenKind.LITERAL:
            return u(t.spelling)
            # return ast.literal_eval(t.spelling)
            

def split_namespace_name(namespace_name):
    all = namespace_name.split('::')
    namespaces, name = all[:-1], all[-1]
    name = name.replace(' &', '')
    return name, namespaces

def is_const_int(type):
    return type.is_const_qualified() and type.kind in (
        TypeKind.SHORT, TypeKind.INT, TypeKind.LONG, TypeKind.LONGLONG, TypeKind.INT128,
        TypeKind.USHORT, TypeKind.UINT, TypeKind.ULONG, TypeKind.ULONGLONG, TypeKind.UINT128)
            
            
def get_compound_typedef_name(compound_type, next_cursor):
    if (next_cursor and next_cursor.kind == CursorKind.TYPEDEF_DECL
        and '{} {}'.format(compound_type, u(next_cursor.spelling)) == u(next_cursor.underlying_typedef_type.spelling)):
        return u(next_cursor.spelling)
    
        
def apply(children, visitor):
    lookahead_children = pairwise(children)
    for child, next_child in lookahead_children:
        if child.kind == CursorKind.TRANSLATION_UNIT:
            filename = u(child.spelling)
            visitor.on_file_begin(filename)

            CLANG_DEFAULT_ENTITIES = ('__int128_t', '__uint128_t', '__builtin_va_list')
            children = (c for c in child.get_children() if u(c.spelling) not in CLANG_DEFAULT_ENTITIES)
            apply(children, visitor)
            visitor.on_file_end()

        if child.kind == CursorKind.NAMESPACE and child.get_children():
            visitor.on_namespace_begin(u(child.spelling))
            apply(child.get_children(), visitor)
            visitor.on_namespace_end(u(child.spelling))

        elif child.kind == CursorKind.TYPEDEF_DECL:
            visitor.on_typedef(u(child.spelling), u(child.underlying_typedef_type.spelling))

        elif child.kind == CursorKind.ENUM_DECL:
            enum_typename = u(child.spelling)
            enum_constants = [(u(c.spelling), c.enum_value)
                              for c in child.get_children()
                              if c.kind == CursorKind.ENUM_CONSTANT_DECL]
            if enum_constants:
                visitor.on_enum(enum_typename, enum_constants)

        elif child.kind == CursorKind.VAR_DECL and is_const_int(child.type):
            visitor.on_const_int(u(child.spelling), get_literal(child))

        elif child.kind == CursorKind.MACRO_DEFINITION:
            name = u(child.spelling)
            if not name.startswith('_') and name not in ('OBJC_NEW_PROPERTIES',):
                visitor.on_macro_value(name, get_literal(child))

        elif child.kind in (CursorKind.STRUCT_DECL, CursorKind.CLASS_DECL):
            compound_name = 'struct' if child.kind == CursorKind.STRUCT_DECL else 'class'
            name = u(child.spelling)
            typedef = False
            if not name:
                name = get_compound_typedef_name(compound_name, next_child)
                if name:
                    typedef = True
                    next(lookahead_children)
                else:
                    continue # discard struct with no name
                
            if child.type.is_pod():
                if child.is_definition():
                    visitor.on_pod_begin(compound_name, name, typedef)
                    apply(child.get_children(), visitor)
                    visitor.on_pod_end(name)
                else:
                    visitor.on_pod_declaration(compound_name, name, typedef)
            else:
                if child.is_definition():
                    visitor.on_class_begin(compound_name, name, typedef)
                    apply(child.get_children(), visitor)
                    visitor.on_class_end(name)
                else:
                    visitor.on_class_declaration(compound_name, name, typedef)

        elif child.kind == CursorKind.FIELD_DECL:
            if child.access_specifier.name != 'PRIVATE':
                name = u(child.spelling)
                visitor.on_field(name, u(child.type.spelling))

        elif child.kind == CursorKind.CXX_METHOD:
            if child.access_specifier.name != 'PRIVATE':
                name = u(child.spelling)
                access = child.access_specifier.name.lower()
                return_type = u(child.result_type.spelling)
                parameters = [(u(i.type.spelling), u(i.spelling)) for i in child.get_arguments()]
                method_type = ''
                if child.is_static_method():
                    method_type = 'static'
                elif child.is_pure_virtual_method():
                    method_type = 'pure'
                elif child.is_virtual_method():
                    method_type = 'virtual'
                visitor.on_method(name, return_type, parameters, access, method_type, child)
                
        elif child.kind == CursorKind.FUNCTION_DECL:
            name = u(child.spelling)
            return_type = u(child.result_type.spelling)
            parameters = [(u(i.type.spelling), u(i.spelling)) for i in child.get_arguments()]
            visitor.on_function(name, return_type, parameters)
            
        elif child.kind == CursorKind.CONSTRUCTOR:
            name = u(child.spelling)
            parameters = [(u(i.type.spelling), u(i.spelling)) for i in child.get_arguments()]        
            visitor.on_constructor(name, parameters)
            
        else:
            # print child.kind, child.spelling, child.type.spelling
            pass
        
    
class VisitorGroup(object):
    def __init__(self, visitors):
        self.visitors = list(visitors)

    def __getattr__(self, name):
        def method(*l, **kw):
            for visitor in self.visitors:
                getattr(visitor, name)(*l, **kw)
                
        return method
        
        
class IndentFile(object):
    def __init__(self, path=None, indent='    '):
        if path:
            self.file = open(path, 'wb')
        else:
            self.file = BytesIO()
        self.indent = indent
        self.level = 0
        
    def close(self):
        if not self.file.closed:
            self.file.close()
        self.level = 0

    def reset_indent(self, level=0):
        if level == 0:
            level = -self.level

        if level < 0:
            self.line()
        self.level = max(0, self.level+level)
    
    def line(self_, line_=u'', *l, **kw):
        # change self to self_ to avoid name conflick so that client could use **locals() as kw
        line = u''.join((self_.level*self_.indent, line_.format(*l, **kw), u'\n'))
        self_.file.write(line.encode('utf-8'))
        
    def write(self, s):
        if isinstance(s, bytes):
            self.file.write(s)
        else:
            self.file.write(s.encode('utf-8'))
        
    @property
    def name(self):
        return self.file.name
        
    
    
@contextmanager        
def indent(visitor):
    visitor.reset_indent(1)
    try:
        yield
    finally:
        visitor.reset_indent(-1)
        
    
class BaseVisitor(object):
    def __init__(self, name, directory, time=None):
        if time is None:
            self.time = datetime.now()

        self.name = name
        if not time:
            self.time = datetime.now()
        self.directory = directory
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)
        self.content_after_begin = False        
        self.banner = 'Generated by cppython v{} at {} for {} module'.format(__version__, self.time.isoformat(), self.name)
        
    def done(self):
        if 'file' in self.__dict__:
            self.file.close()
        
    def on_pod_declaration(self, compound_name, name, typedef):
        pass

    def on_class_declaration(self, compound_name, name, typedef):
        pass

    def on_macro_value(self, *l, **kw):
        pass

    def on_enum(self, *l, **kw):
        pass
    
    def on_typedef(self, *l, **kw):
        pass
    
    def on_pod_begin(self, *l, **kw):
        pass
    
    def on_field(self, *l, **kw):
        pass
    
    def on_pod_end(self, *l, **kw):
        pass
    
    def on_class_begin(self, *l, **kw):
        pass
    
    def on_method(self, *l, **kw):
        pass
    
    def on_class_end(self, *l, **kw):
        pass
    
    def on_file_end(self, *l, **kw):
        pass
    
        
class PxdVisitor(BaseVisitor):
    '''Generate pxd file exporting C++ header declaration in cython
    '''
    
    def __init__(self, name, directory='.', time=None):
        super(PxdVisitor, self).__init__(name, directory, time)
        self.namespaces = []
        self.content_after_begin = False
        self.class_name = None
        
    def on_file_begin(self, filename):
        # TODO Add file header
        
        name = os.path.join(self.directory, os.path.splitext(os.path.basename(filename))[0] + '.pxd')
        self.file = IndentFile(name)
        self.header_file_path = os.path.relpath(filename, self.directory)
        
        self.file.line("'''{}'''", self.banner)
        self.file.line('from libcpp cimport bool')
        self.file.line('from cpython.ref cimport PyObject')
        
        # "nogil" quanlifier marks all entities (function, member function) nogil
        # so that they could be called "with nogil:" later
        self.file.line('cdef extern from "{}" nogil:', self.header_file_path)
        self.file.reset_indent(1)
        self.content_after_begin = False
        
    def on_file_end(self):
        if not self.content_after_begin:
            self.file.line('pass')
        self.done()
        
    def on_namespace_begin(self, namespace):
        self.namespaces.append(namespace)
        self.file.line('cdef extern from "{}" namespace "{}" nogil:',
                       self.header_file_path, '::'.join(self.namespaces))
        self.file.reset_indent(1)
        self.content_after_begin = False
        
    def on_namespace_end(self, namespace):
        if not self.content_after_begin:
            self.file.line('pass')
        self.file.reset_indent(-1)
        self.namespaces.pop()
        self.content_after_begin = True
        
    def on_typedef(self, name, typename):
        self.file.line('ctypedef {} {}', typename, name)
        self.content_after_begin = True
        
    def on_enum(self, name, constants):
        self.file.line()
        self.file.line('cdef enum {}:', name)
        with indent(self.file):
            for k, v in constants:
                self.file.line('{} = {}', k, v)
                # self.file.line('{}', k)
        self.content_after_begin = True
        
    def on_const_int(self, name, value):
        self.file.line('cdef enum: {} = {}', name, value)
        # self.file.line('cdef enum: {}', name)        
        self.content_after_begin = True        
        
    def on_macro_value(self, name, value):
        # Macro should not be export, otherwise will failed 
        pass
        
    def on_pod_begin(self, kind, name, typedef):
        self.content_after_begin = False
        self.file.line()
        define = 'ctypedef' if typedef else 'cdef'
        self.file.line('{} {} {}:', define, kind, name)
        self.file.reset_indent(1)
        
    def on_pod_end(self, name):
        if not self.content_after_begin:
            self.file.line('pass')
        self.file.reset_indent(-1)
        self.content_after_begin = True        
        
    def on_class_begin(self, kind, name, typedef):
        self.class_name = name
        self.file.line('cdef cppclass {}:', name)
        with indent(self.file):
            self.file.line('pass')        
        
    def on_class_end(self, name):
        self.class_name = None
        
    def on_field(self, name, typename):
        self.file.line('{} {}', typename, name)
        self.content_after_begin = True
        
    def on_constructor(self, name, parameters):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type, cursor, *l, **kw):        
        pass
        
    def on_function(self, name, return_type, parameters):
        # parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
        parameters_list = ', '.join('{} {}'.format(split_namespace_name(t)[0], n) for (t, n) in parameters)        
        return_name, namespaces = split_namespace_name(return_type)
        self.file.line('cdef {} {}({}) nogil except +', return_name, name, parameters_list)
        
        
class PxdProxyVisitor(BaseVisitor):
    '''Generate pxd file exporting C++ proxy header declaration in cython
    '''
    
    def __init__(self, name, directory='.', time=None):
        super(PxdProxyVisitor, self).__init__(name, directory, time)
        self.namespaces = []
        self.content_after_begin = False
        self.class_name = None
        self.constructors = set()
        self.class_names = set()
        self.pod_names = set()
        
    def on_file_begin(self, filename):
        # TODO Add file header
        
        self.file = IndentFile(os.path.join(self.directory, self.name+'_cppython.pxd'))
        self.header_file_path = self.name+'_cppython.hpp'
        self.import_name = os.path.basename(os.path.splitext(filename)[0])
        
        self.file.line("'''{}'''", self.banner)
        self.file.line('from libcpp cimport bool')
        self.file.line('from cpython.ref cimport PyObject')
        self.file.line('cimport {}', self.import_name)        
        self.file.line('cdef extern from "{}" nogil:', self.header_file_path)
        self.file.reset_indent(1)
        self.content_after_begin = False
        
    def on_file_end(self):
        if not self.content_after_begin:
            self.file.line('pass')
        self.done()
        
    def on_namespace_begin(self, namespace):
        pass
        
    def on_namespace_end(self, namespace):
        pass
        
    def on_typedef(self, name, typename):
        pass
        
    def on_enum(self, name, constants):
        pass
        
    def on_const_int(self, name, value):
        pass
        
    def on_macro_value(self, name, value):
        pass
        
    def on_pod_begin(self, kind, name, typedef):
        self.pod_names.add(name)        
        
    def on_pod_end(self, name):
        pass
        
    def on_class_begin(self, kind, name, typedef):
        self.class_names.add(name)
        self.class_name = get_proxy_name(name)
        self.file.line('cdef cppclass {}({}.{}):', self.class_name, self.import_name, name)
        self.file.reset_indent(1)
        
    def on_constructor(self, name, parameters):
        self.constructors.add(name)
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        self.file.line('{}(PyObject* self_object, {})', self.class_name, parameters_list)
        
    def get_use_type(self, typename):
        name = typename.split()[0]
        if name in self.class_names or name in self.pod_names:
            return typename.replace(name, '{}.{}'.format(self.import_name, name))
            
        return typename
        
        
    def on_class_end(self, name):
        if name not in self.constructors:
            self.file.line('{}(PyObject* self_object)', self.class_name)
        self.class_name = None
        self.file.reset_indent(-1)
        
    def on_field(self, name, typename):
        # TODO enhance 
        if self.class_name is not None:
            # only define inside class
            self.file.line('{} {}', typename, name)        
        
    def on_method(self, name, return_type, parameters, access, method_type, cursor, *l, **kw):
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        return_name, namespaces = split_namespace_name(return_type)
        
        self.file.line('{} {}({}) except +', return_name, name, parameters_list)
        
        # make c++ base class normal virtual method accessble from python sub class
        # if method_type == 'virtual' and method_type != 'pure':
        #     self.file.line('{} super_{}({}) except +', return_name, name, parameters_list)            
        
    def on_function(self, name, return_type, parameters):
        pass
        
        
class PyxVisitor(BaseVisitor):
    '''Generate pyx file wrappering C++ entieis in cython
    '''
    
    def __init__(self, name, directory='.', time=None):
        super(PyxVisitor, self).__init__(name, directory, time)
        self.types = {}
        self.pod_types = set()
        self.class_types = set()
        self.constructors = set()
        
    def on_file_begin(self, filename):
        # TODO Add file header
        self.file = IndentFile(os.path.join(self.directory, self.name+'.pyx'))
        self.import_name = os.path.splitext(os.path.basename(filename))[0]
        self.import_proxy_name = self.name + '_cppython'
        
        self.file.line('# distutils: language = c++')
        # make python3 string convert to const char* automatically on interface
        # self.file.line('# cython: c_string_type=str, c_string_encoding=ascii')
        self.file.line("'''{}'''", self.banner)
        self.file.line('cimport {}', self.import_name)
        self.file.line('cimport {}', self.import_proxy_name)
        self.file.line('cimport libc.string')
        self.file.line('from libcpp cimport bool')
        self.file.line('from cpython.ref cimport PyObject')
        
        # for any external C/C++ thread
        # TODO, make PyEval_InitThreads optional cause it slows down single thread application
        self.file.line('cdef extern from "Python.h":')
        with indent(self.file):
            self.file.line('void PyEval_InitThreads()')
        self.file.line('PyEval_InitThreads()')
        
        # self.file.line('from cython cimport view')
        self.file.line('import enum # for python 2.x install enum34 package')
        self.file.line()
        
    def on_file_end(self):
        self.file.line('include "{}"', os.path.basename(self.file.name.replace('.pyx', '.pxi')))
        self.done()
        
    def on_namespace_begin(self, namespace):
        pass
        
    def on_namespace_end(self, namespace):
        pass
        
    def on_typedef(self, name, typename):
        self.types[name] = typename
        
    def on_enum(self, name, constants):
        self.file.line()
        self.file.line('class {}(enum.IntEnum):', name)
        with indent(self.file):
            for name, value in constants:
                self.file.line('{} = {}.{}', name, self.import_name, name)
        
    def on_const_int(self, name, value):
        self.file.line('{} = {}.{}', name, self.import_name, name)
        
    def on_macro_value(self, name, value):
        self.file.line('{} = {}', name, value)
        
    def on_pod_begin(self, kind, name, typedef):
        self.pod_types.add(name)
        self.file.line('cdef class {}:', name)
        self.file.reset_indent(1)
        self.file.line('cdef {}.{} _this', self.import_name, name)
        self.file.line('cdef _from_c_(self, {}.{} c_value):', self.import_name, name)
        with indent(self.file):
            self.file.line('self._this = c_value')
            self.file.line('return self')            
            
    def on_pod_end(self, name):
        self.file.reset_indent(-1)
        
        
    def on_class_begin(self, kind, name, typedef):
        self.class_types.add(name)
        self.file.line('cdef class {}:', name)
        self.file.reset_indent(1)
        
        proxy_name = get_proxy_name(name)
        self.file.line('cdef {}.{}* _this', self.import_proxy_name, proxy_name)
        self.file.line()
            
        self.file.line('def __dealloc__(self):')
        with indent(self.file):
            self.file.line('del self._this')
            
            
    def on_constructor(self, name, parameters):
        self.constructors.add(name)
        proxy_name = get_proxy_name(name)        
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        parameters_names = ', '.join(self.get_use_format(t, n) for (t, n) in parameters)
        
        # parameters_list = ', '.join(('self', parameters_list, '*l', '**kw'))
        parameters_list = ', '.join(('self', parameters_list))
        self.file.line('def __init__({}):', parameters_list)
        with indent(self.file):
            self.file.line('self._this = new {}.{}(<PyObject*>(self), {})',
                           self.import_proxy_name, proxy_name, parameters_names)
        
    def on_class_end(self, name):
        if name not in self.constructors:
            proxy_name = get_proxy_name(name)            
            self.file.line('def __cinit__(self):')
            with indent(self.file):
                self.file.line('self._this = new {}.{}(<PyObject*>(self))',
                               self.import_proxy_name, proxy_name)
            
        self.file.line('pass')
        self.file.reset_indent(-1)
        
    def is_char_array(self, typename):
        return re.match(r'char \[\d+\]', self.types.get(typename, typename)) is not None
        
    def on_field(self, name, typename):
        self.file.line('property {}:', name)
        with indent(self.file):
            if self.is_char_array(typename):
                self.file.line('def __get__(self):')
                with indent(self.file):
                    self.file.line('return bytes(self._this.{})[:sizeof(self._this.{})]', name, name)
                self.file.line('def __set__(self, value):')
                with indent(self.file):
                    self.file.line('cdef size_t length = min(sizeof(self._this.{}), len(value))', name)
                    self.file.line('libc.string.memcpy(self._this.{}, <char*>(value), length)',name)
            else:
                self.file.line('def __get__(self):')
                with indent(self.file):
                    self.file.line('return self._this.{}', name)
                self.file.line('def __set__(self, value):')
                with indent(self.file):
                    self.file.line('self._this.{} = value', name)
        
                    
    def on_method(self, name, return_type, parameters, access, method_type, cursor, *l, **kw):        
        # remove namespace and reference
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = 'self, ' + ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        parameters_names = ', '.join(self.get_use_format(t, n) for (t, n) in parameters)
        return_name, namespaces = split_namespace_name(return_type)
        self.file.line('def {}({}):', name, parameters_list)
        with indent(self.file):
            # using with nogil release the GIL when deligate to C/C++ funciton
            # which could help on blocking/IO method but may potentially decrease simply method
            # need some test on this
            self.file.line('with nogil:')
            with indent(self.file):
                ret_val = '' if return_name == 'void' else 'ret = '
                self.file.line('{}self._this.{}({})', ret_val, name, parameters_names)
            
            if return_name in self.pod_types:
                self.file.line('return {}()._from_c_(ret)', return_name)
            elif return_name != 'void':
                self.file.line('return ret')
                
                
    def get_use_format(self, typename, name):
        is_pointer = typename[-1] == '*'
        class_name = typename.split()[0]
        if class_name in self.pod_types:
            if is_pointer:
                return '&{}._this'.format(name)
            else:
                return '{}._this'.format(name)

        if class_name in self.class_types:
            # return '<{}.{}*>({}._this)'.format(self.import_name, class_name, name)
            return '{}._this'.format(name)            
        return name
                    
        
    def get_use_type(self, typename):
        name = typename.split()[0]
        if name in self.class_types or name in self.pod_types:
            return name

        return typename
        
    def get_proxy_type(self, typename):
        name = self.get_use_type(typename)
        if name in self.class_types:
            return get_proxy_name(name)
            
        return name
        
        
    def on_function(self, name, return_type, parameters):
        # remove namespace and reference
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        parameters_names = ', '.join(self.get_use_format(t, n) for (t, n) in parameters)
        return_name, namespaces = split_namespace_name(return_type)
        self.file.line('cpdef {}({}):', name, parameters_list)
        
        with indent(self.file):
            self.file.line('with nogil:')
            with indent(self.file):
                ret_val = '' if return_name == 'void' else 'ret = '
                self.file.line('{}{}.{}({})', ret_val, self.import_name, name, parameters_names)
            
            if return_name in self.pod_types:
                self.file.line('return {}()._from_c_(ret)', return_name)
            elif return_name != 'void':
                self.file.line('return ret')

                
class HppVisitor(BaseVisitor):
    '''Generate C++ header file wrapping C++ non pod classes for use in python
    '''
    
    def __init__(self, name, directory='.', time=None):
        super(HppVisitor, self).__init__(name, directory, time)
        self.namespaces = []
        self.class_name = None
        self.constructors = set()
        
    def on_file_begin(self, filename):
        # TODO Add file header
        
        self.file = IndentFile(os.path.join(self.directory, self.name + '_cppython.hpp'))
        self.header_file_path = os.path.relpath(filename, self.directory)
        
        stem = os.path.splitext(os.path.basename(filename))[0]
        self.header_guard = '_{}_CPPYTON_HPP_'.format(stem.upper())
        self.file.line("// {}", self.banner)
        self.file.line('#ifndef {}', self.header_guard)
        self.file.line('#define {}', self.header_guard)
        self.file.line()                
        self.file.line('#include "{}"', self.header_file_path)
        self.file.line()        
        self.file.write('''
        
#if __cplusplus > 199711L
#define CPPYTHON_CPP_STD11_OVERRIDE override
#else
#define CPPYTHON_CPP_STD11_OVERRIDE
#endif        
        
struct _object;
typedef _object PyObject;

class CppythonProxyBase
{
protected:    
    CppythonProxyBase(PyObject* self);
    virtual ~CppythonProxyBase();
    
    PyObject* Self() const
    {
        return self_;
    }

private:
    PyObject* const self_;
};

''')
        
    def on_file_end(self):
        self.file.line('')
        self.file.line('#endif//{}', self.header_guard)
        self.done()
        
    def on_namespace_begin(self, namespace):
        self.namespaces.append(namespace)
        
    def on_namespace_end(self, namespace):
        self.namespaces.pop()
        
    def on_typedef(self, name, typename):
        pass
        
    def on_enum(self, name, constants):
        pass
        
    def on_const_int(self, name, value):
        pass
        
    def on_macro_value(self, name, value):
        pass
        
    def on_pod_begin(self, kind, name, typedef):
        pass
        
    def on_pod_end(self, name):
        pass
        
    def on_class_begin(self, kind, name, typedef):
        self.class_name = get_proxy_name(name)
        base_class_full_name = '::'+'::'.join(self.namespaces+[name])
        self.file.line('class {} : public CppythonProxyBase, public {}',
                       self.class_name, base_class_full_name)
        self.file.line('{{')
        self.file.line('public:')
        self.file.reset_indent(1)
        self.file.line('typedef {} BaseClassType;', base_class_full_name);
        
    def on_constructor(self, name, parameters):
        self.constructors.add(name)
        parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in [('PyObject*', 'object')] + parameters)
        parameters_name = ', '.join(n for (t, n) in parameters)
        self.file.line('{}({})', self.class_name, parameters_list)
        self.file.line('    : CppythonProxyBase(object)')
        self.file.line('    , BaseClassType({})', parameters_name)        
        self.file.line('{{')
        self.file.line('}}')
        self.file.line()
        
    def on_class_end(self, name):
        if name not in self.constructors:
            self.file.line('{}(PyObject* object)', self.class_name)
            self.file.line('    : CppythonProxyBase(object)')
            self.file.line('{{')
            self.file.line('}}')
            self.file.line()
        
        self.file.reset_indent(-1)
        self.file.line('}};')
        self.file.line()
        self.class_name = None
        
    def on_field(self, name, typename):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type, cursor, *l, **kw):
        if method_type in ('pure', 'virtual'):
            parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
            self.file.line('{} {}({}) CPPYTHON_CPP_STD11_OVERRIDE;', return_type, name, parameters_list)

            # if method_type == 'virtual' and method_type != 'pure':
            #     # make base c++ class normal virtual method accessable from python sub class
            #     # under another name : super_xxx
            #     self.file.line('{} super_{}({})', return_type, name, parameters_list)
            #     self.file.line('{{')
            #     parameters_name = ', '.join(n for (t, n) in parameters)
            #     with indent(self.file):
            #         self.file.line('return BaseClassType::{}({});', name, parameters_name)
            #     self.file.line('}}')
            #     self.file.line('')
            
        
    def on_function(self, name, return_type, parameters):
        pass
                
                
class CppVisitor(BaseVisitor):
    '''Generate C++ source files wrapping C++ non pod classes for use in python
    '''
    
    def __init__(self, name, directory='.', time=None):
        super(CppVisitor, self).__init__(name, directory, time)
        self.namespaces = []
        self.class_name = None
        
    def on_file_begin(self, filename):
        # TODO Add file header
        
        self.file = IndentFile(os.path.join(self.directory, self.name+'_cppython.cpp'))
        self.header_file_path = self.name+'_cppython.hpp'
        
        stem = os.path.basename(os.path.splitext(filename)[0])
        self.file.line("// {}", self.banner)
        self.file.line('#include "{}"', self.header_file_path)
        self.file.write('''
#include <stdexcept>
#include <Python.h>
#include "%s.h"

CppythonProxyBase::CppythonProxyBase(PyObject* self)
    : self_(self)
{
    if (self_ == NULL) {
        throw std::runtime_error("self object is NULL");
    }
}

CppythonProxyBase::~CppythonProxyBase()
{
}

''' % self.name)
        
    def on_file_end(self):
        self.done()
        
    def on_namespace_begin(self, namespace):
        self.namespaces.append(namespace)
        
    def on_namespace_end(self, namespace):
        self.namespaces.pop()
        
    def on_typedef(self, name, typename):
        pass
        
    def on_enum(self, name, constants):
        pass
        
    def on_const_int(self, name, value):
        pass
        
    def on_macro_value(self, name, value):
        pass
        
    def on_pod_begin(self, kind, name, typedef):
        pass
        
    def on_pod_end(self, name):
        pass
        
    def on_class_begin(self, kind, name, typedef):
        self.base_class_name = name
        self.class_name = get_proxy_name(name)
        
    def on_class_end(self, name):
        self.base_class_name = None
        self.class_name = None
        
    def on_field(self, name, typename):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type, cursor, *l, **kw):        
        if method_type in ('pure', 'virtual'):
            parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
            parameters_name = ', '.join(n for (t, n) in parameters)
            parameters_name_for_proxy = ''
            if parameters_name:
                parameters_name_for_proxy = ', ' + parameters_name
            self.file.line('{} {}::{}({})', return_type, self.class_name, name, parameters_list)
            self.file.line('{{')
            with indent(self.file):
                self.file.line('bool const overrided = cppython_has_method(this->Self(), "{}");', name)
                self.file.line('if (overrided) {{')
                with indent(self.file):
                    if return_type == 'void':
                        self.file.line('{}_{}_proxy_call(this->Self(){});',
                                       self.base_class_name, name, parameters_name_for_proxy)
                        
                        self.file.line('return;')
                    else:
                        self.file.line('return {}_{}_proxy_call(this->Self(){});',
                                       self.base_class_name, name, parameters_name_for_proxy)                    
                self.file.line('}}')
                if method_type == 'pure':
                    self.file.line('throw std::runtime_error("pure virtual method {}::{} not implemented");',
                                   self.class_name, name)
                else:
                    self.file.line('return BaseClassType::{}({});', name, parameters_name)
                
            self.file.line('}}')
            self.file.line()
        
    def on_function(self, name, return_type, parameters):
        pass
        
    def on_constructor(self, name, parameters):
        pass
         
        
        
class PxiVisitor(BaseVisitor):
    '''Generate public API for wrapping C++
    '''
    
    def __init__(self, name, directory='.', time=None):
        super(PxiVisitor, self).__init__(name, directory, time)
        self.namespaces = []
        self.class_name = None
        self.pod_types = set()
        self.class_types = set()
        
    def on_file_begin(self, filename):
        # TODO Add file header
        self.import_name = os.path.basename(os.path.splitext(filename)[0])
        
        self.file = IndentFile(os.path.join(self.directory, self.name+'.pxi'))

        self.file.line("'''{}'''", self.banner)        
        self.file.line('import types')
        self.file.line('cdef public bool cppython_has_method(object self, const char* method_name) with gil:')
        with indent(self.file):
            # python3 need method name to be Unicode, which python2 could handle as well
            # we encode the method name to unicode
            self.file.line('method = getattr(self, method_name.decode("utf-8"), None)')
            self.file.line('return isinstance(method, types.MethodType)')
        
    def on_file_end(self):
        self.done()
        
    def on_namespace_begin(self, namespace):
        self.namespaces.append(namespace)
        
    def on_namespace_end(self, namespace):
        self.namespaces.pop()
        
    def on_typedef(self, name, typename):
        pass
        
    def on_enum(self, name, constants):
        pass
        
    def on_const_int(self, name, value):
        pass
        
    def on_macro_value(self, name, value):
        pass
        
    def on_pod_begin(self, kind, name, typedef):
        self.pod_types.add(name)
        
    def on_pod_end(self, name):
        pass
        
    def on_class_begin(self, kind, name, typedef):
        self.class_name = name
        self.class_types.add(name)
        
    def on_class_end(self, name):
        self.class_name = None
        
    def on_field(self, name, typename):
        pass
        
    def get_use_format(self, typename, name):
        is_pointer = typename.endswith('*')        
        typename = typename.split()[0]
        if typename in self.pod_types or typename in self.class_types:
            return '{}()._from_c_({}{})'.format(typename, name, '[0]' if is_pointer else '')
        return name
        
    def get_use_type(self, typename):
        unquanlified_type, quanlify, pointer = parse_type(typename)
        if unquanlified_type in self.pod_types or unquanlified_type in self.class_types:
            return '{}.{}{}'.format(self.import_name, unquanlified_type, pointer)
        return typename
        
    def on_method(self, name, return_type, parameters, access, method_type, cursor, *l, **kw):        
        if method_type not in ('virtual', 'pure'):
            return
            
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        parameters_names = [(n, self.get_use_format(t, n)) for (t, n) in parameters]
        # make it keyword parameter
        parameters_names = ', '.join('{}={}'.format(name[0], name[1]) for name in parameters_names)
        return_name, namespaces = split_namespace_name(return_type)
        return_name = self.get_use_type(return_name)
        
        parameters_list = ', '.join(['object self', parameters_list])
        self.file.line('cdef public {} {}_{}_proxy_call({}) with gil:',
                       return_name, self.class_name,
                       name, parameters_list)
        
        return_ = '' if return_name == 'void' else 'return '
        with indent(self.file):
            self.file.line('method = getattr(self, "{}", None)', name)
            self.file.line('{}method({})', return_, parameters_names)
            
    def on_function(self, name, return_type, parameters):
        pass
        
    def on_constructor(self, name, parameters):
        pass
        
        
def generate_setup_file(
        name, directory='.', sources=[], 
        include=[], library=[], library_dir=[], compile_flag=[], 
        link_flag=[], objects=[], time=None):
    '''Generate setup file for building python extension
    '''
    if time is None:
        time = datetime.now()
    
    banner = 'Generated by cppython v{} at {} for {} module'.format(__version__, time.isoformat(), name) 
    sources = [os.path.relpath(os.path.abspath(i), directory) for i in sources]
    
    with open(os.path.join(directory, 'setup.py'), 'w') as f:
        f.write('''#! /usr/bin/env python
# -*- coding: utf-8 -*-
'{}'
import sys
import os
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

HERE = os.path.dirname(__file__)


extensions = [
    Extension(
        "{}",
        sources = [os.path.relpath(i, HERE) for i in ['{}.pyx', '{}_cppython.cpp', {}]],
        extra_objects = {},
        language = 'c++',
        include_dirs = {},
        libraries = {},
        library_dirs = {},
        extra_compile_args = {},
        extra_link_args = {},
        ),
]

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.append('build_ext')
        sys.argv.append('--inplace')
    
    setup(ext_modules=cythonize(extensions))
        '''.format( 
            banner, name, name, name, ', '.join("'{}'".format(i) for i in sources),
            objects, include, library, library_dir, compile_flag, link_flag))

        
        
def main(argv):
    cmd_parser = argparse.ArgumentParser()
    
    cmd_parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))
    cmd_parser.add_argument('-t', '--header', metavar='cpp_header_file.hpp', nargs=1, required=True,
                            help='target c++ header file for wrapping to python module')
    cmd_parser.add_argument('-s', '--source', metavar='cpp_source_file.cpp', nargs='*', default=[],
                            help='additional c++ source files')
    cmd_parser.add_argument('-i', '--include', metavar='dir/to/c++/include', nargs='*', default=[],
                            help='additional c++ include path')
    cmd_parser.add_argument('-l', '--library', metavar='cpplibname', nargs='*', default=[],
                            help='additional library to link')
    cmd_parser.add_argument('-d', '--library-dir', metavar='path/to/lib', nargs='*', default=[],
                            help='additional library directory')
    cmd_parser.add_argument('-m', '--module', metavar='module_dir/module', required=True,
                            help='target module output path and module name')
    cmd_parser.add_argument('-c', '--compile-flag', metavar='" -O3"', nargs="*", default=[],
                            help='specify extra compile flag, with extra space before -, like this: " -O3"')
    cmd_parser.add_argument('-k', '--link-flag', metavar='" -O3"', nargs="*", default=[],
                            help='specify extra link flag, with extra space before -, like this: " -O3"')
    cmd_parser.add_argument('-o', '--object', metavar='path/to/a.so"', nargs="*", default=[],
                            help='specify extra objects to link against')
    
    args = cmd_parser.parse_args(sys.argv[1:])
    
    module_name = os.path.basename(args.module)
    directory = os.path.dirname(args.module)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    header = args.header
    cpp_files = args.source
    include = [os.path.abspath(i) for i in args.include]
    library_dir = [os.path.abspath(i) for i in args.library_dir]
    compile_flag = [i.strip() for i in args.compile_flag]
    link_flag = [i.strip() for i in args.link_flag]
    
    visitors = [v(module_name, directory) for v in
                (PxdVisitor, PyxVisitor, CppVisitor, HppVisitor, PxiVisitor, PxdProxyVisitor)]
    
    apply([parse_cpp_file(h).cursor for h in header], VisitorGroup(visitors))
        
    for v in visitors:
        print('generating {} ...'.format(v.file.name))
        
    print('generating setup.py ...')
    generate_setup_file(
        module_name, directory, cpp_files, include, args.library, 
        library_dir, compile_flag, link_flag, args.object)

    print('done.')
    
    
if __name__ == '__main__':
    try:
        main(sys.argv)
    except LibclangError as e:
        print('ERROR: clang shared library not found, please download and place it in this directory: {}'.format(
            os.path.dirname(clang.__file__)))
        
