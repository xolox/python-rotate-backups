#!/usr/bin/env python

# Setup script for the `rotate-backups' package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: April 13, 2016
# URL: https://github.com/xolox/python-rotate-backups

"""
Setup script for the ``rotate-backups`` package.

**python setup.py install**
  Install from the working directory into the current Python environment.

**python setup.py sdist**
  Build a source distribution archive.
"""

# Standard library modules.
import codecs
import os
import re

# De-facto standard solution for Python packaging.
from setuptools import setup, find_packages

# Find the directory where the source distribution was unpacked.
source_directory = os.path.dirname(os.path.abspath(__file__))

# Find the current version.
module = os.path.join(source_directory, 'rotate_backups', '__init__.py')
for line in open(module):
    match = re.match(r'^__version__\s*=\s*["\']([^"\']+)["\']$', line)
    if match:
        version_string = match.group(1)
        break
else:
    raise Exception("Failed to extract version from %s!" % module)

# Fill in the long description (for the benefit of PyPI)
# with the contents of README.rst (rendered by GitHub).
readme_file = os.path.join(source_directory, 'README.rst')
with codecs.open(readme_file, 'r', 'utf-8') as handle:
    readme_text = handle.read()

setup(name='rotate-backups',
      version=version_string,
      description="Simple command line interface for backup rotation",
      long_description=readme_text,
      url='https://github.com/xolox/python-rotate-backups',
      author='Peter Odding',
      author_email='peter@peterodding.com',
      packages=find_packages(),
      entry_points=dict(console_scripts=[
          'rotate-backups = rotate_backups.cli:main'
      ]),
      install_requires=[
          'coloredlogs >= 5.0',
          'executor >= 9.8',
          'humanfriendly >= 1.44.5',
          'naturalsort >= 1.4',
          'property-manager >= 1.3',
          'python-dateutil >= 2.2',
          'six >= 1.9.0',
      ],
      test_suite='rotate_backups.tests',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX',
          'Operating System :: Unix',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Software Development',
          'Topic :: System :: Archiving :: Backup',
          'Topic :: System :: Systems Administration',
      ])
