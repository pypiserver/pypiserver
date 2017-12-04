#! /usr/bin/env py.test

import logging

import pip
import pytest

import os.path as osp
import subprocess as sbp


mydir = osp.dirname(__file__)

script_fpath = osp.join(mydir, '..', 'bin', 'test-plugins.sh')

def test_plugins_smoketest():
    out = sbp.check_output(script_fpath, shell=True)
    print(out)
