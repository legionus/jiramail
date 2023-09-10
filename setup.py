#!/usr/bin/env python3

import os
import re
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def find_version(source):
    version_file = read(source)
    version_match = re.search(r"^__VERSION__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


NAME = "jiramail"

setup(
        version=find_version("jiramail/__init__.py"),
        url="https://github.com/legionus/jiramail.git",
        name=NAME,
        description="Transport from jira to mbox",
        author="Alexey Gladkov",
        author_email="gladkov.alexey@gmail.com",
        packages=["jiramail"],
        license="GPLv3+",
        keywords=["jira", "mailbox"],
        install_requires=[
            "jira>=3.5.2",
            ],
        python_requires=">=3.10",
        entry_points={
            "console_scripts": [
                "jiramail=jiramail.command:cmd"
                ],
            },
        )
