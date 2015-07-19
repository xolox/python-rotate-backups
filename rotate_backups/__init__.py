# rotate-backups: Simple command line interface for backup rotation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 19, 2015
# URL: https://github.com/xolox/python-rotate-backups

"""
Usage: rotate-backups [OPTIONS] DIRECTORY..

Supported options:

 -H, --hourly=NUM    how many hourly backups to preserve
 -d, --daily=NUM     how many daily backups to preserve
 -w, --weekly=NUM    how many weekly backups to preserve
 -m, --monthly=NUM   how many monthly backups to preserve
 -y, --yearly=NUM    how many yearly backups to preserve
 -i, --ionice=CLASS  use ionice to set the I/O scheduling class
 -n, --dry-run       don't make any changes, just print what would be done
 -v, --verbose       make more noise
 -h, --help          show this message and exit
"""

# Semi-standard module versioning.
__version__ = '0.1.2'

# Standard library modules.
import collections
import datetime
import functools
import logging
import os
import re

# External dependencies.
import executor
import humanfriendly
import natsort
from dateutil.relativedelta import relativedelta

# Initialize a logger.
logger = logging.getLogger(__name__)

# Ordered mapping of frequency names to the amount of time in each frequency.
ordered_frequencies = (('hourly', relativedelta(hours=1)),
                       ('daily', relativedelta(days=1)),
                       ('weekly', relativedelta(weeks=1)),
                       ('monthly', relativedelta(months=1)),
                       ('yearly', relativedelta(years=1)))
supported_frequencies = dict(ordered_frequencies)

# Regular expression that matches timestamps encoded in filenames.
timestamp_pattern = re.compile(r'''
    # Required components.
    (?P<year>\d{4} ) \D?
    (?P<month>\d{2}) \D?
    (?P<day>\d{2}  ) \D?
    (?:
        # Optional components.
        (?P<hour>\d{2}  ) \D?
        (?P<minute>\d{2}) \D?
        (?P<second>\d{2})?
    )?
''', re.VERBOSE)


def rotate_backups(directory, rotation_scheme, dry_run=False, io_scheduling_class=None):
    """
    Rotate the backups in a directory according to a flexible rotation scheme.

    :param directory: The directory containing the backups (a string).
    :param rotation_scheme: A dictionary with one or more of the keys 'hourly',
                            'daily', 'weekly', 'monthly', 'yearly' and integer
                            values.
    :param dry_run: If this is ``True`` then no changes will be made, which
                    provides a 'preview' of the effect of the rotation scheme
                    (the default is ``False``).
    :param io_scheduling_class: Use ``ionice`` to set the I/O scheduling class
                                (expected to be one of the strings 'idle',
                                'best-effort' or 'realtime').
    """
    # Find the backups and their dates.
    backups = set()
    directory = os.path.abspath(directory)
    logger.info("Scanning directory for timestamped backups: %s", directory)
    for entry in natsort.natsort(os.listdir(directory)):
        match = timestamp_pattern.search(entry)
        if match:
            backups.add(Backup(pathname=os.path.join(directory, entry),
                               datetime=datetime.datetime(*(int(group, 10) for group in match.groups('0')))))
        else:
            logger.debug("Failed to match time stamp in filename: %s", entry)
    if not backups:
        logger.info("No backups found in %s.", directory)
        return
    logger.info("Found %i timestamped backups in %s.", len(backups), directory)
    # Sort the backups by date and find the date/time of the most recent backup.
    sorted_backups = sorted(backups)
    most_recent_backup = sorted_backups[-1].datetime
    # Group the backups by rotation frequencies.
    grouped_backups = dict((frequency, collections.defaultdict(list)) for frequency in supported_frequencies)
    for backup in backups:
        grouped_backups['hourly'][(backup.year, backup.month, backup.day, backup.hour)].append(backup)
        grouped_backups['daily'][(backup.year, backup.month, backup.day)].append(backup)
        grouped_backups['weekly'][(backup.year, backup.week)].append(backup)
        grouped_backups['monthly'][(backup.year, backup.month)].append(backup)
        grouped_backups['yearly'][backup.year].append(backup)
    # Apply the user defined rotation scheme.
    # FIXME Guard against an empty rotation scheme?!
    for frequency, backups_by_frequency in grouped_backups.items():
        # Ignore frequencies not specified by the user.
        if frequency not in rotation_scheme:
            grouped_backups[frequency].clear()
        else:
            retention_period = rotation_scheme[frequency]
            # Reduce the number of backups in each period to a single backup
            # (the first one within the period).
            for period, backups_in_period in backups_by_frequency.items():
                backups_by_frequency[period] = sorted(backups_in_period)[0]
            if retention_period != 'always':
                # Remove backups older than the minimum date.
                minimum_date = most_recent_backup - supported_frequencies[frequency] * retention_period
                for period, backup in backups_by_frequency.items():
                    if backup.datetime < minimum_date:
                        backups_by_frequency.pop(period)
                # If more than the configured number of backups remain at this
                # point then we remove the oldest backups.
                grouped_backups[frequency] = dict(sorted(backups_by_frequency.items())[-retention_period:])
    # Find out which backups should be purged.
    backups_to_preserve = collections.defaultdict(list)
    for frequency, delta in ordered_frequencies:
        for backup in grouped_backups[frequency].values():
            backups_to_preserve[backup].append(frequency)
    for backup in sorted(backups):
        if backup in backups_to_preserve:
            matching_periods = backups_to_preserve[backup]
            logger.info("Preserving %s (matches %s retention %s) ..", backup.pathname,
                        humanfriendly.concatenate(map(repr, matching_periods)),
                        "period" if len(matching_periods) == 1 else "periods")
        else:
            logger.info("Deleting %s %s ..", backup.type, backup.pathname)
            if not dry_run:
                command = ['rm', '-Rf', backup.pathname]
                if io_scheduling_class:
                    command = ['ionice', '--class', io_scheduling_class] + command
                timer = humanfriendly.Timer()
                executor.execute(*command, logger=logger)
                logger.debug("Deleted %s in %s.", backup.pathname, timer)
    if len(backups_to_preserve) == len(backups):
        logger.info("Nothing to do!")


@functools.total_ordering
class Backup(object):

    """:py:class:`Backup` objects represent a rotation subject."""

    def __init__(self, pathname, datetime):
        """
        Initialize a :py:class:`Backup` object.

        :param pathname: The filename of the backup (a string).
        :param datetime: The date/time when the backup was created (a
                         :py:class:`datetime.datetime` object).
        """
        self.pathname = pathname
        self.datetime = datetime

    @property
    def type(self):
        """Get a string describing the type of backup (e.g. file, directory)."""
        if os.path.islink(self.pathname):
            return 'symbolic link'
        elif os.path.isdir(self.pathname):
            return 'directory'
        else:
            return 'file'

    @property
    def week(self):
        """Get the ISO week number."""
        return self.datetime.isocalendar()[1]

    def __getattr__(self, name):
        """Defer attribute access to the datetime object."""
        return getattr(self.datetime, name)

    def __repr__(self):
        """Enable pretty printing of :py:class:`Backup` objects."""
        return "Backup(pathname=%r, datetime=%r)" % (self.pathname, self.datetime)

    def __hash__(self):
        """Make it possible to use :py:class:`Backup` objects in sets and as dictionary keys."""
        return hash(self.pathname)

    def __eq__(self, other):
        """Make it possible to use :py:class:`Backup` objects in sets and as dictionary keys."""
        return type(self) == type(other) and self.datetime == other.datetime

    def __lt__(self, other):
        """Enable proper sorting of backups."""
        return self.datetime < other.datetime
