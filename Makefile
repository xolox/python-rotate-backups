# Makefile for rotate-backups
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: March 21, 2016
# URL: https://github.com/xolox/python-rotate-backups

WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/rotate-backups
ACTIVATE = . $(VIRTUAL_ENV)/bin/activate

default:
	@echo 'Makefile for rotate-backups'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install    install the package in a virtual environment'
	@echo '    make reset      recreate the virtual environment'
	@echo '    make test       run the test suite, report coverage'
	@echo '    make tox        run the tests on all Python versions'
	@echo '    make check      check the coding style'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup all temporary files'
	@echo

install:
	test -d "$(VIRTUAL_ENV)" || virtualenv "$(VIRTUAL_ENV)"
	test -x "$(VIRTUAL_ENV)/bin/pip" || ($(ACTIVATE) && easy_install pip)
	test -x "$(VIRTUAL_ENV)/bin/pip-accel" || ($(ACTIVATE) && pip install --quiet pip-accel)
	$(ACTIVATE) && pip uninstall --yes rotate-backups >/dev/null 2>&1 || true
	$(ACTIVATE) && pip-accel install --quiet --editable .

reset:
	rm -Rf "$(VIRTUAL_ENV)"
	make --no-print-directory clean install

test: install
	$(ACTIVATE) && pip-accel install --quiet coverage pytest pytest-cov
	$(ACTIVATE) && py.test -v --cov --cov-fail-under=90
	$(ACTIVATE) && coverage html

tox: install
	$(ACTIVATE) && pip-accel install --quiet tox
	$(ACTIVATE) && tox

check: install
	$(ACTIVATE) && pip-accel install --quiet flake8 flake8-pep257
	$(ACTIVATE) && flake8

readme: install
	test -x "$(VIRTUAL_ENV)/bin/cog.py" || ($(ACTIVATE) && pip-accel install --quiet cogapp)
	$(ACTIVATE) && cog.py -r README.rst

docs: install
	test -x "$(VIRTUAL_ENV)/bin/sphinx-build" || ($(ACTIVATE) && pip-accel install --quiet sphinx)
	$(ACTIVATE) && cd docs && sphinx-build -b html -d build/doctrees . build/html

publish:
	git push origin && git push --tags origin
	make clean && python setup.py sdist upload

clean:
	rm -Rf *.egg *.egg-info .coverage build dist docs/build htmlcov
	find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	find -type f -name '*.pyc' -delete

.PHONY: default install reset test tox check readme docs publish clean
