Changelog
=========

The purpose of this document is to list all of the notable changes to this
project. The format was inspired by `Keep a Changelog`_. This project adheres
to `semantic versioning`_.

.. contents::
   :local:

.. _Keep a Changelog: http://keepachangelog.com/
.. _semantic versioning: http://semver.org/

`Release 7.0`_ (2020-02-12)
---------------------------

**Significant changes:**

- Sanity checks are done to ensure the directory with backups exists, is
  readable and is writable. However `#18`_ made it clear that such sanity
  checks can misjudge the situation, which made me realize an escape hatch
  should be provided. The new ``--force`` option makes ``rotate-backups``
  continue even if sanity checks fail.

- Skip the sanity check that the directory with backups is writable when the
  ``--removal-command`` option is given (because custom removal commands imply
  custom semantics, see `#18`_ for an example).

**Miscellaneous changes:**

- Start testing on Python 3.7 and document compatibility.
- Dropped Python 2.6 (I don't think anyone still cares about this 😉).
- Copied Travis CI workarounds for MacOS from :pypi:`humanfriendly`.
- Updated ``Makefile`` to use Python 3 for local development.
- Bumped copyright to 2020.

.. _Release 7.0: https://github.com/xolox/python-rotate-backups/compare/6.0...7.0
.. _#18: https://github.com/xolox/python-rotate-backups/issues/18

`Release 6.0`_ (2018-08-03)
---------------------------

This is a bug fix release that changes the behavior of the program, and because
`rotate-backups` involves the deletion of important files I'm considering this
a significant change in behavior that deserves a major version bump...

It was reported in issue `#12`_ that filenames that match the filename pattern
but contain digits with invalid values for the year/month/day/etc fields would
cause a ``ValueError`` exception to be raised.

Starting from this release these filenames are ignored instead, although a
warning is logged to make sure the operator understands what's going on.

.. _Release 6.0: https://github.com/xolox/python-rotate-backups/compare/5.3...6.0
.. _#12: https://github.com/xolox/python-rotate-backups/issues/12

`Release 5.3`_ (2018-08-03)
---------------------------

- Merged pull request `#11`_ which introduces the ``--use-rmdir`` option with
  the suggested use case of removing CephFS snapshots.
- Replaced ``--use-rmdir`` with ``--removal-command=rmdir`` (more general).

.. _Release 5.3: https://github.com/xolox/python-rotate-backups/compare/5.2...5.3
.. _#11: https://github.com/xolox/python-rotate-backups/pull/11

`Release 5.2`_ (2018-04-27)
---------------------------

- Added support for filename patterns in configuration files (`#10`_).
- Bug fix: Skip human friendly pathname formatting for remote backups.
- Improved documentation using ``property_manager.sphinx`` module.

.. _Release 5.2: https://github.com/xolox/python-rotate-backups/compare/5.1...5.2
.. _#10: https://github.com/xolox/python-rotate-backups/issues/10

`Release 5.1`_ (2018-04-27)
---------------------------

- Properly document supported configuration options (`#7`_, `#8`_).
- Properly document backup collection strategy (`#8`_).
- Avoid ``u''`` prefixes in log output of include/exclude list processing.
- Added this changelog, restructured the online documentation.
- Added ``license`` key to ``setup.py`` script.

.. _Release 5.1: https://github.com/xolox/python-rotate-backups/compare/5.0...5.1
.. _#7: https://github.com/xolox/python-rotate-backups/issues/7
.. _#8: https://github.com/xolox/python-rotate-backups/issues/8

`Release 5.0`_ (2018-03-29)
---------------------------

The focus of this release is improved configuration file handling:

- Refactor configuration file handling (backwards incompatible). These changes
  are backwards incompatible because of the following change in semantics
  between the logic that was previously in `rotate-backups` and has since been
  moved to update-dotdee_:

  - Previously only the first configuration file that was found in a default
    location was loaded (there was a 'break' in the loop).

  - Now all configuration files in default locations will be loaded.

  My impression is that this won't bite any unsuspecting users, at least not in
  a destructive way, but I guess only time and a lack of negative feedback will
  tell :-p.

- Added Python 3.6 to supported versions.
- Include documentation in source distributions.
- Change theme of Sphinx documentation.
- Moved test helpers to ``humanfriendly.testing``.

.. _Release 5.0: https://github.com/xolox/python-rotate-backups/compare/4.4...5.0
.. _update-dotdee: https://update-dotdee.readthedocs.io/en/latest/

`Release 4.4`_ (2017-04-13)
---------------------------

Moved ``ionice`` support to executor_.

.. _Release 4.4: https://github.com/xolox/python-rotate-backups/compare/4.3.1...4.4
.. _executor: https://executor.readthedocs.io/en/latest/

`Release 4.3.1`_ (2017-04-13)
-----------------------------

Restore Python 2.6 compatibility by pinning `simpleeval` dependency.

While working on an unreleased Python project that uses `rotate-backups` I
noticed that the tox build for Python 2.6 was broken. Whether it's worth it for
me to keep supporting Python 2.6 is a valid question, but right now the readme
and setup script imply compatibility with Python 2.6 so I feel half obliged to
'fix this issue' :-).

.. _Release 4.3.1: https://github.com/xolox/python-rotate-backups/compare/4.3...4.3.1

`Release 4.3`_ (2016-10-31)
---------------------------

Added MacOS compatibility (`#6`_):

- Ignore ``stat --format=%m`` failures.
- Don't use ``ionice`` when not available.

.. _Release 4.3: https://github.com/xolox/python-rotate-backups/compare/4.2...4.3
.. _#6: https://github.com/xolox/python-rotate-backups/issues/6

`Release 4.2`_ (2016-08-05)
---------------------------

- Document default / alternative rotation algorithms (`#2`_, `#3`_, `#5`_).
- Implement 'minutely' option (`#5`_).

.. _Release 4.2: https://github.com/xolox/python-rotate-backups/compare/4.1...4.2
.. _#2: https://github.com/xolox/python-rotate-backups/issues/2
.. _#3: https://github.com/xolox/python-rotate-backups/issues/3
.. _#5: https://github.com/xolox/python-rotate-backups/issues/5

`Release 4.1`_ (2016-08-05)
---------------------------

- Enable choice for newest backup per time slot (`#5`_).
- Converted ``RotateBackups`` attributes to properties (I ❤ documentability :-).
- Renamed 'constructor' to 'initializer' where applicable.
- Simplified the ``rotate_backups.cli`` module a bit.

.. _Release 4.1: https://github.com/xolox/python-rotate-backups/compare/4.0...4.1
.. _#5: https://github.com/xolox/python-rotate-backups/issues/5

`Release 4.0`_ (2016-07-09)
---------------------------

Added support for concurrent backup rotation.

.. _Release 4.0: https://github.com/xolox/python-rotate-backups/compare/3.5...4.0

`Release 3.5`_ (2016-07-09)
---------------------------

- Use key properties on ``Location`` objects.
- Bring test coverage back up to >= 90%.

.. _Release 3.5: https://github.com/xolox/python-rotate-backups/compare/3.4...3.5

`Release 3.4`_ (2016-07-09)
---------------------------

Added support for expression evaluation for retention periods.

.. _Release 3.4: https://github.com/xolox/python-rotate-backups/compare/3.3...3.4

`Release 3.3`_ (2016-07-09)
---------------------------

Started using verboselogs_.

.. _Release 3.3: https://github.com/xolox/python-rotate-backups/compare/3.2...3.3
.. _verboselogs: https://verboselogs.readthedocs.io/

`Release 3.2`_ (2016-07-08)
---------------------------

- Added support for Python 2.6 :-P.

  By switching to the ``key_property`` support added in `property-manager` 2.0
  I was able to reduce code duplication and improve compatibility::

    6 files changed, 20 insertions(+), 23 deletions(-)

  This removes the dependency on ``functools.total_ordering`` and to the best
  of my knowledge this was the only Python >= 2.7 feature that I was using so
  out of curiosity I changed ``tox.ini`` to run the tests on Python 2.6 and
  indeed everything worked fine! :-)

- Refactored the makefile and ``setup.py`` script (checkers, docs, wheels,
  twine, etc).

.. _Release 3.2: https://github.com/xolox/python-rotate-backups/compare/3.1...3.2

`Release 3.1`_ (2016-04-13)
---------------------------

Implement relaxed rotation mode, adding a ``--relaxed`` option (`#2`_, `#3`_).

.. _Release 3.1: https://github.com/xolox/python-rotate-backups/compare/3.0...3.1
.. _#2: https://github.com/xolox/python-rotate-backups/issues/2
.. _#3: https://github.com/xolox/python-rotate-backups/issues/3

`Release 3.0`_ (2016-04-13)
---------------------------

- Support for backup rotation on remote systems.
- Added Python 3.5 to supported versions.
- Added support for ``-q``, ``--quiet`` command line option.
- Delegate system logging to coloredlogs.
- Improved ``rotate_backups.load_config_file()`` documentation.
- Use ``humanfriendly.sphinx`` module to generate documentation.
- Configured autodoc to order members based on source order.

Some backwards incompatible changes slipped in here, e.g. removing
``Backup.__init__()`` and renaming ``Backup.datetime`` to ``Backup.timestamp``.

In fact the refactoring that I've started here isn't finished yet, because the
separation of concerns between the ``RotateBackups``, ``Location`` and
``Backup`` classes doesn't make a lot of sense at the moment and I'd like to
improve on this. Rewriting projects takes time though :-(.

.. _Release 3.0: https://github.com/xolox/python-rotate-backups/compare/2.3...3.0

`Release 2.3`_ (2015-08-30)
---------------------------

Add/restore Python 3.4 compatibility.

It was always the intention to support Python 3 but a couple of setbacks made
it harder than just "flipping the switch" before now :-). This issue was
reported here: https://github.com/xolox/python-naturalsort/issues/2.

.. _Release 2.3: https://github.com/xolox/python-rotate-backups/compare/2.2...2.3

`Release 2.2`_ (2015-07-19)
---------------------------

Added support for configuration files.

.. _Release 2.2: https://github.com/xolox/python-rotate-backups/compare/2.1...2.2

`Release 2.1`_ (2015-07-19)
---------------------------

Bug fix: Guard against empty rotation schemes.

.. _Release 2.1: https://github.com/xolox/python-rotate-backups/compare/2.0...2.1

`Release 2.0`_ (2015-07-19)
---------------------------

Backwards incompatible: Implement a new Python API.

The idea is that this restructuring will make it easier to re-use (parts of)
the `rotate-backups` package in my other Python projects..

.. _Release 2.0: https://github.com/xolox/python-rotate-backups/compare/1.1...2.0

`Release 1.1`_ (2015-07-19)
---------------------------

Merged pull request `#1`_: Add include/exclude filters.

I made significant changes while merging this (e.g. the short option for
the include list and the use of shell patterns using the fnmatch module)
and I added tests to verify the behavior of the include/exclude logic.

.. _Release 1.1: https://github.com/xolox/python-rotate-backups/compare/1.0...1.1
.. _#1: https://github.com/xolox/python-rotate-backups/pull/1

`Release 1.0`_ (2015-07-19)
---------------------------

- Started working on a proper test suite.
- Split the command line interface from the Python API.
- Prepare for API documentation on Read The Docs.
- Switch from ``py_modules=[...]`` to ``packages=find_packages()`` in ``setup.py``.

.. _Release 1.0: https://github.com/xolox/python-rotate-backups/compare/0.1.2...1.0

`Release 0.1.2`_ (2015-07-15)
-----------------------------

- Bug fix for ``-y``, ``--yearly`` command line option mapping.
- Fixed some typos (in the README and a comment in ``setup.py``).

.. _Release 0.1.2: https://github.com/xolox/python-rotate-backups/compare/0.1.1...0.1.2

`Release 0.1.1`_ (2014-07-03)
-----------------------------

- Added missing dependency.
- Removed Sphinx-isms from README (PyPI doesn't like it, falls back to plain text).

.. _Release 0.1.1: https://github.com/xolox/python-rotate-backups/compare/0.1...0.1.1

`Release 0.1`_ (2014-07-03)
---------------------------

Initial commit (not very well tested yet).

.. _Release 0.1: https://github.com/xolox/python-rotate-backups/tree/0.1
