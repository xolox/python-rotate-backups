#!/usr/bin/env python

# Setup script for the `rotate-backups' package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 3, 2014
# URL: https://github.com/xolox/python-rotate-backups

"""
Setup script for the ``rotate-backups`` package.

**python setup.py install**
  Install from the working directory into the current Python environment.

**python setup.py sdist**
  Build a source distribution archive.
"""

import re
from os.path import abspath, dirname, join
from setuptools import setup

# Find the directory where the source distribution was unpacked.
source_directory = dirname(abspath(__file__))

# Find the current version.
module = join(source_directory, 'rotate_backups.py')
for line in open(module):
    match = re.match(r'^__version__\s*=\s*["\']([^"\']+)["\']$', line)
    if match:
        version_string = match.group(1)
        break
else:
    raise Exception("Failed to extract version from rotate_backups.py!")

# Fill in the long description (for the benefit of PyPi)
# with the contents of README.rst (rendered by GitHub).
readme_file = join(source_directory, 'README.rst')
readme_text = open(readme_file, 'r').read()

setup(name='rotate-backups',
      version=version_string,
      description="Simple command line interface for backup rotation",
      long_description=readme_text,
      url='https://github.com/xolox/python-rotate-backups',
      author='Peter Odding',
      author_email='peter@peterodding.com',
      py_modules=['rotate_backups'],
      entry_points=dict(console_scripts=[
          'rotate-backups = rotate_backups:main'
      ]),
      install_requires=[
          'coloredlogs >= 0.5',
          'executor >= 1.3',
          'naturalsort >= 1.2.1',
          'python-dateutil >= 2.2',
      ],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX',
          'Operating System :: Unix',
          'Topic :: System :: Archiving :: Backup',
          'Topic :: System :: Systems Administration',
      ])
