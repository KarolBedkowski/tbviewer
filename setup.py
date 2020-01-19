#!/usr/bin/python3
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

import tbviewer
import tbviewer.version

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    'License :: OSI Approved :: GNU General Public License (GPL)'
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Environment :: Win32 (MS Windows)",
    "Environment :: X11 Applications",
]

REQUIRES = [
    'setuptools',
    'tkinter',
]


setup(
    name='tbviewer',
    version=tbviewer.version.VERSION,
    description='tbviewer - Trekbuddy atlas/map viewer.',
    long_description=open("README.rst").read(),
    classifiers=CLASSIFIERS,
    author='Karol Będkowski',
    author_email='karol.bedkowski at gmail.com',
    url='',
    download_url='',
    license='GPL v3',
    py_modules=['tbviewer', 'tbviewer_dbg', 'tbcalibrate.py',
                'tbcalibrate_dbg.py'],
    packages=find_packages('.'),
    package_dir={'': '.'},
    include_package_data=True,
    install_requires=REQUIRES,
    entry_points="""
       [console_scripts]
       tbviewer = tbviewer.main:run
       tbcalibrate = tbviewer.main:run_calibrate
    """,
    zip_safe=True,
)
