#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import re

from typing import Optional, Any

import jira
import jira.resources

import jiramail

logger = jiramail.logger


def get_issue_field(issue: jira.resources.Issue, name: str) -> Optional[Any]:
    try:
        return issue.get_field(field_name=name)
    except AttributeError:
        pass
    field = jiramail.jserv.field_by_name(name.lower(), {})
    if field:
        try:
            return issue.get_field(field["id"])
        except AttributeError:
            pass
    return None


def main(cmdargs: argparse.Namespace) -> int:
    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        logger.critical("%s", config.message)
        return jiramail.EX_FAILURE

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        logger.critical("unable to connect to jira: %s", e)
        return jiramail.EX_FAILURE

    if cmdargs.issue:
        issue = jiramail.jserv.jira.issue(cmdargs.issue)

        for field_id, field in jiramail.jserv.jira.editmeta(issue.key)["fields"].items():
            match field_id:
                case "description" | "comment":
                    continue

            name = field.get("name", field_id)
            value = get_issue_field(issue, field_id)
            v_type = field.get("schema", {}).get("type", None)
            i_type = field.get("schema", {}).get("items", None)

            if i_type:
                v_type += " / " + i_type

            print("#", "=" * 79, sep="")
            print("# Field :", str(name))
            print("#  Type :", str(v_type))
            print("#    ID :", str(field_id))
            print("#", "-" * 79, sep="")
            if isinstance(value, list):
                for n, item in enumerate(value):
                    print(f":[{n}]")
                    print(re.sub(r'^(.*)$', r'| \1', f"{item}", flags=re.M))
            elif value is None:
                pass
            else:
                print(re.sub(r'^(.*)$', r'| \1', f"{value}", flags=re.M))
            print("*")

    return jiramail.EX_SUCCESS
