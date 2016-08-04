# Makefile for rotate-backups.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 13, 2016
# URL: https://github.com/xolox/python-rotate-backups

WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/rotate-backups
PATH := $(VIRTUAL_ENV)/bin:$(PATH)
MAKE := $(MAKE) --no-print-directory
SHELL = bash

default:
	@echo 'Makefile for rotate-backups'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install    install the package in a virtual environment'
	@echo '    make reset      recreate the virtual environment'
	@echo '    make check      check coding style (PEP-8, PEP-257)'
	@echo '    make test       run the test suite, report coverage'
	@echo '    make tox        run the tests on all Python versions'
	@echo '    make readme     update usage in readme'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup all temporary files'
	@echo

install:
	@test -d "$(VIRTUAL_ENV)" || mkdir -p "$(VIRTUAL_ENV)"
	@test -x "$(VIRTUAL_ENV)/bin/python" || virtualenv --quiet "$(VIRTUAL_ENV)"
	@test -x "$(VIRTUAL_ENV)/bin/pip" || easy_install pip
	@test -x "$(VIRTUAL_ENV)/bin/pip-accel" || (pip install --quiet pip-accel && pip-accel install --quiet 'urllib3[secure]')
	@echo "Updating requirements .." >&2
	@pip-accel install --quiet --requirement=requirements.txt
	@if ! which rotate-backups &>/dev/null; then  \
		echo "Installing rotate-backups .." >&2;      \
		pip install --quiet --no-deps --editable .; \
	fi

reset:
	$(MAKE) clean
	rm -Rf "$(VIRTUAL_ENV)"
	$(MAKE) install

check: install
	@echo "Updating flake8 .." >&2
	@pip-accel install --upgrade --quiet --requirement=requirements-checks.txt
	@flake8

test: install
	@pip-accel install --quiet coverage pytest pytest-cov
	@py.test -v --cov --cov-report=html --no-cov-on-fail
	@coverage report --fail-under=90

tox: install
	@pip-accel install --quiet tox && tox

readme: install
	@pip-accel install --quiet cogapp && cog.py -r README.rst

docs: readme
	@pip-accel install --quiet sphinx
	@cd docs && sphinx-build -nb html -d build/doctrees . build/html

publish: install
	git push origin && git push --tags origin
	$(MAKE) clean
	pip-accel install --quiet twine wheel
	python setup.py sdist bdist_wheel
	twine upload dist/*
	$(MAKE) clean

clean:
	@rm -Rf *.egg .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default install reset check test tox readme docs publish clean
