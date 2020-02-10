#!/bin/bash -e

main () {

  # On Mac OS X workers we are responsible for creating the Python virtual
  # environment, because we set `language: generic' in the Travis CI build
  # configuration file (to bypass the lack of Python runtime support).
  if [ "$TRAVIS_OS_NAME" = osx ]; then
    local environment="$HOME/virtualenv/python2.7"
    if [ -x "$environment/bin/python" ]; then
      msg "Activating virtual environment ($environment) .."
      source "$environment/bin/activate"
    else
      if ! which virtualenv &>/dev/null; then
        msg "Installing 'virtualenv' in per-user site-packages .."
        pip install --user virtualenv
        msg "Figuring out 'bin' directory of per-user site-packages .."
        LOCAL_BINARIES=$(python -c 'import os, site; print(os.path.join(site.USER_BASE, "bin"))')
        msg "Prefixing '$LOCAL_BINARIES' to PATH .."
        export PATH="$LOCAL_BINARIES:$PATH"
      fi
      msg "Creating virtual environment ($environment) .."
      virtualenv "$environment"
      msg "Activating virtual environment ($environment) .."
      source "$environment/bin/activate"
      msg "Checking if 'pip' executable works .."
      if ! pip --version; then
        msg "Bootstrapping working 'pip' installation using get-pip.py .."
        curl -s https://bootstrap.pypa.io/get-pip.py | python -
      fi
    fi
  fi

  # Install the required Python packages.
  pip install --requirement=requirements-travis.txt

  # Install the project itself, making sure that potential character encoding
  # and/or decoding errors in the setup script are caught as soon as possible.
  LC_ALL=C pip install .

}

msg () {
  echo "[install-on-travis.sh] $*" >&2
}

main "$@"
