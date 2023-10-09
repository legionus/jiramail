#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import re

import jiramail
import jiramail.mbox

config_section = "sub"

def main(cmdargs: argparse.Namespace) -> int:
    jiramail.verbosity = cmdargs.verbose

    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        jiramail.verbose(0, f"{config.message}")
        return jiramail.EX_FAILURE

    if config_section not in config:
        return jiramail.EX_SUCCESS

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        jiramail.verbose(0, f"unable to connect to jira: {e}")
        return jiramail.EX_FAILURE

    ret = jiramail.EX_SUCCESS

    for target in config[config_section]:
        section = config[config_section][target]

        if "skip" in section and re.match(r'^(1|on|yes|true)$', section["skip"], re.IGNORECASE):
            jiramail.verbose(1, f"syncing section '{target}' skipped")
            continue

        if "mbox" not in section:
            jiramail.verbose(0, f"section '{config_section}.{target}' does not contain the 'mbox' parameter which specifies the output mbox file.")
            ret = jiramail.EX_FAILURE
            continue

        mailbox = section["mbox"]

        jiramail.verbose(1, f"syncing section '{target}' to '{mailbox}' ...")

        try:
            mbox = jiramail.Mailbox(mailbox)
        except Exception as e:
            jiramail.verbose(0, f"unable to open mailbox: {e}")
            ret = jiramail.EX_FAILURE
            continue

        if "assignee" in section:
            username = section["assignee"]
            jiramail.mbox.process_query(f"assignee = '{username}'", mbox)

        if "query" in section:
            jiramail.mbox.process_query(section["query"], mbox)

        mbox.close()

        jiramail.verbose(0, f"section '{target}' synced")

    return ret
