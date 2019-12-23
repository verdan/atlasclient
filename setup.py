#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
import os
import sys

here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, here)
from atlasclient import __version__ as version


with open(os.path.join(here, 'README.rst')) as readme_file:
    readme = readme_file.read()

with open(os.path.join(here, 'HISTORY.rst')) as history_file:
    history = history_file.read()

requirements_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'requirements.txt')
test_requirements_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_requirements.txt')
setup_requirements_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'setup_requirements.txt')

with open(requirements_path) as requirements_file:
    requirements = requirements_file.readlines()

with open(test_requirements_path) as test_requirements_file:
    test_requirements = test_requirements_file.readlines()

with open(setup_requirements_path) as setup_requirements_file:
    setup_requirements = setup_requirements_file.readlines()

setup_args = dict(
    name='pyatlasclient',
    version=version,
    description="Apache Atlas Python Client",
    long_description=readme + '\n\n' + history,
    author="Verdan Mahmood",
    author_email='verdan.mahmood@gmail.com',
    url='https://github.com/verdan/pyatlasclient',
    packages=find_packages(include=['atlasclient']),
    include_package_data=True,
    install_requires=requirements,
    license='Apache Software License 2.0',
    zip_safe=False,
    keywords='atlasclient, pyatlasclient, apache atlas, atlas',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)

setup(**setup_args)
