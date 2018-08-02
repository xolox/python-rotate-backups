#!/bin/bash -e

# On Mac OS X workers we are responsible for creating the Python virtual
# environment, because we set `language: generic' in the Travis CI build
# configuration file (to bypass the lack of Python runtime support).
if [ "$TRAVIS_OS_NAME" = osx ]; then
  VIRTUAL_ENV="$HOME/virtualenv/python2.7"
  if [ ! -x "$VIRTUAL_ENV/bin/python" ]; then
    if ! which virtualenv &>/dev/null; then
      # Install `virtualenv' in ~/.local (doesn't require `sudo' privileges).
      pip install --user virtualenv
      # Make sure ~/.local/bin is in the $PATH.
      LOCAL_BINARIES=$(python -c 'import os, site; print(os.path.join(site.USER_BASE, "bin"))')
      export PATH="$PATH:$LOCAL_BINARIES"
    fi
    virtualenv "$VIRTUAL_ENV"
  fi
  source "$VIRTUAL_ENV/bin/activate"
fi

# Install the required Python packages.
pip install --requirement=requirements-travis.txt

# Install the project itself, making sure that potential character encoding
# and/or decoding errors in the setup script are caught as soon as possible.
LC_ALL=C pip install .
