#!/usr/bin/env python3
# This file is part of the account_arba module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import io
import os
import re
from configparser import ConfigParser
from setuptools import setup


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


config = ConfigParser()
config.read_file(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
version = info.get('version', '0.0.1')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)
name = 'trytonar_account_arba'

download_url = 'https://github.com/tryton-ar/account_arba/tree/%s.%s' % (
    major_version, minor_version)

requires = []
for dep in info.get('depends', []):
    if dep == 'account_ar':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif not re.match(r'(ir|res)(\W|$)', dep):
        requires.append(get_require_version('trytond_%s' % dep))
requires.append(get_require_version('trytond'))
requires.append('M2Crypto>=0.22.3')
requires.append('Pillow>=2.8.1')
requires.append('httplib2')
requires.append('pyafipws')
requires.append('pysimplesoap')

tests_require = [get_require_version('proteus')]
dependency_links = [
    'https://github.com/tryton-ar/account_ar/tarball/%s.%s#egg=trytonar_account_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/reingart/pyafipws/tarball/py3k#egg=pyafipws',
    'https://github.com/pysimplesoap/pysimplesoap/tarball/stable_py3k#egg=pysimplesoap',
    ]

setup(name=name,
    version=version,
    description='Tryton module that integrates ARBA (Argentina).',
    long_description=read('README'),
    author='tryton-ar',
    url='https://github.com/tryton-ar/account_arba',
    download_url=download_url,
    package_dir={'trytond.modules.account_arba': '.'},
    packages=[
        'trytond.modules.account_arba',
        'trytond.modules.account_arba.tests',
        ],
    package_data={
        'trytond.modules.account_arba': (info.get('xml', [])
            + ['tryton.cfg', 'view/*.xml', 'locale/*.po']),
        },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        'Topic :: Office/Business :: Financial :: Accounting',
        ],
    license='GPL-3',
    python_requires='>=3.4',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    account_arba = trytond.modules.account_arba
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    )
