rotate-backups: Simple command line interface for backup rotation
=================================================================

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

.. contents::
   :local:

Features
--------

**Dry run mode**
  **Use it.** I'm serious. If you don't and ``rotate-backups`` eats more
  backups than intended you have no right to complain ;-)

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

Status
------

Note the version number 0.1. That's not to say that ``rotate-backups`` doesn't
already do exactly what I want it to, I just don't fully trust it yet so won't
give it a 1.0 version.

Also, I haven't written automated tests to very correctness yet, so until then
please feel free to use the dry run mode to verify that what will happen is
what you expect.

Getting started
---------------

To install:

.. code-block::

   $ pip install rotate-backups

To run:

.. code-block::

   $ rotate-backups --help
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

The last section (see below) contains a real example that shows how rotation
frequencies can be combined.

Contact
-------

The latest version of ``rotate-backups`` is available on PyPI_ and GitHub_. For
bug reports please create an issue on GitHub_. If you have questions,
suggestions, etc. feel free to send me an e-mail at `peter@peterodding.com`_.

License
-------

This software is licensed under the `MIT license`_.

© 2014 Peter Odding.

Real example
------------

.. code-block::

   $ rotate-backups --hourly=24 --daily=7 --weekly=4 --monthly=12 --yearly=always sample-backups/
   INFO Scanning directory for timestamped backups: sample-backups/
   INFO Found 266 timestamped backups in sample-backups/.
   INFO Preserving sample-backups/2013-10-10@20:07 (matches retention period(s) 'monthly' and 'yearly') ..
   INFO Deleting directory sample-backups/2013-10-11@20:06 ..
   INFO Deleting directory sample-backups/2013-10-12@20:06 ..
   INFO Deleting directory sample-backups/2013-10-13@20:07 ..
   INFO Deleting directory sample-backups/2013-10-14@20:06 ..
   INFO Deleting directory sample-backups/2013-10-15@20:06 ..
   INFO Deleting directory sample-backups/2013-10-16@20:06 ..
   INFO Deleting directory sample-backups/2013-10-17@20:07 ..
   INFO Deleting directory sample-backups/2013-10-18@20:06 ..
   INFO Deleting directory sample-backups/2013-10-19@20:06 ..
   INFO Deleting directory sample-backups/2013-10-20@20:05 ..
   INFO Deleting directory sample-backups/2013-10-21@20:07 ..
   INFO Deleting directory sample-backups/2013-10-22@20:06 ..
   INFO Deleting directory sample-backups/2013-10-23@20:06 ..
   INFO Deleting directory sample-backups/2013-10-24@20:06 ..
   INFO Deleting directory sample-backups/2013-10-25@20:06 ..
   INFO Deleting directory sample-backups/2013-10-26@20:06 ..
   INFO Deleting directory sample-backups/2013-10-27@20:06 ..
   INFO Deleting directory sample-backups/2013-10-28@20:07 ..
   INFO Deleting directory sample-backups/2013-10-29@20:06 ..
   INFO Deleting directory sample-backups/2013-10-30@20:07 ..
   INFO Deleting directory sample-backups/2013-10-31@20:07 ..
   INFO Preserving sample-backups/2013-11-01@20:06 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2013-11-02@20:06 ..
   INFO Deleting directory sample-backups/2013-11-03@20:05 ..
   INFO Deleting directory sample-backups/2013-11-04@20:07 ..
   INFO Deleting directory sample-backups/2013-11-05@20:06 ..
   INFO Deleting directory sample-backups/2013-11-06@20:07 ..
   INFO Deleting directory sample-backups/2013-11-07@20:07 ..
   INFO Deleting directory sample-backups/2013-11-08@20:07 ..
   INFO Deleting directory sample-backups/2013-11-09@20:06 ..
   INFO Deleting directory sample-backups/2013-11-10@20:06 ..
   INFO Deleting directory sample-backups/2013-11-11@20:07 ..
   INFO Deleting directory sample-backups/2013-11-12@20:06 ..
   INFO Deleting directory sample-backups/2013-11-13@20:07 ..
   INFO Deleting directory sample-backups/2013-11-14@20:06 ..
   INFO Deleting directory sample-backups/2013-11-15@20:07 ..
   INFO Deleting directory sample-backups/2013-11-16@20:06 ..
   INFO Deleting directory sample-backups/2013-11-17@20:07 ..
   INFO Deleting directory sample-backups/2013-11-18@20:07 ..
   INFO Deleting directory sample-backups/2013-11-19@20:06 ..
   INFO Deleting directory sample-backups/2013-11-20@20:07 ..
   INFO Deleting directory sample-backups/2013-11-21@20:06 ..
   INFO Deleting directory sample-backups/2013-11-22@20:06 ..
   INFO Deleting directory sample-backups/2013-11-23@20:07 ..
   INFO Deleting directory sample-backups/2013-11-24@20:06 ..
   INFO Deleting directory sample-backups/2013-11-25@20:07 ..
   INFO Deleting directory sample-backups/2013-11-26@20:06 ..
   INFO Deleting directory sample-backups/2013-11-27@20:07 ..
   INFO Deleting directory sample-backups/2013-11-28@20:06 ..
   INFO Deleting directory sample-backups/2013-11-29@20:07 ..
   INFO Deleting directory sample-backups/2013-11-30@20:06 ..
   INFO Preserving sample-backups/2013-12-01@20:07 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2013-12-02@20:06 ..
   INFO Deleting directory sample-backups/2013-12-03@20:07 ..
   INFO Deleting directory sample-backups/2013-12-04@20:07 ..
   INFO Deleting directory sample-backups/2013-12-05@20:06 ..
   INFO Deleting directory sample-backups/2013-12-06@20:07 ..
   INFO Deleting directory sample-backups/2013-12-07@20:06 ..
   INFO Deleting directory sample-backups/2013-12-08@20:06 ..
   INFO Deleting directory sample-backups/2013-12-09@20:07 ..
   INFO Deleting directory sample-backups/2013-12-10@20:06 ..
   INFO Deleting directory sample-backups/2013-12-11@20:07 ..
   INFO Deleting directory sample-backups/2013-12-12@20:07 ..
   INFO Deleting directory sample-backups/2013-12-13@20:07 ..
   INFO Deleting directory sample-backups/2013-12-14@20:06 ..
   INFO Deleting directory sample-backups/2013-12-15@20:06 ..
   INFO Deleting directory sample-backups/2013-12-16@20:07 ..
   INFO Deleting directory sample-backups/2013-12-17@20:06 ..
   INFO Deleting directory sample-backups/2013-12-18@20:07 ..
   INFO Deleting directory sample-backups/2013-12-19@20:07 ..
   INFO Deleting directory sample-backups/2013-12-20@20:08 ..
   INFO Deleting directory sample-backups/2013-12-21@20:06 ..
   INFO Deleting directory sample-backups/2013-12-22@20:07 ..
   INFO Deleting directory sample-backups/2013-12-23@20:08 ..
   INFO Deleting directory sample-backups/2013-12-24@20:07 ..
   INFO Deleting directory sample-backups/2013-12-25@20:07 ..
   INFO Deleting directory sample-backups/2013-12-26@20:06 ..
   INFO Deleting directory sample-backups/2013-12-27@20:07 ..
   INFO Deleting directory sample-backups/2013-12-28@20:06 ..
   INFO Deleting directory sample-backups/2013-12-29@20:07 ..
   INFO Deleting directory sample-backups/2013-12-30@20:07 ..
   INFO Deleting directory sample-backups/2013-12-31@20:06 ..
   INFO Preserving sample-backups/2014-01-01@20:07 (matches retention period(s) 'monthly' and 'yearly') ..
   INFO Deleting directory sample-backups/2014-01-02@20:07 ..
   INFO Deleting directory sample-backups/2014-01-03@20:08 ..
   INFO Deleting directory sample-backups/2014-01-04@20:06 ..
   INFO Deleting directory sample-backups/2014-01-05@20:07 ..
   INFO Deleting directory sample-backups/2014-01-06@20:07 ..
   INFO Deleting directory sample-backups/2014-01-07@20:06 ..
   INFO Deleting directory sample-backups/2014-01-08@20:09 ..
   INFO Deleting directory sample-backups/2014-01-09@20:07 ..
   INFO Deleting directory sample-backups/2014-01-10@20:07 ..
   INFO Deleting directory sample-backups/2014-01-11@20:06 ..
   INFO Deleting directory sample-backups/2014-01-12@20:07 ..
   INFO Deleting directory sample-backups/2014-01-13@20:07 ..
   INFO Deleting directory sample-backups/2014-01-14@20:07 ..
   INFO Deleting directory sample-backups/2014-01-15@20:06 ..
   INFO Deleting directory sample-backups/2014-01-16@20:06 ..
   INFO Deleting directory sample-backups/2014-01-17@20:04 ..
   INFO Deleting directory sample-backups/2014-01-18@20:02 ..
   INFO Deleting directory sample-backups/2014-01-19@20:02 ..
   INFO Deleting directory sample-backups/2014-01-20@20:04 ..
   INFO Deleting directory sample-backups/2014-01-21@20:04 ..
   INFO Deleting directory sample-backups/2014-01-22@20:04 ..
   INFO Deleting directory sample-backups/2014-01-23@20:05 ..
   INFO Deleting directory sample-backups/2014-01-24@20:08 ..
   INFO Deleting directory sample-backups/2014-01-25@20:03 ..
   INFO Deleting directory sample-backups/2014-01-26@20:02 ..
   INFO Deleting directory sample-backups/2014-01-27@20:08 ..
   INFO Deleting directory sample-backups/2014-01-28@20:07 ..
   INFO Deleting directory sample-backups/2014-01-29@20:07 ..
   INFO Deleting directory sample-backups/2014-01-30@20:08 ..
   INFO Deleting directory sample-backups/2014-01-31@20:04 ..
   INFO Preserving sample-backups/2014-02-01@20:05 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2014-02-02@20:03 ..
   INFO Deleting directory sample-backups/2014-02-03@20:05 ..
   INFO Deleting directory sample-backups/2014-02-04@20:06 ..
   INFO Deleting directory sample-backups/2014-02-05@20:07 ..
   INFO Deleting directory sample-backups/2014-02-06@20:06 ..
   INFO Deleting directory sample-backups/2014-02-07@20:05 ..
   INFO Deleting directory sample-backups/2014-02-08@20:06 ..
   INFO Deleting directory sample-backups/2014-02-09@20:04 ..
   INFO Deleting directory sample-backups/2014-02-10@20:07 ..
   INFO Deleting directory sample-backups/2014-02-11@20:07 ..
   INFO Deleting directory sample-backups/2014-02-12@20:07 ..
   INFO Deleting directory sample-backups/2014-02-13@20:06 ..
   INFO Deleting directory sample-backups/2014-02-14@20:06 ..
   INFO Deleting directory sample-backups/2014-02-15@20:05 ..
   INFO Deleting directory sample-backups/2014-02-16@20:04 ..
   INFO Deleting directory sample-backups/2014-02-17@20:06 ..
   INFO Deleting directory sample-backups/2014-02-18@20:04 ..
   INFO Deleting directory sample-backups/2014-02-19@20:08 ..
   INFO Deleting directory sample-backups/2014-02-20@20:06 ..
   INFO Deleting directory sample-backups/2014-02-21@20:07 ..
   INFO Deleting directory sample-backups/2014-02-22@20:05 ..
   INFO Deleting directory sample-backups/2014-02-23@20:06 ..
   INFO Deleting directory sample-backups/2014-02-24@20:05 ..
   INFO Deleting directory sample-backups/2014-02-25@20:06 ..
   INFO Deleting directory sample-backups/2014-02-26@20:04 ..
   INFO Deleting directory sample-backups/2014-02-27@20:05 ..
   INFO Deleting directory sample-backups/2014-02-28@20:03 ..
   INFO Preserving sample-backups/2014-03-01@20:04 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2014-03-02@20:01 ..
   INFO Deleting directory sample-backups/2014-03-03@20:05 ..
   INFO Deleting directory sample-backups/2014-03-04@20:06 ..
   INFO Deleting directory sample-backups/2014-03-05@20:05 ..
   INFO Deleting directory sample-backups/2014-03-06@20:24 ..
   INFO Deleting directory sample-backups/2014-03-07@20:03 ..
   INFO Deleting directory sample-backups/2014-03-08@20:04 ..
   INFO Deleting directory sample-backups/2014-03-09@20:01 ..
   INFO Deleting directory sample-backups/2014-03-10@20:05 ..
   INFO Deleting directory sample-backups/2014-03-11@20:05 ..
   INFO Deleting directory sample-backups/2014-03-12@20:05 ..
   INFO Deleting directory sample-backups/2014-03-13@20:05 ..
   INFO Deleting directory sample-backups/2014-03-14@20:04 ..
   INFO Deleting directory sample-backups/2014-03-15@20:04 ..
   INFO Deleting directory sample-backups/2014-03-16@20:02 ..
   INFO Deleting directory sample-backups/2014-03-17@20:04 ..
   INFO Deleting directory sample-backups/2014-03-18@20:06 ..
   INFO Deleting directory sample-backups/2014-03-19@20:06 ..
   INFO Deleting directory sample-backups/2014-03-20@20:06 ..
   INFO Deleting directory sample-backups/2014-03-21@20:04 ..
   INFO Deleting directory sample-backups/2014-03-22@20:03 ..
   INFO Deleting directory sample-backups/2014-03-23@20:01 ..
   INFO Deleting directory sample-backups/2014-03-24@20:03 ..
   INFO Deleting directory sample-backups/2014-03-25@20:05 ..
   INFO Deleting directory sample-backups/2014-03-26@20:03 ..
   INFO Deleting directory sample-backups/2014-03-27@20:04 ..
   INFO Deleting directory sample-backups/2014-03-28@20:03 ..
   INFO Deleting directory sample-backups/2014-03-29@20:03 ..
   INFO Deleting directory sample-backups/2014-03-30@20:01 ..
   INFO Deleting directory sample-backups/2014-03-31@20:04 ..
   INFO Preserving sample-backups/2014-04-01@20:03 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2014-04-02@20:05 ..
   INFO Deleting directory sample-backups/2014-04-03@20:03 ..
   INFO Deleting directory sample-backups/2014-04-04@20:04 ..
   INFO Deleting directory sample-backups/2014-04-05@20:02 ..
   INFO Deleting directory sample-backups/2014-04-06@20:02 ..
   INFO Deleting directory sample-backups/2014-04-07@20:02 ..
   INFO Deleting directory sample-backups/2014-04-08@20:04 ..
   INFO Deleting directory sample-backups/2014-04-09@20:04 ..
   INFO Deleting directory sample-backups/2014-04-10@20:04 ..
   INFO Deleting directory sample-backups/2014-04-11@20:04 ..
   INFO Deleting directory sample-backups/2014-04-12@20:03 ..
   INFO Deleting directory sample-backups/2014-04-13@20:01 ..
   INFO Deleting directory sample-backups/2014-04-14@20:05 ..
   INFO Deleting directory sample-backups/2014-04-15@20:05 ..
   INFO Deleting directory sample-backups/2014-04-16@20:06 ..
   INFO Deleting directory sample-backups/2014-04-17@20:05 ..
   INFO Deleting directory sample-backups/2014-04-18@20:06 ..
   INFO Deleting directory sample-backups/2014-04-19@20:02 ..
   INFO Deleting directory sample-backups/2014-04-20@20:01 ..
   INFO Deleting directory sample-backups/2014-04-21@20:01 ..
   INFO Deleting directory sample-backups/2014-04-22@20:06 ..
   INFO Deleting directory sample-backups/2014-04-23@20:06 ..
   INFO Deleting directory sample-backups/2014-04-24@20:05 ..
   INFO Deleting directory sample-backups/2014-04-25@20:04 ..
   INFO Deleting directory sample-backups/2014-04-26@20:02 ..
   INFO Deleting directory sample-backups/2014-04-27@20:02 ..
   INFO Deleting directory sample-backups/2014-04-28@20:05 ..
   INFO Deleting directory sample-backups/2014-04-29@20:05 ..
   INFO Deleting directory sample-backups/2014-04-30@20:05 ..
   INFO Preserving sample-backups/2014-05-01@20:06 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2014-05-02@20:05 ..
   INFO Deleting directory sample-backups/2014-05-03@20:03 ..
   INFO Deleting directory sample-backups/2014-05-04@20:01 ..
   INFO Deleting directory sample-backups/2014-05-05@20:06 ..
   INFO Deleting directory sample-backups/2014-05-06@20:06 ..
   INFO Deleting directory sample-backups/2014-05-07@20:05 ..
   INFO Deleting directory sample-backups/2014-05-08@20:03 ..
   INFO Deleting directory sample-backups/2014-05-09@20:01 ..
   INFO Deleting directory sample-backups/2014-05-10@20:01 ..
   INFO Deleting directory sample-backups/2014-05-11@20:01 ..
   INFO Deleting directory sample-backups/2014-05-12@20:05 ..
   INFO Deleting directory sample-backups/2014-05-13@20:06 ..
   INFO Deleting directory sample-backups/2014-05-14@20:04 ..
   INFO Deleting directory sample-backups/2014-05-15@20:06 ..
   INFO Deleting directory sample-backups/2014-05-16@20:05 ..
   INFO Deleting directory sample-backups/2014-05-17@20:02 ..
   INFO Deleting directory sample-backups/2014-05-18@20:01 ..
   INFO Deleting directory sample-backups/2014-05-19@20:02 ..
   INFO Deleting directory sample-backups/2014-05-20@20:04 ..
   INFO Deleting directory sample-backups/2014-05-21@20:03 ..
   INFO Deleting directory sample-backups/2014-05-22@20:02 ..
   INFO Deleting directory sample-backups/2014-05-23@20:02 ..
   INFO Deleting directory sample-backups/2014-05-24@20:01 ..
   INFO Deleting directory sample-backups/2014-05-25@20:01 ..
   INFO Deleting directory sample-backups/2014-05-26@20:05 ..
   INFO Deleting directory sample-backups/2014-05-27@20:03 ..
   INFO Deleting directory sample-backups/2014-05-28@20:03 ..
   INFO Deleting directory sample-backups/2014-05-29@20:01 ..
   INFO Deleting directory sample-backups/2014-05-30@20:02 ..
   INFO Deleting directory sample-backups/2014-05-31@20:02 ..
   INFO Preserving sample-backups/2014-06-01@20:01 (matches retention period(s) 'monthly') ..
   INFO Deleting directory sample-backups/2014-06-02@20:05 ..
   INFO Deleting directory sample-backups/2014-06-03@20:02 ..
   INFO Deleting directory sample-backups/2014-06-04@20:03 ..
   INFO Deleting directory sample-backups/2014-06-05@20:03 ..
   INFO Deleting directory sample-backups/2014-06-06@20:02 ..
   INFO Deleting directory sample-backups/2014-06-07@20:01 ..
   INFO Deleting directory sample-backups/2014-06-08@20:01 ..
   INFO Preserving sample-backups/2014-06-09@20:01 (matches retention period(s) 'weekly') ..
   INFO Deleting directory sample-backups/2014-06-10@20:02 ..
   INFO Deleting directory sample-backups/2014-06-11@20:02 ..
   INFO Deleting directory sample-backups/2014-06-12@20:03 ..
   INFO Deleting directory sample-backups/2014-06-13@20:05 ..
   INFO Deleting directory sample-backups/2014-06-14@20:01 ..
   INFO Deleting directory sample-backups/2014-06-15@20:01 ..
   INFO Preserving sample-backups/2014-06-16@20:02 (matches retention period(s) 'weekly') ..
   INFO Deleting directory sample-backups/2014-06-17@20:01 ..
   INFO Deleting directory sample-backups/2014-06-18@20:01 ..
   INFO Deleting directory sample-backups/2014-06-19@20:04 ..
   INFO Deleting directory sample-backups/2014-06-20@20:02 ..
   INFO Deleting directory sample-backups/2014-06-21@20:02 ..
   INFO Deleting directory sample-backups/2014-06-22@20:01 ..
   INFO Preserving sample-backups/2014-06-23@20:04 (matches retention period(s) 'weekly') ..
   INFO Deleting directory sample-backups/2014-06-24@20:06 ..
   INFO Deleting directory sample-backups/2014-06-25@20:03 ..
   INFO Preserving sample-backups/2014-06-26@20:04 (matches retention period(s) 'daily') ..
   INFO Preserving sample-backups/2014-06-27@20:02 (matches retention period(s) 'daily') ..
   INFO Preserving sample-backups/2014-06-28@20:02 (matches retention period(s) 'daily') ..
   INFO Preserving sample-backups/2014-06-29@20:01 (matches retention period(s) 'daily') ..
   INFO Preserving sample-backups/2014-06-30@20:03 (matches retention period(s) 'daily' and 'weekly') ..
   INFO Preserving sample-backups/2014-07-01@20:02 (matches retention period(s) 'daily' and 'monthly') ..
   INFO Preserving sample-backups/2014-07-02@20:03 (matches retention period(s) 'hourly' and 'daily') ..

.. External references:

.. _Easy Automated Snapshot-Style Backups with Linux and Rsync: http://www.mikerubel.org/computers/rsync_snapshots/
.. _GitHub: https://github.com/xolox/python-rotate-backups
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _peter@peterodding.com: peter@peterodding.com
.. _PyPI: https://pypi.python.org/pypi/rotate-backups
.. _Python Package Index: https://pypi.python.org/pypi/rotate-backups
.. _rsync: http://en.wikipedia.org/wiki/rsync
