#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''Bring C++ classes to python
'''

import sys
import os
import re
import datetime
import ast
from datetime import datetime
from contextlib import contextmanager

from clang.cindex import *
import clang

__author__ = 'ZHUO Qiang'
__date__ = '2014-06-23 21:45'
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(i) for i in __version_info__)

# Assume clang lib is beside clang package
Config.set_library_path(os.path.dirname(clang.__file__))

def parse_cpp_file(file_path, include_paths=None):
    # TODO add include path
    tu = TranslationUnit.from_source(
        filename=file_path,
        args=['-x', 'c++'],
        options=(
            TranslationUnit.PARSE_INCOMPLETE|
            TranslationUnit.PARSE_SKIP_FUNCTION_BODIES|
            TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD),
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
    
def get_comment(cursor):
    # TODO add docstring from comment
    return cursor.brief_comment.strip().strip('/').strip()
    
    
def get_literal(cursor):
    for t in cursor.get_tokens():
        if t.kind == TokenKind.LITERAL:
            return t.spelling
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
        and '{} {}'.format(compound_type, next_cursor.spelling) == next_cursor.underlying_typedef_type.spelling):
        return next_cursor.spelling
    
        
def apply(children, visitor):
    lookahead_children = pairwise(children)
    for child, next_child in lookahead_children:
        if child.kind == CursorKind.TRANSLATION_UNIT:
            filename = child.spelling
            visitor.on_file_begin(filename)

            CLANG_DEFAULT_ENTITIES = ('__int128_t', '__uint128_t', '__builtin_va_list')
            children = (c for c in child.get_children() if c.spelling not in CLANG_DEFAULT_ENTITIES)
            apply(children, visitor)
            visitor.on_file_end()

        if child.kind == CursorKind.NAMESPACE and child.get_children():
            visitor.on_namespace_begin(child.spelling)
            apply(child.get_children(), visitor)
            visitor.on_namespace_end(child.spelling)

        elif child.kind == CursorKind.TYPEDEF_DECL:
            visitor.on_typedef(child.spelling, child.underlying_typedef_type.spelling)

        elif child.kind == CursorKind.ENUM_DECL:
            enum_typename = child.spelling
            enum_constants = [(c.spelling, c.enum_value)
                              for c in child.get_children()
                              if c.kind == CursorKind.ENUM_CONSTANT_DECL]
            if enum_constants:
                visitor.on_enum(enum_typename, enum_constants)

        elif child.kind == CursorKind.VAR_DECL and is_const_int(child.type):
            visitor.on_const_int(child.spelling, get_literal(child))

        elif child.kind == CursorKind.MACRO_DEFINITION:
            name = child.spelling
            if not name.startswith('_') and name not in ('OBJC_NEW_PROPERTIES',):
                visitor.on_macro_value(name, get_literal(child))

        elif child.kind in (CursorKind.STRUCT_DECL, CursorKind.CLASS_DECL):
            compound_name = 'struct' if child.kind == CursorKind.STRUCT_DECL else 'class'
            name = child.spelling
            typedef = False
            if not name:
                name = get_compound_typedef_name(compound_name, next_child)
                if name:
                    typedef = True
                    next(lookahead_children)
                else:
                    continue # discard struct with no name
                
            if child.type.is_pod():
                visitor.on_pod_begin(compound_name, name, typedef)
                apply(child.get_children(), visitor)
                visitor.on_pod_end(name)
            else:
                visitor.on_class_begin(compound_name, name, typedef)
                apply(child.get_children(), visitor)
                visitor.on_class_end(name)

        elif child.kind == CursorKind.FIELD_DECL:
            if child.access_specifier.name != 'PRIVATE':
                name = child.spelling
                visitor.on_field(name, child.type.spelling)

        elif child.kind == CursorKind.CXX_METHOD:
            if child.access_specifier.name != 'PRIVATE':
                name = child.spelling
                access = child.access_specifier.name.lower()
                return_type = child.result_type.spelling
                parameters = [(i.type.spelling, i.spelling) for i in child.get_arguments()]
                method_type = ''
                if child.is_static_method():
                    method_type = 'static'
                elif child.is_pure_virtual_method():
                    method_type = 'pure'
                elif child.is_virtual_method():
                    method_type = 'virtual'
                visitor.on_method(name, return_type, parameters, access, method_type)
                
        elif child.kind == CursorKind.FUNCTION_DECL:
            name = child.spelling
            return_type = child.result_type.spelling
            parameters = [(i.type.spelling, i.spelling) for i in child.get_arguments()]
            visitor.on_function(name, return_type, parameters)
            
        elif child.kind == CursorKind.CONSTRUCTOR:
            name = child.spelling
            parameters = [(i.type.spelling, i.spelling) for i in child.get_arguments()]        
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
        
        
class BaseVisitor(object):
    INDENT = '    '        
    def __init__(self, name, directory, time=None):
        if time is None:
            self.time = datetime.now()

        self.name = name
        if not time:
            self.time = datetime.now()
        self.directory = directory
        self.indent_level = 0
        self.file = None
        self.content_after_begin = False        
        self.banner = 'Generated by cppython v{} at {} for {} module'.format(__version__, self.time.isoformat(), self.name)
        
    def writeline(self, line='', *l, **kw):
        self.file.write(''.join((self.indent_level*self.INDENT, line.format(*l, **kw), '\n')))
    
    def reset_indent(self, level=0):
        if level == 0:
            level = -self.indent_level

        if level < 0:
            self.writeline()
        self.indent_level = max(0, self.indent_level+level)
        


@contextmanager        
def indent(visitor):
    visitor.reset_indent(1)
    try:
        yield
    finally:
        visitor.reset_indent(-1)
        
        
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
        self.file = open(name, 'w')
        self.header_file_path = os.path.relpath(filename, self.directory)
        
        self.writeline("'''{}'''", self.banner)
        self.writeline('from libcpp cimport bool')
        self.writeline('from cpython.ref cimport PyObject')
        self.writeline('cdef extern from "{}" nogil:', self.header_file_path)
        self.reset_indent(1)
        self.content_after_begin = False
        
    def on_file_end(self):
        if not self.content_after_begin:
            self.writeline('pass')
        self.file.close()
        
    def on_namespace_begin(self, namespace):
        self.namespaces.append(namespace)
        self.writeline('cdef extern from "{}" namespace "{}" nogil:',
                       self.header_file_path, '::'.join(self.namespaces))
        self.reset_indent(1)
        self.content_after_begin = False
        
    def on_namespace_end(self, namespace):
        if not self.content_after_begin:
            self.writeline('pass')
        self.reset_indent(-1)
        self.namespaces.pop()
        self.content_after_begin = True
        
    def on_typedef(self, name, typename):
        self.writeline('ctypedef {} {}', typename, name)
        self.content_after_begin = True
        
    def on_enum(self, name, constants):
        self.writeline()
        self.writeline('cdef enum {}:', name)
        with indent(self):
            for k, v in constants:
                self.writeline('{} = {}', k, v)
                # self.writeline('{}', k)
        self.content_after_begin = True
        
    def on_const_int(self, name, value):
        self.writeline('cdef enum: {} = {}', name, value)
        # self.writeline('cdef enum: {}', name)        
        self.content_after_begin = True        
        
    def on_macro_value(self, name, value):
        # Macro should not be export, otherwise will failed 
        pass
        
    def on_pod_begin(self, kind, name, typedef):
        self.content_after_begin = False
        self.writeline()
        define = 'ctypedef' if typedef else 'cdef'
        self.writeline('{} {} {}:', define, kind, name)
        self.reset_indent(1)
        
    def on_pod_end(self, name):
        if not self.content_after_begin:
            self.writeline('pass')
        self.reset_indent(-1)
        self.content_after_begin = True        
        
    def on_class_begin(self, kind, name, typedef):
        self.class_name = name
        self.writeline('cdef cppclass {}:', name)
        with indent(self):
            self.writeline('pass')        
        
    def on_class_end(self, name):
        self.class_name = None
        
    def on_field(self, name, typename):
        self.writeline('{} {}', typename, name)
        self.content_after_begin = True
        
    def on_constructor(self, name, parameters):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type):        
        pass
        
    def on_function(self, name, return_type, parameters):
        # parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
        parameters_list = ', '.join('{} {}'.format(split_namespace_name(t)[0], n) for (t, n) in parameters)        
        return_name, namespaces = split_namespace_name(return_type)
        self.writeline('cdef {} {}({}) nogil except +', return_name, name, parameters_list)
        
         
        
        
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
        
    def on_file_begin(self, filename):
        # TODO Add file header
        
        self.file = open(os.path.join(self.directory, self.name+'_cppython.pxd'), 'w')
        self.header_file_path = self.name+'_cppython.hpp'
        self.import_name = os.path.basename(os.path.splitext(filename)[0])
        
        self.writeline("'''{}'''", self.banner)
        self.writeline('from libcpp cimport bool')
        self.writeline('from cpython.ref cimport PyObject')
        self.writeline('cimport {}', self.import_name)        
        self.writeline('cdef extern from "{}" nogil:', self.header_file_path)
        self.reset_indent(1)
        self.content_after_begin = False
        
    def on_file_end(self):
        if not self.content_after_begin:
            self.writeline('pass')
        self.file.close()
        
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
        pass
        
    def on_pod_end(self, name):
        pass
        
    def on_class_begin(self, kind, name, typedef):
        self.class_names.add(name)
        self.class_name = get_proxy_name(name)
        self.writeline('cdef cppclass {}({}.{}):', self.class_name, self.import_name, name)
        self.reset_indent(1)
        
    def on_constructor(self, name, parameters):
        self.constructors.add(name)
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        self.writeline('{}(PyObject* self_object, {})', self.class_name, parameters_list)
        
        
    def get_use_type(self, typename):
        class_name = typename.split()[0]
        if class_name in self.class_names:
            return typename.replace(class_name, '{}.{}'.format(self.import_name, class_name))
            
        return typename
        
        
    def on_class_end(self, name):
        if name not in self.constructors:
            self.writeline('{}(PyObject* self_object)', self.class_name)
        self.class_name = None
        self.reset_indent(-1)
        
    def on_field(self, name, typename):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type):        
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
        return_name, namespaces = split_namespace_name(return_type)
        
        self.writeline('{} {}({}) except +', return_name, name, parameters_list)
        
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
        self.file = open(os.path.join(self.directory, self.name+'.pyx'), 'w')
        self.import_name = os.path.splitext(os.path.basename(filename))[0]
        self.import_proxy_name = self.name + '_cppython'
        
        self.writeline('# distutils: language = c++')
        self.writeline("'''{}'''", self.banner)
        self.writeline('cimport {}', self.import_name)
        self.writeline('cimport {}', self.import_proxy_name)
        self.writeline('cimport libc.string')
        self.writeline('from libcpp cimport bool')
        self.writeline('from cpython.ref cimport PyObject')

        # self.writeline('from cython cimport view')
        self.writeline('import enum # for python 2.x install enum34 package')
        self.writeline()
        
    def on_file_end(self):
        self.writeline('include "{}"', os.path.basename(self.file.name.replace('.pyx', '.pxi')))
        self.file.close()
        
    def on_namespace_begin(self, namespace):
        pass
        
    def on_namespace_end(self, namespace):
        pass
        
    def on_typedef(self, name, typename):
        self.types[name] = typename
        
    def on_enum(self, name, constants):
        self.writeline()
        self.writeline('class {}(enum.IntEnum):', name)
        with indent(self):
            for name, value in constants:
                self.writeline('{} = {}.{}', name, self.import_name, name)
        
    def on_const_int(self, name, value):
        self.writeline('{} = {}.{}', name, self.import_name, name)
        
    def on_macro_value(self, name, value):
        self.writeline('{} = {}', name, value)
        
    def on_pod_begin(self, kind, name, typedef):
        self.pod_types.add(name)
        self.writeline('cdef class {}:', name)
        self.reset_indent(1)
        self.writeline('cdef {}.{} _this', self.import_name, name)
        self.writeline('cdef _from_c_(self, {}.{} c_value):', self.import_name, name)
        with indent(self):
            self.writeline('self._this = c_value')
            self.writeline('return self')            
            
    def on_pod_end(self, name):
        self.reset_indent(-1)
        
        
    def on_class_begin(self, kind, name, typedef):
        self.class_types.add(name)
        self.writeline('cdef class {}:', name)
        self.reset_indent(1)
        
        proxy_name = get_proxy_name(name)
        self.writeline('cdef {}.{}* _this', self.import_proxy_name, proxy_name)
        self.writeline()
            
        self.writeline('def __dealloc__(self):')
        with indent(self):
            self.writeline('del self._this')
            
            
    def on_constructor(self, name, parameters):
        self.constructors.add(name)
        proxy_name = get_proxy_name(name)        
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(self.get_use_type(t), n) for (t, n) in parameters)
        parameters_names = ', '.join(self.get_use_format(t, n) for (t, n) in parameters)
        
        self.writeline('def __init__(self, {}):', parameters_list)
        with indent(self):
            self.writeline('self._this = new {}.{}(<PyObject*>(self), {})',
                           self.import_proxy_name, proxy_name, parameters_names)
        
    def on_class_end(self, name):
        if name not in self.constructors:
            proxy_name = get_proxy_name(name)            
            self.writeline('def __cinit__(self):')
            with indent(self):
                self.writeline('self._this = new {}.{}(<PyObject*>(self))',
                               self.import_proxy_name, proxy_name)
            
        self.writeline('pass')
        self.reset_indent(-1)
        
    def is_char_array(self, typename):
        return re.match(r'char \[\d+\]', self.types.get(typename, typename)) is not None
        
    def on_field(self, name, typename):
        self.writeline('property {}:', name)
        with indent(self):
            if self.is_char_array(typename):
                self.writeline('def __get__(self):')
                with indent(self):
                    self.writeline('return bytes(self._this.{})[:sizeof(self._this.{})]', name, name)
                self.writeline('def __set__(self, value):')
                with indent(self):
                    self.writeline('cdef int length = min(sizeof(self._this.{}), len(value))', name)
                    self.writeline('libc.string.memcpy(self._this.{}, <char*>(value), length)',name)
            else:
                self.writeline('def __get__(self):')
                with indent(self):
                    self.writeline('return self._this.{}', name)
                self.writeline('def __set__(self, value):')
                with indent(self):
                    self.writeline('self._this.{} = value', name)
        
                    
    def on_method(self, name, return_type, parameters, access, method_type):        
        # remove namespace and reference
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = 'self, ' + ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
        parameters_names = ', '.join(self.get_use_format(t, n) for (t, n) in parameters)
        return_name, namespaces = split_namespace_name(return_type)
            
        self.writeline('def {}({}):', name, parameters_list)
        with indent(self):
            if return_name in self.pod_types:
                self.writeline('return {}()._from_c_(self._this..{}({}))', return_name, name, parameters_names)
            else:
                return_ = 'return '
                if return_name == 'void':
                    return_= ''
                self.writeline('{}self._this.{}({})', return_, name, parameters_names)                
        
                
    def get_use_format(self, typename, name):
        if typename in self.pod_types:
            return '{}._this'.format(name)

        class_name = typename.split()[0]
        if class_name in self.class_types:
            # return '<{}.{}*>({}._this)'.format(self.import_name, class_name, name)
            return '{}._this'.format(name)            
        return name
                    
        
    def get_use_type(self, typename):
        class_name = typename.split()[0]
        if typename.split()[0] in self.class_types:
            return class_name

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
        self.writeline('cpdef {}({}):', name, parameters_list)
        
        with indent(self):
            if return_name in self.pod_types:
                self.writeline('return {}()._from_c_({}.{}({}))', return_name, self.import_name, name, parameters_names)
            else:
                return_ = 'return '
                if return_name == 'void':
                    return_= ''
                self.writeline('{}{}.{}({})', return_, self.import_name, name, parameters_names)                
        
            

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
        
        self.file = open(os.path.join(self.directory, self.name + '_cppython.hpp'), 'w')
        self.header_file_path = os.path.relpath(filename, self.directory)
        
        stem = os.path.splitext(os.path.basename(filename))[0]
        self.header_guard = '_{}_CPPYTON_HPP_'.format(stem.upper())
        self.writeline("// {}", self.banner)
        self.writeline('#ifndef {}', self.header_guard)
        self.writeline('#define {}', self.header_guard)
        self.writeline()                
        self.writeline('#include "{}"', self.header_file_path)
        self.writeline()        
        self.file.write('''
struct _object;
typedef _object PyObject;

class CppythonProxyBase
{
protected:    
    CppythonProxyBase(PyObject* self);
    ~CppythonProxyBase();
    
    PyObject* Self() const
    {
        return self_;
    }

private:
    PyObject* const self_;
};

''')
        
    def on_file_end(self):
        self.writeline('')
        self.writeline('#endif//{}', self.header_guard)
        self.file.close()
        
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
        self.writeline('class {} : public CppythonProxyBase, public {}',
                       self.class_name, base_class_full_name)
        self.writeline('{{')
        self.writeline('public:')
        self.reset_indent(1)
        self.writeline('typedef {} BaseClassType;', base_class_full_name);
        
    def on_constructor(self, name, parameters):
        self.constructors.add(name)
        parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in [('PyObject*', 'object')] + parameters)
        parameters_name = ', '.join(n for (t, n) in parameters)
        self.writeline('{}({})', self.class_name, parameters_list)
        self.writeline('    : CppythonProxyBase(object)')
        self.writeline('    , BaseClassType({})', parameters_name)        
        self.writeline('{{')
        self.writeline('}}')
        self.writeline()
        
    def on_class_end(self, name):
        if name not in self.constructors:
            self.writeline('{}(PyObject* object)', self.class_name)
            self.writeline('    : CppythonProxyBase(object)')
            self.writeline('{{')
            self.writeline('}}')
            self.writeline()
        
        self.reset_indent(-1)
        self.writeline('}};')
        self.writeline()
        self.class_name = None
        
    def on_field(self, name, typename):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type):        
        if method_type in ('pure', 'virtual'):
            parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
            self.writeline('{} {}({});', return_type, name, parameters_list)
        
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
        
        self.file = open(os.path.join(self.directory, self.name+'_cppython.cpp'), 'w')
        self.header_file_path = self.name+'_cppython.hpp'
        
        stem = os.path.basename(os.path.splitext(filename)[0])
        self.writeline("// {}", self.banner)
        self.writeline('#include "{}"', self.header_file_path)
        self.writeline('#include "{}_api.h"', self.name)
        self.file.write('''
#include <Python.h>
#include <stdexcept>

CppythonProxyBase::CppythonProxyBase(PyObject* self)
    : self_(self)
{
    if (self_ == NULL) {
        throw std::runtime_error("self object is NULL");
    }
    if (import_%s()) {
        throw std::runtime_error("could not import python extension module");
    } 
    Py_XINCREF(self_);
}

CppythonProxyBase::~CppythonProxyBase()
{
    Py_XDECREF(self_);
}

''' % self.name)
        
    def on_file_end(self):
        self.file.close()
        
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
        
    def on_method(self, name, return_type, parameters, access, method_type):        
        if method_type in ('pure', 'virtual'):
            parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
            parameters_name = ', '.join(n for (t, n) in parameters)
            parameters_name_for_proxy = ''
            if parameters_name:
                parameters_name_for_proxy = ', ' + parameters_name
            self.writeline('{} {}::{}({})', return_type, self.class_name, name, parameters_list)
            self.writeline('{{')
            with indent(self):
                self.writeline('bool overrided = cppython_has_method(this->Self(), (char*)"{}");', name)
                self.writeline('if (overrided) {{')
                with indent(self):
                    if return_type == 'void':
                        self.writeline('{}_{}_proxy_call(this->Self(){});',
                                       self.base_class_name, name, parameters_name_for_proxy)
                        
                        self.writeline('return;')
                    else:
                        self.writeline('return {}_{}_proxy_call(this->Self(){});',
                                       self.base_class_name, name, parameters_name_for_proxy)                    
                self.writeline('}}')
                if method_type == 'pure':
                    self.writeline('throw std::runtime_error("pure virtual method {}::{} not implemented");',
                                   self.class_name, name)
                else:
                    self.writeline('return BaseClassType::{}({});', name, parameters_name)
                
            self.writeline('}}')
            self.writeline()
        
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
        
    def on_file_begin(self, filename):
        # TODO Add file header
        self.file = open(os.path.join(self.directory, self.name+'.pxi'), 'w')

        self.writeline("'''{}'''", self.banner)        
        self.writeline('import types')
        self.writeline('cdef public api bool cppython_has_method(object self, const char* method_name):')
        with indent(self):
            self.writeline('method = getattr(self, method_name, None)')
            self.writeline('return isinstance(method, types.MethodType)')
        
    def on_file_end(self):
        self.file.close()
        
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
        self.class_name = name
        
    def on_class_end(self, name):
        self.class_name = None
        
    def on_field(self, name, typename):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type):        
        if method_type not in ('virtual', 'pure'):
            return
            
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
        parameters_names = ', '.join(self.get_use_format(t, n) for (t, n) in parameters)
        return_name, namespaces = split_namespace_name(return_type)
        
        parameters_list = ', '.join(['object self', parameters_list])
        self.writeline('cdef public api {} {}_{}_proxy_call({}):',
                       return_name, self.class_name,
                       name, parameters_list)
        
        return_ = '' if return_name == 'void' else 'return '
        with indent(self):
            self.writeline('method = getattr(self, "{}", None)', name)
            self.writeline('{}method({})', return_, parameters_names)
            
    def on_function(self, name, return_type, parameters):
        pass
        
    def on_constructor(self, name, parameters):
        pass
        
        
class SetupVisitor(BaseVisitor):
    '''Generate setup file for building python extension
    '''
    
    def __init__(self, name, directory='.', sources=None, time=None):
        super(SetupVisitor, self).__init__(name, directory, time)
        self.file = open(os.path.join(self.directory, 'setup.py'), 'w')
        self.sources = []
        if sources:
            self.sources = sources
        
        self.sources = [os.path.relpath(i, self.directory) for i in self.sources]
            
    def on_file_begin(self, filename):
        self.filename = filename
        
    def on_file_end(self):
        self.writeline('''#! /usr/bin/env python
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
        include_dirs = [],
        libraries = [],
        library_dirs = []),
]

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.append('build_ext')
        sys.argv.append('--inplace')
    
    setup(ext_modules=cythonize(extensions))
''', self.banner, self.name, self.name, self.name, ', '.join("'{}'".format(i) for i in self.sources))
        self.file.close()
        
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
        pass
        
    def on_pod_end(self, name):
        pass
        
    def on_class_begin(self, kind, name, typedef):
        pass
        
    def on_class_end(self, name):
        pass
        
    def on_field(self, name, typename):
        pass
        
    def on_method(self, name, return_type, parameters, access, method_type):        
        pass
            
    def on_function(self, name, return_type, parameters):
        pass
        
    def on_constructor(self, name, parameters):
        pass
        
        
def main(argv):
    if len(argv) <= 2:
        print 'cppython input-c++-header-file <additonal c++ source file> output/path/to/module/name'
        return

    hpp_path = argv[1]
    module_name = os.path.basename(argv[-1])
    directory = os.path.dirname(argv[-1])
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    cpp_files = argv[2:-1]
    
    tu = parse_cpp_file(hpp_path)
    visitors = [v(module_name, directory) for v in
                (PxdVisitor, PyxVisitor, CppVisitor, HppVisitor, PxiVisitor, PxdProxyVisitor)]
    visitors.append(SetupVisitor(module_name, directory, cpp_files))
    apply([tu.cursor], VisitorGroup(visitors))
    print 'done.'
        
if __name__ == '__main__':
    main(sys.argv)
