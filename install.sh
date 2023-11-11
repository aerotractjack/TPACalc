#!/bin/bash

pushd /home/aerotract/software/TPACalc
rm -rf *.egg-info/ dist/ build/
/usr/bin/python3 setup.py sdist bdist_wheel
/usr/bin/python3 -m pip install --upgrade --force-reinstall dist/tpacalc-0.1-py3-none-any.whl
popd