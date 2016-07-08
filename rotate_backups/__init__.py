# rotate-backups: Simple command line interface for backup rotation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 9, 2016
# URL: https://github.com/xolox/python-rotate-backups

"""
Simple to use Python API for rotation of backups.

The :mod:`rotate_backups` module contains the Python API of the
`rotate-backups` package. The core logic of the package is contained in the
:class:`RotateBackups` class.
"""

# Standard library modules.
import collections
import datetime
import fnmatch
import os
import re

# External dependencies.
from dateutil.relativedelta import relativedelta
from executor.contexts import create_context
from humanfriendly import Timer, coerce_boolean, format_path, parse_path
from humanfriendly.text import compact, concatenate, split
from natsort import natsort
from property_manager import PropertyManager, key_property, required_property
from six import string_types
from six.moves import configparser
from verboselogs import VerboseLogger

# Semi-standard module versioning.
__version__ = '3.3'

# Initialize a logger for this module.
logger = VerboseLogger(__name__)

GLOBAL_CONFIG_FILE = '/etc/rotate-backups.ini'
"""The pathname of the system wide configuration file (a string)."""

LOCAL_CONFIG_FILE = '~/.rotate-backups.ini'
"""The pathname of the user specific configuration file (a string)."""

ORDERED_FREQUENCIES = (('hourly', relativedelta(hours=1)),
                       ('daily', relativedelta(days=1)),
                       ('weekly', relativedelta(weeks=1)),
                       ('monthly', relativedelta(months=1)),
                       ('yearly', relativedelta(years=1)))
"""
A list of tuples with two values each:

- The name of a rotation frequency (a string like 'hourly', 'daily', etc.).
- A :class:`~dateutil.relativedelta.relativedelta` object.

The tuples are sorted by increasing delta (intentionally).
"""

SUPPORTED_FREQUENCIES = dict(ORDERED_FREQUENCIES)
"""
A dictionary with rotation frequency names (strings) as keys and
:class:`~dateutil.relativedelta.relativedelta` objects as values. This
dictionary is generated based on the tuples in :data:`ORDERED_FREQUENCIES`.
"""

TIMESTAMP_PATTERN = re.compile(r'''
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
"""
A compiled regular expression object used to match timestamps encoded in
filenames.
"""


def coerce_location(value, **options):
    """
    Coerce a string to a :class:`Location` object.

    :param value: The value to coerce (a string or :class:`Location` object).
    :param options: Any keyword arguments are passed on to
                    :func:`~executor.contexts.create_context()`.
    :returns: A :class:`Location` object.
    """
    if isinstance(value, Location):
        # Location objects pass through untouched.
        return value
    else:
        # Other values are expected to be strings.
        if not isinstance(value, string_types):
            msg = "Expected Location object or string, got %s instead!"
            raise ValueError(msg % type(value))
        # Try to parse a remote location.
        ssh_alias, _, directory = value.partition(':')
        if ssh_alias and directory and '/' not in ssh_alias:
            options['ssh_alias'] = ssh_alias
        else:
            directory = value
        return Location(context=create_context(**options),
                        directory=parse_path(directory))


def coerce_retention_period(value):
    """
    Coerce a retention period to a Python value.

    :param value: A string containing an integer number or the text 'always'.
    :returns: An integer number or the string 'always'.
    :raises: :exc:`~exceptions.ValueError` when the string can't be coerced.
    """
    value = value.strip()
    if value.lower() == 'always':
        return 'always'
    elif value.isdigit():
        return int(value)
    else:
        raise ValueError("Invalid retention period! (%s)" % value)


def load_config_file(configuration_file=None):
    """
    Load a configuration file with backup directories and rotation schemes.

    :param configuration_file: Override the pathname of the configuration file
                               to load (a string or :data:`None`).
    :returns: A generator of tuples with four values each:

              1. An execution context created using :mod:`executor.contexts`.
              2. The pathname of a directory with backups (a string).
              3. A dictionary with the rotation scheme.
              4. A dictionary with additional options.
    :raises: :exc:`~exceptions.ValueError` when `configuration_file` is given
             but doesn't exist or can't be loaded.

    When `configuration_file` isn't given :data:`LOCAL_CONFIG_FILE` and
    :data:`GLOBAL_CONFIG_FILE` are checked and the first configuration file
    that exists is loaded. This function is used by :class:`RotateBackups` to
    discover user defined rotation schemes and by :mod:`rotate_backups.cli` to
    discover directories for which backup rotation is configured.
    """
    parser = configparser.RawConfigParser()
    if configuration_file:
        logger.verbose("Reading configuration file %s ..", format_path(configuration_file))
        loaded_files = parser.read(configuration_file)
        if len(loaded_files) == 0:
            msg = "Failed to read configuration file! (%s)"
            raise ValueError(msg % configuration_file)
    else:
        for config_file in LOCAL_CONFIG_FILE, GLOBAL_CONFIG_FILE:
            pathname = parse_path(config_file)
            if parser.read(pathname):
                logger.verbose("Reading configuration file %s ..", format_path(pathname))
                break
    for section in parser.sections():
        items = dict(parser.items(section))
        context_options = {}
        if coerce_boolean(items.get('use-sudo')):
            context_options['sudo'] = True
        if items.get('ssh-user'):
            context_options['ssh_user'] = items['ssh-user']
        location = coerce_location(section, **context_options)
        rotation_scheme = dict((name, coerce_retention_period(items[name]))
                               for name in SUPPORTED_FREQUENCIES
                               if name in items)
        options = dict(include_list=split(items.get('include-list', '')),
                       exclude_list=split(items.get('exclude-list', '')),
                       io_scheduling_class=items.get('ionice'),
                       strict=coerce_boolean(items.get('strict', 'yes')))
        yield location, rotation_scheme, options


def rotate_backups(directory, rotation_scheme, include_list=None, exclude_list=None,
                   dry_run=False, io_scheduling_class=None):
    """
    Rotate the backups in a directory according to a flexible rotation scheme.

    .. note:: This function exists to preserve backwards compatibility with
              older versions of the `rotate-backups` package where all of the
              logic was exposed as a single function. Please refer to the
              documentation of the :class:`RotateBackups` constructor and the
              :func:`~RotateBackups.rotate_backups()` method for an explanation
              of this function's parameters.
    """
    RotateBackups(
        rotation_scheme=rotation_scheme,
        include_list=include_list,
        exclude_list=exclude_list,
        dry_run=dry_run,
        io_scheduling_class=io_scheduling_class,
    ).rotate_backups(directory)


class RotateBackups(object):

    """Python API for the ``rotate-backups`` program."""

    def __init__(self, rotation_scheme, include_list=None, exclude_list=None,
                 dry_run=False, io_scheduling_class=None, config_file=None,
                 strict=True):
        """
        Construct a :class:`RotateBackups` object.

        :param rotation_scheme: A dictionary with one or more of the keys 'hourly',
                                'daily', 'weekly', 'monthly', 'yearly'. Each key is
                                expected to have one of the following values:

                                - An integer gives the number of backups in the
                                  corresponding category to preserve, starting from
                                  the most recent backup and counting back in
                                  time.
                                - The string 'always' means all backups in the
                                  corresponding category are preserved (useful for
                                  the biggest time unit in the rotation scheme).

                                By default no backups are preserved for categories
                                (keys) not present in the dictionary.
        :param include_list: A list of strings with :mod:`fnmatch` patterns. If a
                             nonempty include list is specified each backup must
                             match a pattern in the include list, otherwise it
                             will be ignored.
        :param exclude_list: A list of strings with :mod:`fnmatch` patterns. If a
                             backup matches the exclude list it will be ignored,
                             *even if it also matched the include list* (it's the
                             only logical way to combine both lists).
        :param dry_run: If this is :data:`True` then no changes will be made, which
                        provides a 'preview' of the effect of the rotation scheme
                        (the default is :data:`False`). Right now this is only useful
                        in the command line interface because there's no return
                        value.
        :param io_scheduling_class: Use ``ionice`` to set the I/O scheduling class
                                    (expected to be one of the strings 'idle',
                                    'best-effort' or 'realtime').
        :param config_file: The pathname of a configuration file (a string).
        :param strict: Whether to enforce the time window for each rotation
                       frequency (a boolean, defaults to :data:`True`). The
                       easiest way to explain the difference between strict
                       and relaxed rotation is using an example:

                       - If `strict` is :data:`True` and the number of hourly
                         backups to preserve is three, only backups created in
                         the relevant time window (the hour of the most recent
                         backup and the two hours leading up to that) will
                         match the hourly frequency.

                       - If `strict` is :data:`False` then the three most
                         recent backups will all match the hourly frequency
                         (and thus be preserved), regardless of the calculated
                         time window.

                       If the explanation above is not clear enough, here's a
                       simple way to decide whether you want to customize this
                       behavior:

                       - If your backups are created at regular intervals and
                         you never miss an interval then the default
                         (:data:`True`) is most likely fine.

                       - If your backups are created at irregular intervals
                         then you may want to set `strict` to :data:`False` to
                         convince :class:`RotateBackups` to preserve more
                         backups.
        """
        self.rotation_scheme = rotation_scheme
        self.include_list = include_list
        self.exclude_list = exclude_list
        self.dry_run = dry_run
        self.io_scheduling_class = io_scheduling_class
        self.config_file = config_file
        self.strict = strict

    def rotate_backups(self, location, load_config=True):
        """
        Rotate the backups in a directory according to a flexible rotation scheme.

        :param location: Any value accepted by :func:`coerce_location()`.
        :param load_config: If :data:`True` (so by default) the rotation scheme
                            and other options can be customized by the user in
                            a configuration file. In this case the caller's
                            arguments are only used when the configuration file
                            doesn't define a configuration for the location.
        :raises: :exc:`~exceptions.ValueError` when the given location doesn't
                 exist, isn't readable or isn't writable. The third check is
                 only performed when dry run isn't enabled.

        This function binds the main methods of the :class:`RotateBackups`
        class together to implement backup rotation with an easy to use Python
        API. If you're using `rotate-backups` as a Python API and the default
        behavior is not satisfactory, consider writing your own
        :func:`rotate_backups()` function based on the underlying
        :func:`collect_backups()`, :func:`group_backups()`,
        :func:`apply_rotation_scheme()` and
        :func:`find_preservation_criteria()` methods.
        """
        location = coerce_location(location)
        # Load configuration overrides by user?
        if load_config:
            location = self.load_config_file(location)
        # Collect the backups in the given directory.
        sorted_backups = self.collect_backups(location)
        if not sorted_backups:
            logger.info("No backups found in %s.", location)
            return
        # Make sure the directory is writable.
        if not self.dry_run:
            location.ensure_writable()
        most_recent_backup = sorted_backups[-1]
        # Group the backups by the rotation frequencies.
        backups_by_frequency = self.group_backups(sorted_backups)
        # Apply the user defined rotation scheme.
        self.apply_rotation_scheme(backups_by_frequency, most_recent_backup.timestamp)
        # Find which backups to preserve and why.
        backups_to_preserve = self.find_preservation_criteria(backups_by_frequency)
        # Apply the calculated rotation scheme.
        for backup in sorted_backups:
            if backup in backups_to_preserve:
                matching_periods = backups_to_preserve[backup]
                logger.info("Preserving %s (matches %s retention %s) ..",
                            format_path(backup.pathname),
                            concatenate(map(repr, matching_periods)),
                            "period" if len(matching_periods) == 1 else "periods")
            else:
                logger.info("Deleting %s ..", format_path(backup.pathname))
                if not self.dry_run:
                    command = ['rm', '-Rf', backup.pathname]
                    if self.io_scheduling_class:
                        command = ['ionice', '--class', self.io_scheduling_class] + command
                    timer = Timer()
                    location.context.execute(*command)
                    logger.verbose("Deleted %s in %s.", format_path(backup.pathname), timer)
        if len(backups_to_preserve) == len(sorted_backups):
            logger.info("Nothing to do! (all backups preserved)")

    def load_config_file(self, location):
        """
        Load a rotation scheme and other options from a configuration file.

        :param location: Any value accepted by :func:`coerce_location()`.
        :returns: The configured or given :class:`Location` object.
        """
        location = coerce_location(location)
        for configured_location, rotation_scheme, options in load_config_file(self.config_file):
            if location == configured_location:
                logger.verbose("Loading configuration for %s ..", location)
                if rotation_scheme:
                    self.rotation_scheme = rotation_scheme
                for name, value in options.items():
                    if value:
                        setattr(self, name, value)
                return configured_location
        logger.verbose("No configuration found for %s.", location)
        return location

    def collect_backups(self, location):
        """
        Collect the backups at the given location.

        :param location: Any value accepted by :func:`coerce_location()`.
        :returns: A sorted :class:`list` of :class:`Backup` objects (the
                  backups are sorted by their date).
        :raises: :exc:`~exceptions.ValueError` when the given directory doesn't
                 exist or isn't readable.
        """
        backups = []
        location = coerce_location(location)
        logger.info("Scanning %s for backups ..", location)
        location.ensure_readable()
        for entry in natsort(location.context.list_entries(location.directory)):
            match = TIMESTAMP_PATTERN.search(entry)
            if match:
                if self.exclude_list and any(fnmatch.fnmatch(entry, p) for p in self.exclude_list):
                    logger.verbose("Excluded %r (it matched the exclude list).", entry)
                elif self.include_list and not any(fnmatch.fnmatch(entry, p) for p in self.include_list):
                    logger.verbose("Excluded %r (it didn't match the include list).", entry)
                else:
                    backups.append(Backup(
                        pathname=os.path.join(location.directory, entry),
                        timestamp=datetime.datetime(*(int(group, 10) for group in match.groups('0'))),
                    ))
            else:
                logger.debug("Failed to match time stamp in filename: %s", entry)
        if backups:
            logger.info("Found %i timestamped backups in %s.", len(backups), location)
        return sorted(backups)

    def group_backups(self, backups):
        """
        Group backups collected by :func:`collect_backups()` by rotation frequencies.

        :param backups: A :class:`set` of :class:`Backup` objects.
        :returns: A :class:`dict` whose keys are the names of rotation
                  frequencies ('hourly', 'daily', etc.) and whose values are
                  dictionaries. Each nested dictionary contains lists of
                  :class:`Backup` objects that are grouped together because
                  they belong into the same time unit for the corresponding
                  rotation frequency.
        """
        backups_by_frequency = dict((frequency, collections.defaultdict(list)) for frequency in SUPPORTED_FREQUENCIES)
        for b in backups:
            backups_by_frequency['hourly'][(b.year, b.month, b.day, b.hour)].append(b)
            backups_by_frequency['daily'][(b.year, b.month, b.day)].append(b)
            backups_by_frequency['weekly'][(b.year, b.week)].append(b)
            backups_by_frequency['monthly'][(b.year, b.month)].append(b)
            backups_by_frequency['yearly'][b.year].append(b)
        return backups_by_frequency

    def apply_rotation_scheme(self, backups_by_frequency, most_recent_backup):
        """
        Apply the user defined rotation scheme to the result of :func:`group_backups()`.

        :param backups_by_frequency: A :class:`dict` in the format generated by
                                     :func:`group_backups()`.
        :param most_recent_backup: The :class:`~datetime.datetime` of the most
                                   recent backup.
        :raises: :exc:`~exceptions.ValueError` when the rotation scheme
                 dictionary is empty (this would cause all backups to be
                 deleted).

        .. note:: This method mutates the given data structure by removing all
                  backups that should be removed to apply the user defined
                  rotation scheme.
        """
        if not self.rotation_scheme:
            raise ValueError("Refusing to use empty rotation scheme! (all backups would be deleted)")
        for frequency, backups in backups_by_frequency.items():
            # Ignore frequencies not specified by the user.
            if frequency not in self.rotation_scheme:
                backups.clear()
            else:
                # Reduce the number of backups in each period of this rotation
                # frequency to a single backup (the first in the period).
                for period, backups_in_period in backups.items():
                    first_backup = sorted(backups_in_period)[0]
                    backups[period] = [first_backup]
                # Check if we need to rotate away backups in old periods.
                retention_period = self.rotation_scheme[frequency]
                if retention_period != 'always':
                    # Remove backups created before the minimum date of this
                    # rotation frequency? (relative to the most recent backup)
                    if self.strict:
                        minimum_date = most_recent_backup - SUPPORTED_FREQUENCIES[frequency] * retention_period
                        for period, backups_in_period in list(backups.items()):
                            for backup in backups_in_period:
                                if backup.timestamp < minimum_date:
                                    backups_in_period.remove(backup)
                            if not backups_in_period:
                                backups.pop(period)
                    # If there are more periods remaining than the user
                    # requested to be preserved we delete the oldest one(s).
                    items_to_preserve = sorted(backups.items())[-retention_period:]
                    backups_by_frequency[frequency] = dict(items_to_preserve)

    def find_preservation_criteria(self, backups_by_frequency):
        """
        Collect the criteria used to decide which backups to preserve.

        :param backups_by_frequency: A :class:`dict` in the format generated by
                                     :func:`group_backups()` which has been
                                     processed by :func:`apply_rotation_scheme()`.
        :returns: A :class:`dict` with :class:`Backup` objects as keys and
                  :class:`list` objects containing strings (rotation
                  frequencies) as values.
        """
        backups_to_preserve = collections.defaultdict(list)
        for frequency, delta in ORDERED_FREQUENCIES:
            for period in backups_by_frequency[frequency].values():
                for backup in period:
                    backups_to_preserve[backup].append(frequency)
        return backups_to_preserve


class Location(PropertyManager):

    """:class:`Location` objects represent a root directory containing backups."""

    @required_property
    def context(self):
        """An execution context created using :mod:`executor.contexts`."""

    @required_property
    def directory(self):
        """The pathname of a directory containing backups (a string)."""

    def ensure_exists(self):
        """Make sure the location exists."""
        if not self.context.is_directory(self.directory):
            # This can also happen when we don't have permission to one of the
            # parent directories so we'll point that out in the error message
            # when it seems applicable (so as not to confuse users).
            if self.context.have_superuser_privileges:
                msg = "The directory %s doesn't exist!"
                raise ValueError(msg % self)
            else:
                raise ValueError(compact("""
                    The directory {location} isn't accessible, most likely
                    because it doesn't exist or because of permissions. If
                    you're sure the directory exists you can use the
                    --use-sudo option.
                """, location=self))

    def ensure_readable(self):
        """Make sure the location exists and is readable."""
        self.ensure_exists()
        if not self.context.is_readable(self.directory):
            if self.context.have_superuser_privileges:
                msg = "The directory %s isn't readable!"
                raise ValueError(msg % self)
            else:
                raise ValueError(compact("""
                    The directory {location} isn't readable, most likely
                    because of permissions. Consider using the --use-sudo
                    option.
                """, location=self))

    def ensure_writable(self):
        """Make sure the directory exists and is writable."""
        self.ensure_exists()
        if not self.context.is_writable(self.directory):
            if self.context.have_superuser_privileges:
                msg = "The directory %s isn't writable!"
                raise ValueError(msg % self)
            else:
                raise ValueError(compact("""
                    The directory {location} isn't writable, most likely due
                    to permissions. Consider using the --use-sudo option.
                """, location=self))

    def __str__(self):
        """Render a simple human readable representation of a location."""
        ssh_alias = getattr(self.context, 'ssh_alias', None)
        return '%s:%s' % (ssh_alias, self.directory) if ssh_alias else self.directory

    def __eq__(self, other):
        """Check whether two locations point to the same host and directory."""
        return isinstance(other, type(self)) and self._key() == other._key()

    def _key(self):
        ssh_alias = getattr(self.context, 'ssh_alias', None)
        directory = os.path.normpath(self.directory)
        return ssh_alias, directory


class Backup(PropertyManager):

    """
    :class:`Backup` objects represent a rotation subject.

    In addition to the :attr:`pathname`, :attr:`timestamp` and :attr:`week`
    properties :class:`Backup` objects support all of the attributes of
    :class:`~datetime.datetime` objects by deferring attribute access for
    unknown attributes to :attr:`timestamp`.
    """

    key_properties = 'timestamp', 'pathname'
    """
    Customize the ordering of :class:`Backup` objects.

    :class:`Backup` objects are ordered first by their :attr:`timestamp` and
    second by their :attr:`pathname`. This class variable overrides
    :attr:`~property_manager.PropertyManager.key_properties`.
    """

    @key_property
    def pathname(self):
        """The pathname of the backup (a string)."""

    @key_property
    def timestamp(self):
        """The date and time when the backup was created (a :class:`~datetime.datetime` object)."""

    @property
    def week(self):
        """The ISO week number of :attr:`timestamp` (a number)."""
        return self.timestamp.isocalendar()[1]

    def __getattr__(self, name):
        """Defer attribute access to :attr:`timestamp`."""
        return getattr(self.timestamp, name)
