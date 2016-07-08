rotate-backups: Simple command line interface for backup rotation
=================================================================

.. image:: https://travis-ci.org/xolox/python-rotate-backups.svg?branch=master
   :target: https://travis-ci.org/xolox/python-rotate-backups

.. image:: https://coveralls.io/repos/xolox/python-rotate-backups/badge.svg?branch=master
   :target: https://coveralls.io/r/xolox/python-rotate-backups?branch=master

Backups are good for you. Most people learn this the hard way (including me).
Nowadays my Linux laptop automatically creates a full system snapshot every
four hours by pushing changed files to an `rsync`_ daemon running on the server
in my home network and creating a snapshot afterwards using the ``cp -al``
command (the article `Easy Automated Snapshot-Style Backups with Linux and
Rsync`_ explains the basic technique). The server has a second disk attached
which asynchronously copies from the main disk so that a single disk failure
doesn't wipe all of my backups (the "time delayed replication" aspect has also
proven to be very useful).

Okay, cool, now I have backups of everything, up to date and going back in
time! But I'm running through disk space like crazy... A proper deduplicating
filesystem would be awesome but I'm running crappy consumer grade hardware and
e.g. ZFS has not been a good experience in the past. So I'm going to have to
delete backups...

Deleting backups is never nice, but an easy and proper rotation scheme can help
a lot. I wanted to keep things manageable so I wrote a Python script to do it
for me. Over the years I actually wrote several variants. Because I kept
copy/pasting these scripts around I decided to bring the main features together
in a properly documented Python package and upload it to the `Python Package
Index`_.

The `rotate-backups` package is currently tested on cPython 2.6, 2.7, 3.4, 3.5
and PyPy (2.7).

.. contents::
   :local:

Features
--------

**Dry run mode**
  **Use it.** I'm serious. If you don't and `rotate-backups` eats more backups
  than intended you have no right to complain ;-)

**Flexible rotation**
  Rotation with any combination of hourly, daily, weekly, monthly and yearly
  retention periods.

**Fuzzy timestamp matching in filenames**
  The modification times of the files and/or directories are not relevant. If
  you speak Python regular expressions, here is how the fuzzy matching
  works::

   # Required components.
   (?P<year>\d{4}) \D?
   (?P<month>\d{2}) \D?
   (?P<day>\d{2}) \D?
   (
      # Optional components.
      (?P<hour>\d{2}) \D?
      (?P<minute>\d{2}) \D?
      (?P<second>\d{2})?
   )?

**All actions are logged**
  Log messages are saved to the system log (e.g. ``/var/log/syslog``) so you
  can retrace what happened when something seems to have gone wrong.

Installation
------------

The `rotate-backups` package is available on PyPI_ which means installation
should be as simple as:

.. code-block:: sh

   $ pip install rotate-backups

There's actually a multitude of ways to install Python packages (e.g. the `per
user site-packages directory`_, `virtual environments`_ or just installing
system wide) and I have no intention of getting into that discussion here, so
if this intimidates you then read up on your options before returning to these
instructions ;-).

Usage
-----

There are two ways to use the `rotate-backups` package: As the command line
program ``rotate-backups`` and as a Python API. For details about the Python
API please refer to the API documentation available on `Read the Docs`_. The
command line interface is described below.

Command line
~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `rotate-backups --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('rotate_backups.cli')
.. ]]]

**Usage:** `rotate-backups [OPTIONS] [DIRECTORY, ..]`

Easy rotation of backups based on the Python package by the same name.

To use this program you specify a rotation scheme via (a combination of) the ``--hourly``, ``--daily``, ``--weekly``, ``--monthly`` and/or ``--yearly`` options and the directory (or directories) containing backups to rotate as one or more positional arguments.

You can rotate backups on a remote system over SSH by prefixing a DIRECTORY with an SSH alias and separating the two with a colon (similar to how rsync accepts remote locations).

Instead of specifying directories and a rotation scheme on the command line you can also add them to a configuration file. For more details refer to the online documentation (see also the ``--config`` option).

Please use the ``--dry-run`` option to test the effect of the specified rotation scheme before letting this program loose on your precious backups! If you don't test the results using the dry run mode and this program eats more backups than intended you have no right to complain ;-).

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-H``, ``--hourly=COUNT``","Set the number of hourly backups to preserve during rotation:
   
   - If ``COUNT`` is a number it gives the number of hourly backups to preserve,
     starting from the most recent hourly backup and counting back in time.
   - Alternatively you can provide an expression that will be evaluated to get
     a number (e.g. if ``COUNT`` is ""7 \* 2"" the result would be 14).
   - You can also pass ""always"" for ``COUNT``, in this case all hourly backups are
     preserved.
   - By default no hourly backups are preserved."
   "``-d``, ``--daily=COUNT``","Set the number of daily backups to preserve during rotation. Refer to the
   usage of the ``-H``, ``--hourly`` option for details."
   "``-w``, ``--weekly=COUNT``","Set the number of weekly backups to preserve during rotation. Refer to the
   usage of the ``-H``, ``--hourly`` option for details."
   "``-m``, ``--monthly=COUNT``","Set the number of monthly backups to preserve during rotation. Refer to the
   usage of the ``-H``, ``--hourly`` option for details."
   "``-y``, ``--yearly=COUNT``","Set the number of yearly backups to preserve during rotation. Refer to the
   usage of the ``-H``, ``--hourly`` option for details."
   "``-I``, ``--include=PATTERN``","Only process backups that match the shell pattern given by ``PATTERN``. This
   argument can be repeated. Make sure to quote ``PATTERN`` so the shell doesn't
   expand the pattern before it's received by rotate-backups."
   "``-x``, ``--exclude=PATTERN``","Don't process backups that match the shell pattern given by ``PATTERN``. This
   argument can be repeated. Make sure to quote ``PATTERN`` so the shell doesn't
   expand the pattern before it's received by rotate-backups."
   "``-r``, ``--relaxed``","By default the time window for each rotation scheme is enforced (this is
   referred to as strict rotation) but the ``-r``, ``--relaxed`` option can be used
   to alter this behavior. The easiest way to explain the difference between
   strict and relaxed rotation is using an example:
   
   - When using strict rotation and the number of hourly backups to preserve
     is three, only backups created in the relevant time window (the hour of
     the most recent backup and the two hours leading up to that) will match
     the hourly frequency.
   
   - When using relaxed rotation the three most recent backups will all match
     the hourly frequency (and thus be preserved), regardless of the
     calculated time window.
   
   If the explanation above is not clear enough, here's a simple way to decide
   whether you want to customize this behavior or not:
   
   - If your backups are created at regular intervals and you never miss an
     interval then strict rotation (the default) is probably the best choice.
   
   - If your backups are created at irregular intervals then you may want to
     use the ``-r``, ``--relaxed`` option in order to preserve more backups."
   "``-i``, ``--ionice=CLASS``","Use the ""ionice"" program to set the I/O scheduling class and priority of
   the ""rm"" invocations used to remove backups. ``CLASS`` is expected to be one of
   the values ""idle"", ""best-effort"" or ""realtime"". Refer to the man page of
   the ""ionice"" program for details about these values."
   "``-c``, ``--config=PATH``","Load configuration from the pathname given by ``PATH``. If this option isn't
   given two default locations are checked: ""~/.rotate-backups.ini"" and
   ""/etc/rotate-backups.ini"". The first of these two configuration files to
   exist is loaded. For more details refer to the online documentation."
   "``-u``, ``--use-sudo``","Enable the use of ""sudo"" to rotate backups in directories that are not
   readable and/or writable for the current user (or the user logged in to a
   remote system over SSH)."
   "``-n``, ``--dry-run``","Don't make any changes, just print what would be done. This makes it easy
   to evaluate the impact of a rotation scheme without losing any backups."
   "``-v``, ``--verbose``",Make more noise (increase logging verbosity). Can be repeated.
   "``-q``, ``--quiet``",Make less noise (decrease logging verbosity). Can be repeated.
   "``-h``, ``--help``","Show this message and exit.
   "

.. [[[end]]]

Configuration files
~~~~~~~~~~~~~~~~~~~

Instead of specifying directories and rotation schemes on the command line you
can also add them to a configuration file.

By default two locations are checked for a configuration file, these are
``~/.rotate-backups.ini`` and ``/etc/rotate-backups.ini``. The first of these
that exists is loaded. You can load a configuration file in a nonstandard
location using the command line option ``--config``.

Configuration files use the familiar INI syntax. Each section defines a
directory that contains backups to be rotated. The options in each section
define the rotation scheme and other options. Here's an example based on how I
use `rotate-backups` to rotate the backups of the Linux installations that I
make regular backups of:

.. code-block:: ini

   # /etc/rotate-backups.ini:
   # Configuration file for the rotate-backups program that specifies
   # directories containing backups to be rotated according to specific
   # rotation schemes.

   [/backups/laptop]
   hourly = 24
   daily = 7
   weekly = 4
   monthly = 12
   yearly = always
   ionice = idle

   [/backups/server]
   daily = 7 * 2
   weekly = 4 * 2
   monthly = 12 * 4
   yearly = always
   ionice = idle

   [/backups/mopidy]
   daily = 7
   weekly = 4
   monthly = 2
   ionice = idle

   [/backups/xbmc]
   daily = 7
   weekly = 4
   monthly = 2
   ionice = idle

As you can see in the retention periods of the directory ``/backups/server`` in
the example above you are allowed to use expressions that evaluate to a number
(instead of having to write out the literal number).

Here's an example of a configuration for two remote directories:

.. code-block:: ini

   # SSH as a regular user and use `sudo' to elevate privileges.
   [server:/backups/laptop]
   use-sudo = yes
   hourly = 24
   daily = 7
   weekly = 4
   monthly = 12
   yearly = always
   ionice = idle

   # SSH as the root user (avoids sudo passwords).
   [server:/backups/server]
   ssh-user = root
   hourly = 24
   daily = 7
   weekly = 4
   monthly = 12
   yearly = always
   ionice = idle

As this example shows you have the option to connect as the root user or to
connect as a regular user and use ``sudo`` to elevate privileges.

Contact
-------

The latest version of `rotate-backups` is available on PyPI_ and GitHub_. The
documentation is hosted on `Read the Docs`_. For bug reports please create an
issue on GitHub_. If you have questions, suggestions, etc. feel free to send me
an e-mail at `peter@peterodding.com`_.

License
-------

This software is licensed under the `MIT license`_.

© 2016 Peter Odding.

.. External references:

.. _Easy Automated Snapshot-Style Backups with Linux and Rsync: http://www.mikerubel.org/computers/rsync_snapshots/
.. _GitHub: https://github.com/xolox/python-rotate-backups
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _per user site-packages directory: https://www.python.org/dev/peps/pep-0370/
.. _peter@peterodding.com: peter@peterodding.com
.. _PyPI: https://pypi.python.org/pypi/rotate-backups
.. _Python Package Index: https://pypi.python.org/pypi/rotate-backups
.. _Read the Docs: https://rotate-backups.readthedocs.org
.. _rsync: http://en.wikipedia.org/wiki/rsync
.. _virtual environments: http://docs.python-guide.org/en/latest/dev/virtualenvs/
