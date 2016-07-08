# rotate-backups: Simple command line interface for backup rotation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 9, 2016
# URL: https://github.com/xolox/python-rotate-backups

"""
Usage: rotate-backups [OPTIONS] [DIRECTORY, ..]

Easy rotation of backups based on the Python package by the same name.

To use this program you specify a rotation scheme via (a combination of) the
--hourly, --daily, --weekly, --monthly and/or --yearly options and the
directory (or directories) containing backups to rotate as one or more
positional arguments.

You can rotate backups on a remote system over SSH by prefixing a DIRECTORY
with an SSH alias and separating the two with a colon (similar to how rsync
accepts remote locations).

Instead of specifying directories and a rotation scheme on the command line you
can also add them to a configuration file. For more details refer to the online
documentation (see also the --config option).

Please use the --dry-run option to test the effect of the specified rotation
scheme before letting this program loose on your precious backups! If you don't
test the results using the dry run mode and this program eats more backups than
intended you have no right to complain ;-).

Supported options:

  -H, --hourly=COUNT

    Set the number of hourly backups to preserve during rotation:

    - If COUNT is a number it gives the number of hourly backups to preserve,
      starting from the most recent hourly backup and counting back in time.
    - Alternatively you can provide an expression that will be evaluated to get
      a number (e.g. if COUNT is `7 * 2' the result would be 14).
    - You can also pass `always' for COUNT, in this case all hourly backups are
      preserved.
    - By default no hourly backups are preserved.

  -d, --daily=COUNT

    Set the number of daily backups to preserve during rotation. Refer to the
    usage of the -H, --hourly option for details.

  -w, --weekly=COUNT

    Set the number of weekly backups to preserve during rotation. Refer to the
    usage of the -H, --hourly option for details.

  -m, --monthly=COUNT

    Set the number of monthly backups to preserve during rotation. Refer to the
    usage of the -H, --hourly option for details.

  -y, --yearly=COUNT

    Set the number of yearly backups to preserve during rotation. Refer to the
    usage of the -H, --hourly option for details.

  -I, --include=PATTERN

    Only process backups that match the shell pattern given by PATTERN. This
    argument can be repeated. Make sure to quote PATTERN so the shell doesn't
    expand the pattern before it's received by rotate-backups.

  -x, --exclude=PATTERN

    Don't process backups that match the shell pattern given by PATTERN. This
    argument can be repeated. Make sure to quote PATTERN so the shell doesn't
    expand the pattern before it's received by rotate-backups.

  -r, --relaxed

    By default the time window for each rotation scheme is enforced (this is
    referred to as strict rotation) but the -r, --relaxed option can be used
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
      use the -r, --relaxed option in order to preserve more backups.

  -i, --ionice=CLASS

    Use the `ionice' program to set the I/O scheduling class and priority of
    the `rm' invocations used to remove backups. CLASS is expected to be one of
    the values `idle', `best-effort' or `realtime'. Refer to the man page of
    the `ionice' program for details about these values.

  -c, --config=PATH

    Load configuration from the pathname given by PATH. If this option isn't
    given two default locations are checked: `~/.rotate-backups.ini' and
    `/etc/rotate-backups.ini'. The first of these two configuration files to
    exist is loaded. For more details refer to the online documentation.

  -u, --use-sudo

    Enable the use of `sudo' to rotate backups in directories that are not
    readable and/or writable for the current user (or the user logged in to a
    remote system over SSH).

  -n, --dry-run

    Don't make any changes, just print what would be done. This makes it easy
    to evaluate the impact of a rotation scheme without losing any backups.

  -v, --verbose

    Make more noise (increase logging verbosity). Can be repeated.

  -q, --quiet

    Make less noise (decrease logging verbosity). Can be repeated.

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import sys

# External dependencies.
import coloredlogs
from humanfriendly import concatenate, parse_path, pluralize
from humanfriendly.terminal import usage
from verboselogs import VerboseLogger

# Modules included in our package.
from rotate_backups import (
    RotateBackups,
    coerce_location,
    coerce_retention_period,
    load_config_file,
)

# Initialize a logger.
logger = VerboseLogger(__name__)


def main():
    """Command line interface for the ``rotate-backups`` program."""
    coloredlogs.install(syslog=True)
    # Command line option defaults.
    config_file = None
    dry_run = False
    exclude_list = []
    include_list = []
    io_scheduling_class = None
    rotation_scheme = {}
    use_sudo = False
    strict = True
    # Internal state.
    selected_locations = []
    # Parse the command line arguments.
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'H:d:w:m:y:I:x:ri:c:r:unvqh', [
            'hourly=', 'daily=', 'weekly=', 'monthly=', 'yearly=', 'include=',
            'exclude=', 'relaxed', 'ionice=', 'config=', 'use-sudo', 'dry-run',
            'verbose', 'quiet', 'help',
        ])
        for option, value in options:
            if option in ('-H', '--hourly'):
                rotation_scheme['hourly'] = coerce_retention_period(value)
            elif option in ('-d', '--daily'):
                rotation_scheme['daily'] = coerce_retention_period(value)
            elif option in ('-w', '--weekly'):
                rotation_scheme['weekly'] = coerce_retention_period(value)
            elif option in ('-m', '--monthly'):
                rotation_scheme['monthly'] = coerce_retention_period(value)
            elif option in ('-y', '--yearly'):
                rotation_scheme['yearly'] = coerce_retention_period(value)
            elif option in ('-I', '--include'):
                include_list.append(value)
            elif option in ('-x', '--exclude'):
                exclude_list.append(value)
            elif option in ('-r', '--relaxed'):
                strict = False
            elif option in ('-i', '--ionice'):
                value = value.lower().strip()
                expected = ('idle', 'best-effort', 'realtime')
                if value not in expected:
                    msg = "Invalid I/O scheduling class! (got %r while valid options are %s)"
                    raise Exception(msg % (value, concatenate(expected)))
                io_scheduling_class = value
            elif option in ('-c', '--config'):
                config_file = parse_path(value)
            elif option in ('-u', '--use-sudo'):
                use_sudo = True
            elif option in ('-n', '--dry-run'):
                logger.info("Performing a dry run (because of %s option) ..", option)
                dry_run = True
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-q', '--quiet'):
                coloredlogs.decrease_verbosity()
            elif option in ('-h', '--help'):
                usage(__doc__)
                return
            else:
                assert False, "Unhandled option! (programming error)"
        if rotation_scheme:
            logger.verbose("Rotation scheme defined on command line: %s", rotation_scheme)
        if arguments:
            # Rotation of the locations given on the command line.
            selected_locations.extend(coerce_location(value, sudo=use_sudo) for value in arguments)
            location_source = 'command line arguments'
        else:
            # Rotation of all configured locations.
            selected_locations.extend(location for location, rotation_scheme, options in load_config_file(config_file))
            location_source = 'configuration file'
        # Inform the user which location(s) will be rotated.
        if selected_locations:
            logger.verbose("Selected %s based on %s:",
                           pluralize(len(selected_locations), "location"),
                           location_source)
            for number, location in enumerate(selected_locations, start=1):
                logger.verbose(" %i. %s", number, location)
        else:
            # Show the usage message when no directories are given nor configured.
            logger.verbose("No location(s) to rotate selected.")
            usage(__doc__)
            return
    except Exception as e:
        logger.error("%s", e)
        sys.exit(1)
    # Rotate the backups in the selected directories.
    for location in selected_locations:
        RotateBackups(
            rotation_scheme=rotation_scheme,
            include_list=include_list,
            exclude_list=exclude_list,
            io_scheduling_class=io_scheduling_class,
            dry_run=dry_run,
            config_file=config_file,
            strict=strict,
        ).rotate_backups(location)
