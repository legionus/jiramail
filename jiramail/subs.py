#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import re

import jiramail
import jiramail.mbox

logger = jiramail.logger
config_section = "sub"


# pylint: disable-next=unused-argument
def main(cmdargs: argparse.Namespace) -> int:
    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        logger.critical("%s", config.message)
        return jiramail.EX_FAILURE

    if config_section not in config:
        return jiramail.EX_SUCCESS

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        logger.critical("unable to connect to jira: %s", e)
        return jiramail.EX_FAILURE

    ret = jiramail.EX_SUCCESS

    for target in config[config_section]:
        section = config[config_section][target]

        if "skip" in section and re.match(r'^(1|on|yes|true)$', section["skip"], re.IGNORECASE):
            logger.info("syncing section `%s' skipped", target)
            continue

        if "mbox" not in section:
            logger.critical("section `%s.%s' does not contain the 'mbox' parameter which specifies the output mbox file.",
                            config_section, target)
            ret = jiramail.EX_FAILURE
            continue

        mailbox = section["mbox"]

        logger.info("syncing section `%s' to `%s' ...", target, mailbox)

        try:
            mbox = jiramail.Mailbox(mailbox)
        except Exception as e:
            logger.critical("unable to open mailbox: %s", e)
            ret = jiramail.EX_FAILURE
            continue

        if "assignee" in section:
            username = section["assignee"]
            jiramail.mbox.process_query(f"assignee = '{username}'", mbox)

        if "query" in section:
            jiramail.mbox.process_query(section["query"], mbox)

        mbox.close()

        logger.critical("section `%s' synced", target)

    return ret
