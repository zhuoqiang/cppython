#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''Bring C++ classes to python
'''

import sys
import os
import clang
import datetime
import ast
from datetime import datetime

from clang.cindex import *

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
        options=TranslationUnit.PARSE_INCOMPLETE|TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
    )
    return tu


def get_comment(cursor):
    # TODO add docstring from comment
    return cursor.brief_comment.strip().strip('/').strip()
    
    
def get_literal_value(cursor):
    for t in cursor.get_tokens():
        if t.kind == TokenKind.LITERAL:
            return ast.literal_eval(t.spelling)
            

def is_const_int(type):
    return type.is_const_qualified() and type.kind in (
        TypeKind.SHORT, TypeKind.INT, TypeKind.LONG, TypeKind.LONGLONG, TypeKind.INT128,
        TypeKind.USHORT, TypeKind.UINT, TypeKind.ULONG, TypeKind.ULONGLONG, TypeKind.UINT128)
            
            
def apply_cursor(child, visitor):
    if child.kind == CursorKind.NAMESPACE and child.get_children():
        visitor.on_namespace_begin(child.spelling)
        for c in child.get_children():
            apply_cursor(c, visitor)
        visitor.on_namespace_end(child.spelling)
        return

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
        visitor.on_const_int(child.spelling, get_literal_value(child))
        
    else:
        # print child.kind, child.spelling, child.type.spelling
        pass
        
    # for c in child.get_children():
    #     print c.kind, c.spelling, c.type.spelling
    
    
def apply(tu, visitor):
    cursor = tu.cursor
    filename = cursor.spelling
    visitor.on_file(filename)
    
    CLANG_DEFAULT_ENTITIES = ('__int128_t', '__uint128_t', '__builtin_va_list')
    children = (c for c in cursor.get_children() if c.spelling not in CLANG_DEFAULT_ENTITIES)
    for c in children:
        apply_cursor(c, visitor)
        


class VisitorGroup(object):
    def __init__(self, visitors):
        self.visitors = visitors

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
        
    def writeline(self, line='', *l, **kw):
        self.file.write(''.join((self.indent_level*self.INDENT, line.format(*l, **kw), '\n')))
    
    def reset_indent(self, level=0):
        if level == 0:
            level = -self.indent_level

        if level < 0:
            self.writeline()
        self.indent_level = max(0, self.indent_level+level)
        

class Indent():
    def __init__(self, obj):
        self.obj = obj
    def __enter__(self):
        self.obj.reset_indent(1)
    def __exit__(self, type, value, traceback):
        self.obj.reset_indent(-1)
        

class PxdVisitor(BaseVisitor):
    '''Generate pxd file exporting C++ header declaration in cython
    '''
    
    def __init__(self, directory='.', time=None):
        super(PxdVisitor, self).__init__(directory, time)
        self.namespaces = []
        
    def on_file(self, filename):
        self.file = open(generate_file_name(self.directory, filename, '.pxd'), 'w')
        self.header_file_path = os.path.relpath(filename, self.directory)
        
        self.writeline('cdef extern from "{}":', self.header_file_path)
        self.reset_indent(1)
        self.writeline('pass')
        
    def on_namespace_begin(self, namespace):
        self.namespaces.append(namespace)
        self.writeline('cdef extern from "{}" namespace "{}":',
                       self.header_file_path, '::'.join(self.namespaces))
        self.reset_indent(1)
        
    def on_namespace_end(self, namespace):
        self.writeline('pass')
        self.reset_indent(-1)
        
    def on_typedef(self, name, typename):
        self.writeline('ctypedef {} {}', typename, name)
        
    def on_enum(self, name, constants):
        self.writeline('cdef enum {}:', name)
        with Indent(self) as _:
            for k, v in constants:
                self.writeline('{} = {}', k, v)
        
    def on_const_int(self, name, value):
        self.writeline('cdef enum: {} = {}', name, value)
        
        
        
class PyxVisitor(BaseVisitor):
    '''Generate pyx file wrappering C++ entieis in cython
    '''
    
    def __init__(self, directory='.', time=None):
        super(PyxVisitor, self).__init__(directory, time)
        
    def on_file(self, filename):
        self.file = open(generate_file_name(self.directory, filename, '_proxy.pyx'), 'w')
        stem = os.path.splitext(os.path.basename(filename))[0]
        
        self.writeline('# distutils: language = c++')
        self.writeline('cimport {}', stem)
        
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
        
        
        
# class Visitor(object):
#     def __init__(self, directory='.'):
#         self.directory = directory

#     def on_file(self, filename):
#         stem = os.path.splitext(filename)[0]
        
#         self.pxd = open(os.path.join(self.directory, stem+'.pxd'), 'w')
#         self.pyx = open(os.path.join(self.directory, stem+'.pyx'), 'w'))
#         self.cpp = open(os.path.join(self.directory, stem+'_cppython_proxy.cpp'), 'w'))
#         self.hpp = open(os.path.join(self.directory, stem+'_cppython_proxy.hpp'), 'w'))
    
#         self.pyx.write('cimport')
        
        
        
if __name__ == '__main__':
    pass
