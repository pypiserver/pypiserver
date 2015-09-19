## A test-distribution to check if 
#    bottle supports uploading 100's of packages,
#    see: https://github.com/pypiserver/pypiserver/issues/82
#
# Has been run once `pip wheel .`, just to generate:
#    ./wheelhouse/centodeps-0.0.0-cp34-none-win_amd64.whl
# 
from setuptools import setup
setup(
    name='centodeps',
    install_requires=['a==1.0'] * 200,
    options={
        'bdist_wheel': {'universal': True},
    },
)
