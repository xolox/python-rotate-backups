# rotate-backups: Simple command line interface for backup rotation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: October 31, 2016
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
import numbers
import os
import re

# External dependencies.
from dateutil.relativedelta import relativedelta
from executor import ExternalCommandFailed
from executor.concurrent import CommandPool
from executor.contexts import RemoteContext, create_context
from humanfriendly import Timer, coerce_boolean, format_path, parse_path, pluralize
from humanfriendly.text import compact, concatenate, split
from natsort import natsort
from property_manager import (
    PropertyManager,
    cached_property,
    key_property,
    lazy_property,
    mutable_property,
    required_property,
)
from simpleeval import simple_eval
from six import string_types
from six.moves import configparser
from verboselogs import VerboseLogger

# Semi-standard module versioning.
__version__ = '4.3'

# Initialize a logger for this module.
logger = VerboseLogger(__name__)

GLOBAL_CONFIG_FILE = '/etc/rotate-backups.ini'
"""The pathname of the system wide configuration file (a string)."""

LOCAL_CONFIG_FILE = '~/.rotate-backups.ini'
"""The pathname of the user specific configuration file (a string)."""

ORDERED_FREQUENCIES = (
    ('minutely', relativedelta(minutes=1)),
    ('hourly', relativedelta(hours=1)),
    ('daily', relativedelta(days=1)),
    ('weekly', relativedelta(weeks=1)),
    ('monthly', relativedelta(months=1)),
    ('yearly', relativedelta(years=1)),
)
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
    # Location objects pass through untouched.
    if not isinstance(value, Location):
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
        # Create the location object.
        value = Location(
            context=create_context(**options),
            directory=parse_path(directory),
        )
    return value


def coerce_retention_period(value):
    """
    Coerce a retention period to a Python value.

    :param value: A string containing the text 'always', a number or
                  an expression that can be evaluated to a number.
    :returns: A number or the string 'always'.
    :raises: :exc:`~exceptions.ValueError` when the string can't be coerced.
    """
    # Numbers pass through untouched.
    if not isinstance(value, numbers.Number):
        # Other values are expected to be strings.
        if not isinstance(value, string_types):
            msg = "Expected string, got %s instead!"
            raise ValueError(msg % type(value))
        # Check for the literal string `always'.
        value = value.strip()
        if value.lower() == 'always':
            value = 'always'
        else:
            # Evaluate other strings as expressions.
            value = simple_eval(value)
            if not isinstance(value, numbers.Number):
                msg = "Expected numeric result, got %s instead!"
                raise ValueError(msg % type(value))
    return value


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
                       strict=coerce_boolean(items.get('strict', 'yes')),
                       prefer_recent=coerce_boolean(items.get('prefer-recent', 'no')))
        yield location, rotation_scheme, options


def rotate_backups(directory, rotation_scheme, **options):
    """
    Rotate the backups in a directory according to a flexible rotation scheme.

    .. note:: This function exists to preserve backwards compatibility with
              older versions of the `rotate-backups` package where all of the
              logic was exposed as a single function. Please refer to the
              documentation of the :class:`RotateBackups` initializer and the
              :func:`~RotateBackups.rotate_backups()` method for an explanation
              of this function's parameters.
    """
    program = RotateBackups(rotation_scheme=rotation_scheme, **options)
    program.rotate_backups(directory)


class RotateBackups(PropertyManager):

    """Python API for the ``rotate-backups`` program."""

    def __init__(self, rotation_scheme, **options):
        """
        Initialize a :class:`RotateBackups` object.

        :param rotation_scheme: Used to set :attr:`rotation_scheme`.
        :param options: Any keyword arguments are used to set the values of the
                        properties :attr:`config_file`, :attr:`dry_run`,
                        :attr:`exclude_list`, :attr:`include_list`,
                        :attr:`io_scheduling_class` and :attr:`strict`.
        """
        options.update(rotation_scheme=rotation_scheme)
        super(RotateBackups, self).__init__(**options)

    @mutable_property
    def config_file(self):
        """
        The pathname of a configuration file (a string or :data:`None`).

        When this property is set :func:`rotate_backups()` will use
        :func:`load_config_file()` to give the user (operator) a chance to set
        the rotation scheme and other options via a configuration file.
        """

    @mutable_property
    def dry_run(self):
        """
        :data:`True` to simulate rotation, :data:`False` to actually remove backups (defaults to :data:`False`).

        If this is :data:`True` then :func:`rotate_backups()` won't make any
        actual changes, which provides a 'preview' of the effect of the
        rotation scheme. Right now this is only useful in the command line
        interface because there's no return value.
        """
        return False

    @cached_property(writable=True)
    def exclude_list(self):
        """
        Filename patterns to exclude specific backups (a list of strings).

        This is a list of strings with :mod:`fnmatch` patterns. When
        :func:`collect_backups()` encounters a backup whose name matches any of
        the patterns in this list the backup will be ignored, *even if it also
        matches the include list* (it's the only logical way to combine both
        lists).

        :see also: :attr:`include_list`
        """
        return []

    @cached_property(writable=True)
    def include_list(self):
        """
        Filename patterns to select specific backups (a list of strings).

        This is a list of strings with :mod:`fnmatch` patterns. When it's not
        empty :func:`collect_backups()` will only collect backups whose name
        matches a pattern in the list.

        :see also: :attr:`exclude_list`
        """
        return []

    @mutable_property
    def io_scheduling_class(self):
        """
        The I/O scheduling class for backup rotation (a string or :data:`None`).

        When this property is set (and :attr:`~Location.have_ionice` is
        :data:`True`) then ionice_ will be used to set the I/O scheduling class
        for backup rotation. This can be useful to reduce the impact of backup
        rotation on the rest of the system.

        The value of this property is expected to be one of the strings 'idle',
        'best-effort' or 'realtime'.

        .. _ionice: https://linux.die.net/man/1/ionice
        """

    @mutable_property
    def prefer_recent(self):
        """
        Whether to prefer older or newer backups in each time slot (a boolean).

        Defaults to :data:`False` which means the oldest backup in each time
        slot (an hour, a day, etc.) is preserved while newer backups in the
        time slot are removed. You can set this to :data:`True` if you would
        like to preserve the newest backup in each time slot instead.
        """
        return False

    @required_property
    def rotation_scheme(self):
        """
        The rotation scheme to apply to backups (a dictionary).

        Each key in this dictionary defines a rotation frequency (one of the
        strings 'minutely', 'hourly', 'daily', 'weekly', 'monthly' and
        'yearly') and each value defines a retention count:

        - An integer value represents the number of backups to preserve in the
          given rotation frequency, starting from the most recent backup and
          counting back in time.

        - The string 'always' means all backups in the given rotation frequency
          are preserved (this is intended to be used with the biggest frequency
          in the rotation scheme, e.g. yearly).

        No backups are preserved for rotation frequencies that are not present
        in the dictionary.
        """

    @mutable_property
    def strict(self):
        """
        Whether to enforce the time window for each rotation frequency (a boolean, defaults to :data:`True`).

        The easiest way to explain the difference between strict and relaxed
        rotation is using an example:

        - If :attr:`strict` is :data:`True` and the number of hourly backups to
          preserve is three, only backups created in the relevant time window
          (the hour of the most recent backup and the two hours leading up to
          that) will match the hourly frequency.

        - If :attr:`strict` is :data:`False` then the three most recent backups
          will all match the hourly frequency (and thus be preserved),
          regardless of the calculated time window.

        If the explanation above is not clear enough, here's a simple way to
        decide whether you want to customize this behavior:

        - If your backups are created at regular intervals and you never miss
          an interval then the default (:data:`True`) is most likely fine.

        - If your backups are created at irregular intervals then you may want
          to set :attr:`strict` to :data:`False` to convince
          :class:`RotateBackups` to preserve more backups.
        """
        return True

    def rotate_concurrent(self, *locations, **kw):
        """
        Rotate the backups in the given locations concurrently.

        :param locations: One or more values accepted by :func:`coerce_location()`.
        :param kw: Any keyword arguments are passed on to :func:`rotate_backups()`.

        This function uses :func:`rotate_backups()` to prepare rotation
        commands for the given locations and then it removes backups in
        parallel, one backup per mount point at a time.

        The idea behind this approach is that parallel rotation is most useful
        when the files to be removed are on different disks and so multiple
        devices can be utilized at the same time.

        Because mount points are per system :func:`rotate_concurrent()` will
        also parallelize over backups located on multiple remote systems.
        """
        timer = Timer()
        pool = CommandPool(concurrency=10)
        logger.info("Scanning %s ..", pluralize(len(locations), "backup location"))
        for location in locations:
            for cmd in self.rotate_backups(location, prepare=True, **kw):
                pool.add(cmd)
        if pool.num_commands > 0:
            backups = pluralize(pool.num_commands, "backup")
            logger.info("Preparing to rotate %s (in parallel) ..", backups)
            pool.run()
            logger.info("Successfully rotated %s in %s.", backups, timer)

    def rotate_backups(self, location, load_config=True, prepare=False):
        """
        Rotate the backups in a directory according to a flexible rotation scheme.

        :param location: Any value accepted by :func:`coerce_location()`.
        :param load_config: If :data:`True` (so by default) the rotation scheme
                            and other options can be customized by the user in
                            a configuration file. In this case the caller's
                            arguments are only used when the configuration file
                            doesn't define a configuration for the location.
        :param prepare: If this is :data:`True` (not the default) then
                        :func:`rotate_backups()` will prepare the required
                        rotation commands without running them.
        :returns: A list with the rotation commands (:class:`ExternalCommand`
                  objects).
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
        rotation_commands = []
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
                    command_line = ['rm', '-Rf', backup.pathname]
                    if self.io_scheduling_class and location.have_ionice:
                        command_line = ['ionice', '--class', self.io_scheduling_class] + command_line
                    group_by = (location.ssh_alias, location.mount_point)
                    command = location.context.prepare(*command_line, group_by=group_by)
                    rotation_commands.append(command)
                    if not prepare:
                        timer = Timer()
                        command.wait()
                        logger.verbose("Deleted %s in %s.", format_path(backup.pathname), timer)
        if len(backups_to_preserve) == len(sorted_backups):
            logger.info("Nothing to do! (all backups preserved)")
        return rotation_commands

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
            backups_by_frequency['minutely'][(b.year, b.month, b.day, b.hour, b.minute)].append(b)
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
                # Reduce the number of backups in each time slot of this
                # rotation frequency to a single backup (the oldest one or the
                # newest one).
                for period, backups_in_period in backups.items():
                    index = -1 if self.prefer_recent else 0
                    selected_backup = sorted(backups_in_period)[index]
                    backups[period] = [selected_backup]
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

    @lazy_property
    def have_ionice(self):
        """:data:`True` when ionice_ is available, :data:`False` otherwise."""
        return self.context.test('which', 'ionice')

    @lazy_property
    def mount_point(self):
        """
        The pathname of the mount point of :attr:`directory` (a string or :data:`None`).

        If the ``stat --format=%m ...`` command that is used to determine the
        mount point fails, the value of this property defaults to :data:`None`.
        This enables graceful degradation on e.g. Mac OS X whose ``stat``
        implementation is rather bare bones compared to GNU/Linux.
        """
        try:
            return self.context.capture('stat', '--format=%m', self.directory, silent=True)
        except ExternalCommandFailed:
            return None

    @lazy_property
    def is_remote(self):
        """:data:`True` if the location is remote, :data:`False` otherwise."""
        return isinstance(self.context, RemoteContext)

    @lazy_property
    def ssh_alias(self):
        """The SSH alias of a remote location (a string or :data:`None`)."""
        return self.context.ssh_alias if self.is_remote else None

    @property
    def key_properties(self):
        """
        A list of strings with the names of the :attr:`~custom_property.key` properties.

        Overrides :attr:`~property_manager.PropertyManager.key_properties` to
        customize the ordering of :class:`Location` objects so that they are
        ordered first by their :attr:`ssh_alias` and second by their
        :attr:`directory`.
        """
        return ['ssh_alias', 'directory'] if self.is_remote else ['directory']

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
        return '%s:%s' % (self.ssh_alias, self.directory) if self.ssh_alias else self.directory


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
