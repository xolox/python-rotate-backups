# rotate-backups: Simple command line interface for backup rotation.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 19, 2015
# URL: https://github.com/xolox/python-rotate-backups

"""
Usage: rotate-backups [OPTIONS] DIRECTORY..

Easy rotation of backups based on the Python package by the same name. To use
this program you specify a rotation scheme via (a combination of) the --hourly,
--daily, --weekly, --monthly and/or --yearly options and specify the directory
(or multiple directories) containing backups to rotate as one or more
positional arguments.

Please use the --dry-run option to test the effect of the specified rotation
scheme before letting this program loose on your precious backups! If you don't
test the results using the dry run mode and this program eats more backups than
intended you have no right to complain ;-).

Supported options:

  -H, --hourly=COUNT

    Set the number of hourly backups to preserve during rotation:

    - If COUNT is an integer it gives the number of hourly backups to preserve,
      starting from the most recent hourly backup and counting back in time.
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

  -i, --ionice=CLASS

    Use the `ionice' program to set the I/O scheduling class and priority of
    the `rm' invocations used to remove backups. CLASS is expected to be one of
    the values `idle', `best-effort' or `realtime'. Refer to the man page of
    the `ionice' program for details about these values.

  -n, --dry-run

    Don't make any changes, just print what would be done. This makes it easy
    to evaluate the impact of a rotation scheme without losing any backups.

  -v, --verbose

    Make more noise (increase logging verbosity).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import logging
import logging.handlers
import os
import sys

# External dependencies.
import coloredlogs
from humanfriendly import concatenate
from humanfriendly.terminal import usage

# Modules included in our package.
from rotate_backups import rotate_backups

# Initialize a logger.
logger = logging.getLogger(__name__)


def main():
    """Command line interface for the ``rotate-backups`` program."""
    coloredlogs.install()
    if os.path.exists('/dev/log'):
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        handler.setFormatter(logging.Formatter('%(module)s[%(process)d] %(levelname)s %(message)s'))
        logger.addHandler(handler)
    # Command line option defaults.
    dry_run = False
    exclude_list = []
    include_list = []
    io_scheduling_class = None
    rotation_scheme = {}
    # Parse the command line arguments.
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'H:d:w:m:y:I:x:i:nvh', [
            'hourly=', 'daily=', 'weekly=', 'monthly=', 'yearly=', 'include=',
            'exclude=', 'ionice=', 'dry-run', 'verbose', 'help',
        ])
        for option, value in options:
            if option in ('-H', '--hourly'):
                rotation_scheme['hourly'] = cast_to_retention_period(value)
            elif option in ('-d', '--daily'):
                rotation_scheme['daily'] = cast_to_retention_period(value)
            elif option in ('-w', '--weekly'):
                rotation_scheme['weekly'] = cast_to_retention_period(value)
            elif option in ('-m', '--monthly'):
                rotation_scheme['monthly'] = cast_to_retention_period(value)
            elif option in ('-y', '--yearly'):
                rotation_scheme['yearly'] = cast_to_retention_period(value)
            elif option in ('-I', '--include'):
                include_list.append(value)
            elif option in ('-x', '--exclude'):
                exclude_list.append(value)
            elif option in ('-i', '--ionice'):
                value = value.lower().strip()
                expected = ('idle', 'best-effort', 'realtime')
                if value not in expected:
                    msg = "Invalid I/O scheduling class! (got %r while valid options are %s)"
                    raise Exception(msg % (value, concatenate(expected)))
                io_scheduling_class = value
            elif option in ('-n', '--dry-run'):
                logger.info("Performing a dry run (because of %s option) ..", option)
                dry_run = True
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-h', '--help'):
                usage(__doc__)
                return
            else:
                assert False, "Unhandled option! (programming error)"
        logger.debug("Parsed rotation scheme: %s", rotation_scheme)
        if not arguments:
            usage(__doc__)
            return
        for pathname in arguments:
            if not os.path.isdir(pathname):
                msg = "Directory doesn't exist! (%s)"
                raise Exception(msg % pathname)
    except Exception as e:
        logger.error("%s", e)
        sys.exit(1)
    # Rotate the backups in the given directories.
    for pathname in arguments:
        rotate_backups(
            directory=pathname,
            rotation_scheme=rotation_scheme,
            include_list=include_list,
            exclude_list=exclude_list,
            io_scheduling_class=io_scheduling_class,
            dry_run=dry_run,
        )


def cast_to_retention_period(value):
    """Cast a command line argument to a retention period (the string 'always' or an integer)."""
    value = value.strip()
    if value.lower() == 'always':
        return 'always'
    elif value.isdigit():
        return int(value)
    else:
        raise Exception("Invalid number %s!" % value)
