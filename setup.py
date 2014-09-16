#          Copyright Jamie Allsop 2014-2014
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          http://www.boost.org/LICENSE_1_0.txt)

#-------------------------------------------------------------------------------
#   setup.py
#-------------------------------------------------------------------------------

from setuptools import setup

try:
    import pypandoc
    read_markdown = lambda f: pypandoc.convert(f, 'rst')
except ImportError:
    print( "warning: pypandoc module not found, could not convert Markdown to RST" )
    read_markdown = lambda f: open(f, 'r').read()


setup(
    name             = 'cppscons',
    version          = '0.1',
    description      = 'cppscons, an extension package to simplify and extend Scons',
    author           = 'ja11sop',
    url              = 'https://github.com/ja11sop/cppscons',
    license          = 'LICENSE_1_0.txt',
    long_description = read_markdown('README.md'),
    packages         = [
        'cppscons',
        'cppscons.cpp',
        'cppscons.dependencies',
        'cppscons.methods',
        'cppscons.modules',
        'cppscons.platforms',
        'cppscons.profiles',
        'cppscons.project_generators',
        'cppscons.scms',
        'cppscons.toolchains',
        'cppscons.variants'
    ],
    install_requires = [ 'colorama', 'gcovr' ]
)