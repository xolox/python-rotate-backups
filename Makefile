# Makefile for rotate-backups
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 19, 2015
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
	@echo '    make test       run the test suite'
	@echo '    make coverage   run the tests, report coverage'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup all temporary files'
	@echo

install:
	test -d "$(VIRTUAL_ENV)" || virtualenv "$(VIRTUAL_ENV)"
	test -x "$(VIRTUAL_ENV)/bin/pip" || ($(ACTIVATE) && easy_install pip)
	test -x "$(VIRTUAL_ENV)/bin/pip-accel" || ($(ACTIVATE) && pip install pip-accel)
	$(ACTIVATE) && pip uninstall -y rotate-backups >/dev/null 2>&1 || true
	$(ACTIVATE) && pip install --quiet --editable .

reset:
	rm -Rf "$(VIRTUAL_ENV)"
	make --no-print-directory clean install

test: install
	test -x "$(VIRTUAL_ENV)/bin/py.test" || ($(ACTIVATE) && pip-accel install pytest)
	$(ACTIVATE) && py.test -v
	$(ACTIVATE) && make coverage
	test -x "$(VIRTUAL_ENV)/bin/tox" || ($(ACTIVATE) && pip-accel install tox)
	$(ACTIVATE) && tox

coverage: install
	$(ACTIVATE) && pip-accel install coverage
	$(ACTIVATE) && coverage run setup.py test
	$(ACTIVATE) && coverage report
	$(ACTIVATE) && coverage html

readme:
	test -x "$(VIRTUAL_ENV)/bin/cog.py" || ($(ACTIVATE) && pip-accel install cogapp)
	$(ACTIVATE) && cog.py -r README.rst

docs: install
	test -x "$(VIRTUAL_ENV)/bin/sphinx-build" || ($(ACTIVATE) && pip-accel install sphinx)
	$(ACTIVATE) && cd docs && sphinx-build -b html -d build/doctrees . build/html

publish:
	git push origin && git push --tags origin
	make clean && python setup.py sdist upload

clean:
	rm -Rf *.egg *.egg-info .coverage build dist docs/build htmlcov
	find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	find -type f -name '*.pyc' -delete

.PHONY: default install reset test coverage docs publish clean
