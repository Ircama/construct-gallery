#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
# construct-gallery module
#############################################################################

from setuptools import setup, find_packages
import re
import os
import sys

import json
from urllib import request
from pkg_resources import parse_version

###########################################################################

END_OF_INTRODUCTION = '## Setup'

EPILOGUE = '''
Full information, installation notes, API reference and usage details at the [construct-gallery GitHub repository](https://github.com/Ircama/construct-gallery).
'''

DESCRIPTION = ("construct-gallery GUI (based on wxPython) and development modules")

PACKAGE_NAME = "construct-gallery"

VERSIONFILE = "construct_gallery/__version__.py"

###########################################################################

def versions(pkg_name, site):
    url = 'https://' + site + '.python.org/pypi/' + pkg_name + '/json'
    print("Package " + pkg_name + ". Site URL: " + url)
    try:
        releases = json.loads(request.urlopen(url).read())['releases']
    except Exception as e:
        print("Error while getting data from URL '" + url + "': " + repr(e))
        return []
    return sorted(releases, key=parse_version, reverse=True)

with open("README.md", "r") as readme:
    long_description = readme.read()

build = ''
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

if os.environ.get('GITHUB_RUN_NUMBER') is not None:
    version_list_pypi = [
        a for a in versions(PACKAGE_NAME, 'pypi') if a.startswith(verstr)]
    version_list_testpypi = [
        a for a in versions(PACKAGE_NAME, 'testpypi') if a.startswith(verstr)]
    if (version_list_pypi or
            version_list_testpypi or
            os.environ.get('GITHUB_FORCE_RUN_NUMBER') is not None):
        print('---------------------------------'
            '---------------------------------')
        print("Using build number " + os.environ['GITHUB_RUN_NUMBER'])
        if version_list_pypi:
            print(
                "Version list available in pypi: " +
                ', '.join(version_list_pypi))
        if version_list_testpypi:
            print(
                "Version list available in testpypi: " +
                ', '.join(version_list_testpypi))
        print('---------------------------------'
            '---------------------------------')
        verstr += '-' + os.environ['GITHUB_RUN_NUMBER']

setup(
    name=PACKAGE_NAME,
    version=verstr,
    description=(DESCRIPTION),
    long_description=long_description[
        :long_description.find(END_OF_INTRODUCTION)] + EPILOGUE,
    long_description_content_type="text/markdown",
    classifiers=[
        "License :: Other/Proprietary License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        'Programming Language :: Python :: 3 :: Only',
        "Programming Language :: Python :: Implementation :: CPython",
        "Development Status :: 5 - Production/Stable",
        "Typing :: Typed",
        "Intended Audience :: Developers",
    ],
    author="Ircama",
    url="https://github.com/Ircama/construct-gallery",
    license='CC-BY-NC-SA-4.0',
    packages=["construct_gallery"],
    package_data={
        "construct_gallery": ["py.typed"],
    },
    entry_points={
        "gui_scripts": [
            "construct-gallery=construct_gallery.main:main"
        ]
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'construct-editor'
    ],
    keywords=[
        "construct-gallery",
        "construct-editor",
        "module",
        "gui",
        "wx",
        "wxpython",
        "widget",
        "binary",
        "editor" "construct",
        "bleak",
        "BLE",
        "bluetooth",
        "plugin",
    ],
    python_requires=">=3.8",
)
