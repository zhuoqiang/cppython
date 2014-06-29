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
            name = child.spelling
            typedef = 'cdef '
            if not name:
                name = get_compound_typedef_name('struct', next_child)
                if name:
                    typedef = 'ctypedef '
                    next(lookahead_children) # discard typedef
                    pass
                else:
                    continue # discard struct with no name
                
            if child.type.is_pod():
                visitor.on_pod_begin('{}struct'.format(typedef), name)
                apply(child.get_children(), visitor)
                visitor.on_pod_end('{}struct'.format(typedef), name)
            else:
                # TOOD
                pass

        elif child.kind == CursorKind.FIELD_DECL:
            name = child.spelling
            visitor.on_field(name, child.type.spelling)

        elif child.kind == CursorKind.FUNCTION_DECL:
            name = child.spelling
            return_type = child.result_type.spelling
            parameters = [(i.type.spelling, i.spelling) for i in child.get_arguments()]
            visitor.on_function(name, return_type, parameters)
            
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
        
        
def generate_file_name(directory, base_file_name, extension):
    stem = os.path.splitext(os.path.basename(base_file_name))[0]
    return os.path.join(directory, stem+extension)
        
    
class BaseVisitor(object):
    INDENT = '    '        
    def __init__(self, directory='.', time=None):
        if time is None:
            time = datetime.now()

        self.time = time
        self.directory = directory
        self.indent_level = 0
        self.file = None
        self.content_after_begin = False        
        
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
    
    def __init__(self, directory='.', time=None):
        super(PxdVisitor, self).__init__(directory, time)
        self.namespaces = []
        self.content_after_begin = False
        
    def on_file_begin(self, filename):
        # TODO Add file header
        
        self.file = open(generate_file_name(self.directory, filename, '.pxd'), 'w')
        self.header_file_path = os.path.relpath(filename, self.directory)
        
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
        
    def on_pod_begin(self, kind, name):
        self.content_after_begin = False
        self.writeline()
        self.writeline('{} {}:', kind, name)
        self.reset_indent(1)
        
    def on_pod_end(self, kind, name):
        if not self.content_after_begin:
            self.writeline('pass')
        self.reset_indent(-1)
        self.content_after_begin = True        
        
    def on_field(self, name, typename):
        self.writeline('{} {}', typename, name)
        self.content_after_begin = True
        
        
    def on_function(self, name, return_type, parameters):
        # parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
        parameters_list = ', '.join('{} {}'.format(split_namespace_name(t)[0], n) for (t, n) in parameters)        
        return_name, namespaces = split_namespace_name(return_type)
        self.writeline('cdef {} {}({}) nogil', return_name, name, parameters_list)
        
        
class PyxVisitor(BaseVisitor):
    '''Generate pyx file wrappering C++ entieis in cython
    '''
    
    def __init__(self, directory='.', time=None):
        super(PyxVisitor, self).__init__(directory, time)
        self.types = {}
        self.pod_types = set()
        
    def on_file_begin(self, filename):
        # TODO Add file header
        self.file = open(generate_file_name(self.directory, filename, '_proxy.pyx'), 'w')
        self.import_name = os.path.splitext(os.path.basename(filename))[0]
        
        self.writeline('# distutils: language = c++')
        self.writeline('cimport {}', self.import_name)
        self.writeline('cimport libc.string')        
        self.writeline('import enum # for python 2.x install enum34 package')
        self.writeline()
        
    def on_file_end(self):
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
        
    def on_pod_begin(self, kind, name):
        self.pod_types.add(name)
        self.writeline('cdef class {}:', name)
        self.reset_indent(1)
        self.writeline('cdef {}.{} _this', self.import_name, name)
        self.writeline('cdef _from_c_(self, {}.{} c_value):', self.import_name, name)
        with indent(self):
            self.writeline('self._this = c_value')
            self.writeline('return self')            
            
    def on_pod_end(self, kind, name):
        self.reset_indent(-1)
        pass
        
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
        
                    
    def get_use_format(self, typename, name):
        if typename in self.pod_types:
            return '{}._this'.format(name)
        return name
                    
    def on_function(self, name, return_type, parameters):
        # remove namespace and reference
        parameters = [(split_namespace_name(t)[0], n) for (t, n) in parameters]
        parameters_list = ', '.join('{} {}'.format(t, n) for (t, n) in parameters)
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
        
            
if __name__ == '__main__':
    pass
