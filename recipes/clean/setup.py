# pylint: disable=C0103
"""Setup for pydrobert.kaldi"""

from __future__ import print_function

import os
import platform
import shlex
import sys

import numpy
import pkgconfig

from distutils.core import Extension
from distutils.core import setup

assert pkgconfig.exists('kaldi-base')
assert pkgconfig.exists('kaldi-matrix')
assert pkgconfig.exists('kaldi-thread')
assert pkgconfig.exists('kaldi-util')
assert pkgconfig.exists('kaldi-feat')
python_dir = os.path.abspath('python')
src_dir = os.path.abspath('src')
swig_include_dir = os.path.abspath('swig')

with open('README.rst') as f:
    readme_text = f.read()

kaldi_libraries = {
    'kaldi-base', 'kaldi-thread', 'kaldi-util', 'kaldi-matrix', 'kaldi-feat'}
kaldi_library_dirs = set()
kaldi_include_dirs = {numpy.get_include()}

# pkg-config returns in unicode, so we should cast in case of py2.7
kaldi_compiler_args = shlex.split(pkgconfig.cflags(
    'kaldi-util kaldi-matrix kaldi-base kaldi-thread kaldi-feat'))
define_symbols = set() # extract for swig
idx = 0
while idx < len(kaldi_compiler_args):
    if kaldi_compiler_args[idx][:2] == '-I':
        if len(kaldi_compiler_args[idx]) == 2:
            del kaldi_compiler_args[idx]
            kaldi_include_dirs.add(kaldi_compiler_args[idx])
        else:
            kaldi_include_dirs.add(kaldi_compiler_args[idx][2:])
        del kaldi_compiler_args[idx]
    elif kaldi_compiler_args[idx][:2] == '-D':
        define_symbols.add(kaldi_compiler_args[idx])
        idx += 1
    else:
        del kaldi_compiler_args[idx]
kaldi_linker_args = shlex.split(pkgconfig.libs(
    'kaldi-util kaldi-base kaldi-matrix kaldi-thread kaldi-feat'))
idx = 0
while idx < len(kaldi_linker_args):
    if kaldi_linker_args[idx][:2] == '-L':
        if len(kaldi_linker_args[idx]) == 2:
            del kaldi_linker_args[idx]
            kaldi_library_dirs.add(kaldi_linker_args[idx])
        else:
            kaldi_library_dirs.add(kaldi_linker_args[idx][2:])
        del kaldi_linker_args[idx]
    elif kaldi_linker_args[idx][:2] == '-l':
        kaldi_libraries.add(kaldi_linker_args[idx][2:])
        del kaldi_linker_args[idx]
    else:
        del kaldi_linker_args[idx]
# distutils doesn't like to set rpath, so we do it manually on OSX
if platform.system() == 'Darwin':
    assert len(kaldi_library_dirs) == 1
    kaldi_linker_args += ['-Wl,-rpath,' + kaldi_library_dirs.pop()]

swig_opts = ['-c++', '-builtin', '-Wall'] + list(define_symbols) + \
        ['-I' + swig_include_dir]
kaldi_compiler_args.append('-Wno-unused-variable') # kaldi-table-inl.h:501

kaldi_module = Extension(
    'pydrobert.kaldi._internal',
    sources=[os.path.join(swig_include_dir, 'pydrobert', 'kaldi.i')],
    libraries=list(kaldi_libraries),
    runtime_library_dirs=list(kaldi_library_dirs),
    include_dirs=list(kaldi_include_dirs),
    extra_compile_args=kaldi_compiler_args,
    extra_link_args=kaldi_linker_args,
    swig_opts=swig_opts,
)

setup(
    name='pydrobert-kaldi',
    ext_modules=[kaldi_module],
    namespace_packages=['pydrobert'],
    package_dir={'':python_dir},
    packages=['pydrobert', 'pydrobert.kaldi'],
    long_description=readme_text,
    py_modules=['pydrobert.kaldi.tables'],
)
