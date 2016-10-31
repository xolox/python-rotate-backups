#!/bin/bash -e

# On Mac OS X workers we are responsible for activating the Python virtual
# environment, because we set `language: generic' in the Travis CI build
# configuration file (to bypass the lack of Python runtime support).

if [ "$TRAVIS_OS_NAME" = osx ]; then
  VIRTUAL_ENV="$HOME/virtualenv/python2.7"
  source "$VIRTUAL_ENV/bin/activate"
fi

eval "$@"
