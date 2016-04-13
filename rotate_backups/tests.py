# Test suite for the `rotate-backups' Python package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: April 13, 2016
# URL: https://github.com/xolox/python-rotate-backups

"""Test suite for the `rotate-backups` package."""

# Standard library modules.
import logging
import os
import shutil
import sys
import tempfile
import unittest

# External dependencies.
import coloredlogs
from six.moves import configparser

# The module we're testing.
from rotate_backups import (
    RotateBackups,
    coerce_location,
    load_config_file,
)
from rotate_backups.cli import main

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

SAMPLE_BACKUP_SET = set([
    '2013-10-10@20:07', '2013-10-11@20:06', '2013-10-12@20:06', '2013-10-13@20:07', '2013-10-14@20:06',
    '2013-10-15@20:06', '2013-10-16@20:06', '2013-10-17@20:07', '2013-10-18@20:06', '2013-10-19@20:06',
    '2013-10-20@20:05', '2013-10-21@20:07', '2013-10-22@20:06', '2013-10-23@20:06', '2013-10-24@20:06',
    '2013-10-25@20:06', '2013-10-26@20:06', '2013-10-27@20:06', '2013-10-28@20:07', '2013-10-29@20:06',
    '2013-10-30@20:07', '2013-10-31@20:07', '2013-11-01@20:06', '2013-11-02@20:06', '2013-11-03@20:05',
    '2013-11-04@20:07', '2013-11-05@20:06', '2013-11-06@20:07', '2013-11-07@20:07', '2013-11-08@20:07',
    '2013-11-09@20:06', '2013-11-10@20:06', '2013-11-11@20:07', '2013-11-12@20:06', '2013-11-13@20:07',
    '2013-11-14@20:06', '2013-11-15@20:07', '2013-11-16@20:06', '2013-11-17@20:07', '2013-11-18@20:07',
    '2013-11-19@20:06', '2013-11-20@20:07', '2013-11-21@20:06', '2013-11-22@20:06', '2013-11-23@20:07',
    '2013-11-24@20:06', '2013-11-25@20:07', '2013-11-26@20:06', '2013-11-27@20:07', '2013-11-28@20:06',
    '2013-11-29@20:07', '2013-11-30@20:06', '2013-12-01@20:07', '2013-12-02@20:06', '2013-12-03@20:07',
    '2013-12-04@20:07', '2013-12-05@20:06', '2013-12-06@20:07', '2013-12-07@20:06', '2013-12-08@20:06',
    '2013-12-09@20:07', '2013-12-10@20:06', '2013-12-11@20:07', '2013-12-12@20:07', '2013-12-13@20:07',
    '2013-12-14@20:06', '2013-12-15@20:06', '2013-12-16@20:07', '2013-12-17@20:06', '2013-12-18@20:07',
    '2013-12-19@20:07', '2013-12-20@20:08', '2013-12-21@20:06', '2013-12-22@20:07', '2013-12-23@20:08',
    '2013-12-24@20:07', '2013-12-25@20:07', '2013-12-26@20:06', '2013-12-27@20:07', '2013-12-28@20:06',
    '2013-12-29@20:07', '2013-12-30@20:07', '2013-12-31@20:06', '2014-01-01@20:07', '2014-01-02@20:07',
    '2014-01-03@20:08', '2014-01-04@20:06', '2014-01-05@20:07', '2014-01-06@20:07', '2014-01-07@20:06',
    '2014-01-08@20:09', '2014-01-09@20:07', '2014-01-10@20:07', '2014-01-11@20:06', '2014-01-12@20:07',
    '2014-01-13@20:07', '2014-01-14@20:07', '2014-01-15@20:06', '2014-01-16@20:06', '2014-01-17@20:04',
    '2014-01-18@20:02', '2014-01-19@20:02', '2014-01-20@20:04', '2014-01-21@20:04', '2014-01-22@20:04',
    '2014-01-23@20:05', '2014-01-24@20:08', '2014-01-25@20:03', '2014-01-26@20:02', '2014-01-27@20:08',
    '2014-01-28@20:07', '2014-01-29@20:07', '2014-01-30@20:08', '2014-01-31@20:04', '2014-02-01@20:05',
    '2014-02-02@20:03', '2014-02-03@20:05', '2014-02-04@20:06', '2014-02-05@20:07', '2014-02-06@20:06',
    '2014-02-07@20:05', '2014-02-08@20:06', '2014-02-09@20:04', '2014-02-10@20:07', '2014-02-11@20:07',
    '2014-02-12@20:07', '2014-02-13@20:06', '2014-02-14@20:06', '2014-02-15@20:05', '2014-02-16@20:04',
    '2014-02-17@20:06', '2014-02-18@20:04', '2014-02-19@20:08', '2014-02-20@20:06', '2014-02-21@20:07',
    '2014-02-22@20:05', '2014-02-23@20:06', '2014-02-24@20:05', '2014-02-25@20:06', '2014-02-26@20:04',
    '2014-02-27@20:05', '2014-02-28@20:03', '2014-03-01@20:04', '2014-03-02@20:01', '2014-03-03@20:05',
    '2014-03-04@20:06', '2014-03-05@20:05', '2014-03-06@20:24', '2014-03-07@20:03', '2014-03-08@20:04',
    '2014-03-09@20:01', '2014-03-10@20:05', '2014-03-11@20:05', '2014-03-12@20:05', '2014-03-13@20:05',
    '2014-03-14@20:04', '2014-03-15@20:04', '2014-03-16@20:02', '2014-03-17@20:04', '2014-03-18@20:06',
    '2014-03-19@20:06', '2014-03-20@20:06', '2014-03-21@20:04', '2014-03-22@20:03', '2014-03-23@20:01',
    '2014-03-24@20:03', '2014-03-25@20:05', '2014-03-26@20:03', '2014-03-27@20:04', '2014-03-28@20:03',
    '2014-03-29@20:03', '2014-03-30@20:01', '2014-03-31@20:04', '2014-04-01@20:03', '2014-04-02@20:05',
    '2014-04-03@20:03', '2014-04-04@20:04', '2014-04-05@20:02', '2014-04-06@20:02', '2014-04-07@20:02',
    '2014-04-08@20:04', '2014-04-09@20:04', '2014-04-10@20:04', '2014-04-11@20:04', '2014-04-12@20:03',
    '2014-04-13@20:01', '2014-04-14@20:05', '2014-04-15@20:05', '2014-04-16@20:06', '2014-04-17@20:05',
    '2014-04-18@20:06', '2014-04-19@20:02', '2014-04-20@20:01', '2014-04-21@20:01', '2014-04-22@20:06',
    '2014-04-23@20:06', '2014-04-24@20:05', '2014-04-25@20:04', '2014-04-26@20:02', '2014-04-27@20:02',
    '2014-04-28@20:05', '2014-04-29@20:05', '2014-04-30@20:05', '2014-05-01@20:06', '2014-05-02@20:05',
    '2014-05-03@20:03', '2014-05-04@20:01', '2014-05-05@20:06', '2014-05-06@20:06', '2014-05-07@20:05',
    '2014-05-08@20:03', '2014-05-09@20:01', '2014-05-10@20:01', '2014-05-11@20:01', '2014-05-12@20:05',
    '2014-05-13@20:06', '2014-05-14@20:04', '2014-05-15@20:06', '2014-05-16@20:05', '2014-05-17@20:02',
    '2014-05-18@20:01', '2014-05-19@20:02', '2014-05-20@20:04', '2014-05-21@20:03', '2014-05-22@20:02',
    '2014-05-23@20:02', '2014-05-24@20:01', '2014-05-25@20:01', '2014-05-26@20:05', '2014-05-27@20:03',
    '2014-05-28@20:03', '2014-05-29@20:01', '2014-05-30@20:02', '2014-05-31@20:02', '2014-06-01@20:01',
    '2014-06-02@20:05', '2014-06-03@20:02', '2014-06-04@20:03', '2014-06-05@20:03', '2014-06-06@20:02',
    '2014-06-07@20:01', '2014-06-08@20:01', '2014-06-09@20:01', '2014-06-10@20:02', '2014-06-11@20:02',
    '2014-06-12@20:03', '2014-06-13@20:05', '2014-06-14@20:01', '2014-06-15@20:01', '2014-06-16@20:02',
    '2014-06-17@20:01', '2014-06-18@20:01', '2014-06-19@20:04', '2014-06-20@20:02', '2014-06-21@20:02',
    '2014-06-22@20:01', '2014-06-23@20:04', '2014-06-24@20:06', '2014-06-25@20:03', '2014-06-26@20:04',
    '2014-06-27@20:02', '2014-06-28@20:02', '2014-06-29@20:01', '2014-06-30@20:03', '2014-07-01@20:02',
    '2014-07-02@20:03', 'some-random-directory',
])


class RotateBackupsTestCase(unittest.TestCase):

    """:mod:`unittest` compatible container for `rotate-backups` tests."""

    def setUp(self):
        """Enable verbose logging for the test suite."""
        coloredlogs.install(level=logging.DEBUG)

    def test_argument_validation(self):
        """Test argument validation."""
        # Test that an invalid ionice scheduling class causes an error to be reported.
        assert run_cli('--ionice=unsupported-class') != 0
        # Test that an invalid rotation scheme causes an error to be reported.
        assert run_cli('--hourly=not-a-number') != 0
        # Test that invalid location values are properly reported.
        self.assertRaises(ValueError, lambda: coerce_location(['not', 'a', 'string']))
        # Argument validation tests that require an empty directory.
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            # Test that non-existing directories cause an error to be reported.
            self.assertRaises(ValueError, lambda: run_cli(os.path.join(root, 'does-not-exist')))
            # Test that loading of a custom configuration file raises an
            # exception when the configuration file cannot be loaded.
            self.assertRaises(ValueError, lambda: list(load_config_file(os.path.join(root, 'rotate-backups.ini'))))
            # Test that an empty rotation scheme raises an exception.
            self.create_sample_backup_set(root)
            self.assertRaises(ValueError, lambda: RotateBackups(rotation_scheme={}).rotate_backups(root))
        # Argument validation tests that assume the current user isn't root.
        if os.getuid() != 0:
            # I'm being lazy and will assume that this test suite will only be
            # run on systems where users other than root do not have access to
            # /root.
            self.assertRaises(ValueError, lambda: run_cli('-n', '/root'))

    def test_dry_run(self):
        """Make sure dry run doesn't remove any backups."""
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            self.create_sample_backup_set(root)
            run_cli(
                '--dry-run', '--verbose', '--daily=7', '--weekly=7',
                '--monthly=12', '--yearly=always', root,
            )
            backups_that_were_preserved = set(os.listdir(root))
            assert backups_that_were_preserved == SAMPLE_BACKUP_SET

    def test_rotate_backups(self):
        """Test the :func:`.rotate_backups()` function."""
        # These are the backups expected to be preserved. After each backup
        # I've noted which rotation scheme it falls in and the number of
        # preserved backups within that rotation scheme (counting up as we
        # progress through the backups sorted by date).
        expected_to_be_preserved = set([
            '2013-10-10@20:07',  # monthly (1), yearly (1)
            '2013-11-01@20:06',  # monthly (2)
            '2013-12-01@20:07',  # monthly (3)
            '2014-01-01@20:07',  # monthly (4), yearly (2)
            '2014-02-01@20:05',  # monthly (5)
            '2014-03-01@20:04',  # monthly (6)
            '2014-04-01@20:03',  # monthly (7)
            '2014-05-01@20:06',  # monthly (8)
            '2014-06-01@20:01',  # monthly (9)
            '2014-06-09@20:01',  # weekly (1)
            '2014-06-16@20:02',  # weekly (2)
            '2014-06-23@20:04',  # weekly (3)
            '2014-06-26@20:04',  # daily (1)
            '2014-06-27@20:02',  # daily (2)
            '2014-06-28@20:02',  # daily (3)
            '2014-06-29@20:01',  # daily (4)
            '2014-06-30@20:03',  # daily (5), weekly (4)
            '2014-07-01@20:02',  # daily (6), monthly (10)
            '2014-07-02@20:03',  # hourly (1), daily (7)
            'some-random-directory',  # no recognizable time stamp, should definitely be preserved
            'rotate-backups.ini',  # no recognizable time stamp, should definitely be preserved
        ])
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            # Specify the rotation scheme and options through a configuration file.
            config_file = os.path.join(root, 'rotate-backups.ini')
            parser = configparser.RawConfigParser()
            parser.add_section(root)
            parser.set(root, 'hourly', '24')
            parser.set(root, 'daily', '7')
            parser.set(root, 'weekly', '4')
            parser.set(root, 'monthly', '12')
            parser.set(root, 'yearly', 'always')
            parser.set(root, 'ionice', 'idle')
            with open(config_file, 'w') as handle:
                parser.write(handle)
            self.create_sample_backup_set(root)
            run_cli('--verbose', '--config=%s' % config_file)
            backups_that_were_preserved = set(os.listdir(root))
            assert backups_that_were_preserved == expected_to_be_preserved

    def test_include_list(self):
        """Test include list logic."""
        # These are the backups expected to be preserved within the year 2014
        # (other years are excluded and so should all be preserved, see below).
        # After each backup I've noted which rotation scheme it falls in.
        expected_to_be_preserved = set([
            '2014-01-01@20:07',  # monthly, yearly
            '2014-02-01@20:05',  # monthly
            '2014-03-01@20:04',  # monthly
            '2014-04-01@20:03',  # monthly
            '2014-05-01@20:06',  # monthly
            '2014-06-01@20:01',  # monthly
            '2014-06-09@20:01',  # weekly
            '2014-06-16@20:02',  # weekly
            '2014-06-23@20:04',  # weekly
            '2014-06-26@20:04',  # daily
            '2014-06-27@20:02',  # daily
            '2014-06-28@20:02',  # daily
            '2014-06-29@20:01',  # daily
            '2014-06-30@20:03',  # daily, weekly
            '2014-07-01@20:02',  # daily, monthly
            '2014-07-02@20:03',  # hourly, daily
            'some-random-directory',  # no recognizable time stamp, should definitely be preserved
        ])
        for name in SAMPLE_BACKUP_SET:
            if not name.startswith('2014-'):
                expected_to_be_preserved.add(name)
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            self.create_sample_backup_set(root)
            run_cli(
                '--verbose', '--ionice=idle', '--hourly=24', '--daily=7',
                '--weekly=4', '--monthly=12', '--yearly=always',
                '--include=2014-*', root,
            )
            backups_that_were_preserved = set(os.listdir(root))
            assert backups_that_were_preserved == expected_to_be_preserved

    def test_exclude_list(self):
        """Test exclude list logic."""
        # These are the backups expected to be preserved. After each backup
        # I've noted which rotation scheme it falls in and the number of
        # preserved backups within that rotation scheme (counting up as we
        # progress through the backups sorted by date).
        expected_to_be_preserved = set([
            '2013-10-10@20:07',  # monthly (1), yearly (1)
            '2013-11-01@20:06',  # monthly (2)
            '2013-12-01@20:07',  # monthly (3)
            '2014-01-01@20:07',  # monthly (4), yearly (2)
            '2014-02-01@20:05',  # monthly (5)
            '2014-03-01@20:04',  # monthly (6)
            '2014-04-01@20:03',  # monthly (7)
            '2014-05-01@20:06',  # monthly (8)
            '2014-05-19@20:02',  # weekly (1)
            '2014-05-26@20:05',  # weekly (2)
            '2014-06-01@20:01',  # monthly (9)
            '2014-06-09@20:01',  # weekly (3)
            '2014-06-16@20:02',  # weekly (4)
            '2014-06-23@20:04',  # weekly (5)
            '2014-06-26@20:04',  # daily (1)
            '2014-06-27@20:02',  # daily (2)
            '2014-06-28@20:02',  # daily (3)
            '2014-06-29@20:01',  # daily (4)
            '2014-06-30@20:03',  # daily (5), weekly (6)
            '2014-07-01@20:02',  # daily (6), monthly (10)
            '2014-07-02@20:03',  # hourly (1), daily (7)
            'some-random-directory',  # no recognizable time stamp, should definitely be preserved
        ])
        for name in SAMPLE_BACKUP_SET:
            if name.startswith('2014-05-'):
                expected_to_be_preserved.add(name)
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            self.create_sample_backup_set(root)
            run_cli(
                '--verbose', '--ionice=idle', '--hourly=24', '--daily=7',
                '--weekly=4', '--monthly=12', '--yearly=always',
                '--exclude=2014-05-*', root,
            )
            backups_that_were_preserved = set(os.listdir(root))
            assert backups_that_were_preserved == expected_to_be_preserved

    def test_strict_rotation(self):
        """Test strict rotation."""
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            os.mkdir(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_10-00'))
            os.mkdir(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_12-00'))
            os.mkdir(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_16-00'))
            run_cli('--hourly=3', '--daily=1', root)
            assert os.path.exists(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_10-00'))
            assert os.path.exists(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_12-00')) is False
            assert os.path.exists(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_16-00'))

    def test_relaxed_rotation(self):
        """Test relaxed rotation."""
        with TemporaryDirectory(prefix='rotate-backups-', suffix='-test-suite') as root:
            os.mkdir(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_10-00'))
            os.mkdir(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_12-00'))
            os.mkdir(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_16-00'))
            run_cli('--hourly=3', '--daily=1', '--relaxed', root)
            assert os.path.exists(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_10-00'))
            assert os.path.exists(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_12-00'))
            assert os.path.exists(os.path.join(root, 'galera_backup_db4.sl.example.lab_2016-03-17_16-00'))

    def create_sample_backup_set(self, root):
        """Create a sample backup set to be rotated."""
        for name in SAMPLE_BACKUP_SET:
            os.mkdir(os.path.join(root, name))


def run_cli(*arguments):
    """Simple wrapper to run :func:`rotate_backups.cli.main()` in the same process."""
    # Temporarily replace sys.argv.
    saved_arguments = sys.argv
    sys.argv = ['rotate-backups'] + list(arguments)
    try:
        main()
        exit_code = 0
    except SystemExit as e:
        exit_code = e.code
    finally:
        # Restore sys.argv before we return.
        sys.argv = saved_arguments
    return exit_code


class TemporaryDirectory(object):

    """
    Easy temporary directory creation & cleanup using the :keyword:`with` statement.

    Here's an example of how to use this:

    .. code-block:: python

       with TemporaryDirectory() as directory:
           # Do something useful here.
           assert os.path.isdir(directory)
    """

    def __init__(self, **options):
        """
        Initialize context manager that manages creation & cleanup of temporary directory.

        :param options: Any keyword arguments are passed on to
                        :func:`tempfile.mkdtemp()`.
        """
        self.options = options

    def __enter__(self):
        """Create the temporary directory."""
        self.temporary_directory = tempfile.mkdtemp(**self.options)
        logger.debug("Created temporary directory: %s", self.temporary_directory)
        return self.temporary_directory

    def __exit__(self, exc_type, exc_value, traceback):
        """Destroy the temporary directory."""
        logger.debug("Cleaning up temporary directory: %s", self.temporary_directory)
        shutil.rmtree(self.temporary_directory)
        del self.temporary_directory
