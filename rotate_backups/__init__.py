# rotate-backups: Simple command line interface for backup rotation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 12, 2020
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
import shlex

# External dependencies.
from dateutil.relativedelta import relativedelta
from executor import ExternalCommandFailed
from executor.concurrent import CommandPool
from executor.contexts import RemoteContext, create_context
from humanfriendly import Timer, coerce_boolean, format_path, parse_path, pluralize
from humanfriendly.text import concatenate, split
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
from update_dotdee import ConfigLoader
from verboselogs import VerboseLogger

# Semi-standard module versioning.
__version__ = '7.0'

# Initialize a logger for this module.
logger = VerboseLogger(__name__)

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

DEFAULT_REMOVAL_COMMAND = ['rm', '-fR']
"""The default removal command (a list of strings)."""


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


def load_config_file(configuration_file=None, expand=True):
    """
    Load a configuration file with backup directories and rotation schemes.

    :param configuration_file: Override the pathname of the configuration file
                               to load (a string or :data:`None`).
    :param expand: :data:`True` to expand filename patterns to their matches,
                   :data:`False` otherwise.
    :returns: A generator of tuples with four values each:

              1. An execution context created using :mod:`executor.contexts`.
              2. The pathname of a directory with backups (a string).
              3. A dictionary with the rotation scheme.
              4. A dictionary with additional options.
    :raises: :exc:`~exceptions.ValueError` when `configuration_file` is given
             but doesn't exist or can't be loaded.

    This function is used by :class:`RotateBackups` to discover user defined
    rotation schemes and by :mod:`rotate_backups.cli` to discover directories
    for which backup rotation is configured. When `configuration_file` isn't
    given :class:`~update_dotdee.ConfigLoader` is used to search for
    configuration files in the following locations:

    - ``/etc/rotate-backups.ini`` and ``/etc/rotate-backups.d/*.ini``
    - ``~/.rotate-backups.ini`` and ``~/.rotate-backups.d/*.ini``
    - ``~/.config/rotate-backups.ini`` and ``~/.config/rotate-backups.d/*.ini``

    All of the available configuration files are loaded in the order given
    above, so that sections in user-specific configuration files override
    sections by the same name in system-wide configuration files.
    """
    expand_notice_given = False
    if configuration_file:
        loader = ConfigLoader(available_files=[configuration_file], strict=True)
    else:
        loader = ConfigLoader(program_name='rotate-backups', strict=False)
    for section in loader.section_names:
        items = dict(loader.get_options(section))
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
        # Don't override the value of the 'removal_command' property unless the
        # 'removal-command' configuration file option has a value set.
        if items.get('removal-command'):
            options['removal_command'] = shlex.split(items['removal-command'])
        # Expand filename patterns?
        if expand and location.have_wildcards:
            logger.verbose("Expanding filename pattern %s on %s ..", location.directory, location.context)
            if location.is_remote and not expand_notice_given:
                logger.notice("Expanding remote filename patterns (may be slow) ..")
                expand_notice_given = True
            for match in sorted(location.context.glob(location.directory)):
                if location.context.is_directory(match):
                    logger.verbose("Matched directory: %s", match)
                    expanded = Location(context=location.context, directory=match)
                    yield expanded, rotation_scheme, options
                else:
                    logger.verbose("Ignoring match (not a directory): %s", match)
        else:
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
        :param options: Any keyword arguments are used to set the values of
                        instance properties that support assignment
                        (:attr:`config_file`, :attr:`dry_run`,
                        :attr:`exclude_list`, :attr:`include_list`,
                        :attr:`io_scheduling_class`, :attr:`removal_command`
                        and :attr:`strict`).
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

    @mutable_property
    def force(self):
        """
        :data:`True` to continue if sanity checks fail, :data:`False` to raise an exception.

        Sanity checks are performed before backup rotation starts to ensure
        that the given location exists, is readable and is writable. If
        :attr:`removal_command` is customized then the last sanity check (that
        the given location is writable) is skipped (because custom removal
        commands imply custom semantics, see also `#18`_). If a sanity check
        fails an exception is raised, but you can set :attr:`force` to
        :data:`True` to continue with backup rotation instead (the default is
        obviously :data:`False`).

        .. seealso:: :func:`Location.ensure_exists()`,
                     :func:`Location.ensure_readable()` and
                     :func:`Location.ensure_writable()`

        .. _#18: https://github.com/xolox/python-rotate-backups/issues/18
        """
        return False

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

    @mutable_property
    def removal_command(self):
        """
        The command used to remove backups (a list of strings).

        By default the command ``rm -fR`` is used. This choice was made because
        it works regardless of whether the user's "backups to be rotated" are
        files or directories or a mixture of both.

        .. versionadded: 5.3
           This option was added as a generalization of the idea suggested in
           `pull request 11`_, which made it clear to me that being able to
           customize the removal command has its uses.

        .. _pull request 11: https://github.com/xolox/python-rotate-backups/pull/11
        """
        return DEFAULT_REMOVAL_COMMAND

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
        :returns: A list with the rotation commands
                  (:class:`~executor.ExternalCommand` objects).
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
        # Make sure the directory is writable, but only when the default
        # removal command is being used (because custom removal commands
        # imply custom semantics that we shouldn't get in the way of, see
        # https://github.com/xolox/python-rotate-backups/issues/18 for
        # more details about one such use case).
        if not self.dry_run and (self.removal_command == DEFAULT_REMOVAL_COMMAND):
            location.ensure_writable(self.force)
        most_recent_backup = sorted_backups[-1]
        # Group the backups by the rotation frequencies.
        backups_by_frequency = self.group_backups(sorted_backups)
        # Apply the user defined rotation scheme.
        self.apply_rotation_scheme(backups_by_frequency, most_recent_backup.timestamp)
        # Find which backups to preserve and why.
        backups_to_preserve = self.find_preservation_criteria(backups_by_frequency)
        # Apply the calculated rotation scheme.
        for backup in sorted_backups:
            friendly_name = backup.pathname
            if not location.is_remote:
                # Use human friendly pathname formatting for local backups.
                friendly_name = format_path(backup.pathname)
            if backup in backups_to_preserve:
                matching_periods = backups_to_preserve[backup]
                logger.info("Preserving %s (matches %s retention %s) ..",
                            friendly_name, concatenate(map(repr, matching_periods)),
                            "period" if len(matching_periods) == 1 else "periods")
            else:
                logger.info("Deleting %s ..", friendly_name)
                if not self.dry_run:
                    # Copy the list with the (possibly user defined) removal command.
                    removal_command = list(self.removal_command)
                    # Add the pathname of the backup as the final argument.
                    removal_command.append(backup.pathname)
                    # Construct the command object.
                    command = location.context.prepare(
                        command=removal_command,
                        group_by=(location.ssh_alias, location.mount_point),
                        ionice=self.io_scheduling_class,
                    )
                    rotation_commands.append(command)
                    if not prepare:
                        timer = Timer()
                        command.wait()
                        logger.verbose("Deleted %s in %s.", friendly_name, timer)
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
        for configured_location, rotation_scheme, options in load_config_file(self.config_file, expand=False):
            if configured_location.match(location):
                logger.verbose("Loading configuration for %s ..", location)
                if rotation_scheme:
                    self.rotation_scheme = rotation_scheme
                for name, value in options.items():
                    if value:
                        setattr(self, name, value)
                # Create a new Location object based on the directory of the
                # given location and the execution context of the configured
                # location, because:
                #
                # 1. The directory of the configured location may be a filename
                #    pattern whereas we are interested in the expanded name.
                #
                # 2. The execution context of the given location may lack some
                #    details of the configured location.
                return Location(
                    context=configured_location.context,
                    directory=location.directory,
                )
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
        location.ensure_readable(self.force)
        for entry in natsort(location.context.list_entries(location.directory)):
            match = TIMESTAMP_PATTERN.search(entry)
            if match:
                if self.exclude_list and any(fnmatch.fnmatch(entry, p) for p in self.exclude_list):
                    logger.verbose("Excluded %s (it matched the exclude list).", entry)
                elif self.include_list and not any(fnmatch.fnmatch(entry, p) for p in self.include_list):
                    logger.verbose("Excluded %s (it didn't match the include list).", entry)
                else:
                    try:
                        backups.append(Backup(
                            pathname=os.path.join(location.directory, entry),
                            timestamp=datetime.datetime(*(int(group, 10) for group in match.groups('0'))),
                        ))
                    except ValueError as e:
                        logger.notice("Ignoring %s due to invalid date (%s).", entry, e)
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
        return self.context.have_ionice

    @lazy_property
    def have_wildcards(self):
        """:data:`True` if :attr:`directory` is a filename pattern, :data:`False` otherwise."""
        return '*' in self.directory

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

    def ensure_exists(self, override=False):
        """
        Sanity check that the location exists.

        :param override: :data:`True` to log a message, :data:`False` to raise
                         an exception (when the sanity check fails).
        :returns: :data:`True` if the sanity check succeeds,
                  :data:`False` if it fails (and `override` is :data:`True`).
        :raises: :exc:`~exceptions.ValueError` when the sanity
                 check fails and `override` is :data:`False`.

        .. seealso:: :func:`ensure_readable()`, :func:`ensure_writable()` and :func:`add_hints()`
        """
        if self.context.is_directory(self.directory):
            logger.verbose("Confirmed that location exists: %s", self)
            return True
        elif override:
            logger.notice("It seems %s doesn't exist but --force was given so continuing anyway ..", self)
            return False
        else:
            message = "It seems %s doesn't exist or isn't accessible due to filesystem permissions!"
            raise ValueError(self.add_hints(message % self))

    def ensure_readable(self, override=False):
        """
        Sanity check that the location exists and is readable.

        :param override: :data:`True` to log a message, :data:`False` to raise
                         an exception (when the sanity check fails).
        :returns: :data:`True` if the sanity check succeeds,
                  :data:`False` if it fails (and `override` is :data:`True`).
        :raises: :exc:`~exceptions.ValueError` when the sanity
                 check fails and `override` is :data:`False`.

        .. seealso:: :func:`ensure_exists()`, :func:`ensure_writable()` and :func:`add_hints()`
        """
        # Only sanity check that the location is readable when its
        # existence has been confirmed, to avoid multiple notices
        # about the same underlying problem.
        if self.ensure_exists(override):
            if self.context.is_readable(self.directory):
                logger.verbose("Confirmed that location is readable: %s", self)
                return True
            elif override:
                logger.notice("It seems %s isn't readable but --force was given so continuing anyway ..", self)
            else:
                message = "It seems %s isn't readable!"
                raise ValueError(self.add_hints(message % self))
        return False

    def ensure_writable(self, override=False):
        """
        Sanity check that the directory exists and is writable.

        :param override: :data:`True` to log a message, :data:`False` to raise
                         an exception (when the sanity check fails).
        :returns: :data:`True` if the sanity check succeeds,
                  :data:`False` if it fails (and `override` is :data:`True`).
        :raises: :exc:`~exceptions.ValueError` when the sanity
                 check fails and `override` is :data:`False`.

        .. seealso:: :func:`ensure_exists()`, :func:`ensure_readable()` and :func:`add_hints()`
        """
        # Only sanity check that the location is readable when its
        # existence has been confirmed, to avoid multiple notices
        # about the same underlying problem.
        if self.ensure_exists(override):
            if self.context.is_writable(self.directory):
                logger.verbose("Confirmed that location is writable: %s", self)
                return True
            elif override:
                logger.notice("It seems %s isn't writable but --force was given so continuing anyway ..", self)
            else:
                message = "It seems %s isn't writable!"
                raise ValueError(self.add_hints(message % self))
        return False

    def add_hints(self, message):
        """
        Provide hints about failing sanity checks.

        :param message: The message to the user (a string).
        :returns: The message including hints (a string).

        When superuser privileges aren't being used a hint about the
        ``--use-sudo`` option will be added (in case a sanity check failed
        because we don't have permission to one of the parent directories).

        In all cases a hint about the ``--force`` option is added (in case the
        sanity checks themselves are considered the problem, which is obviously
        up to the operator to decide).

        .. seealso:: :func:`ensure_exists()`, :func:`ensure_readable()` and :func:`ensure_writable()`
        """
        sentences = [message]
        if not self.context.have_superuser_privileges:
            sentences.append("If filesystem permissions are the problem consider using the --use-sudo option.")
        sentences.append("To continue despite this failing sanity check you can use --force.")
        return " ".join(sentences)

    def match(self, location):
        """
        Check if the given location "matches".

        :param location: The :class:`Location` object to try to match.
        :returns: :data:`True` if the two locations are on the same system and
                  the :attr:`directory` can be matched as a filename pattern or
                  a literal match on the normalized pathname.
        """
        if self.ssh_alias != location.ssh_alias:
            # Never match locations on other systems.
            return False
        elif self.have_wildcards:
            # Match filename patterns using fnmatch().
            return fnmatch.fnmatch(location.directory, self.directory)
        else:
            # Compare normalized directory pathnames.
            self = os.path.normpath(self.directory)
            other = os.path.normpath(location.directory)
            return self == other

    def __str__(self):
        """Render a simple human readable representation of a location."""
        return '%s:%s' % (self.ssh_alias, self.directory) if self.ssh_alias else self.directory


class Backup(PropertyManager):

    """:class:`Backup` objects represent a rotation subject."""

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
