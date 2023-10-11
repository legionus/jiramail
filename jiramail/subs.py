#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import multiprocessing
import re

from typing import Dict, List, Any

import jiramail
import jiramail.mbox

logger = jiramail.logger
config_section = "sub"


def sync_mailbox(config: Dict[str, Any], mailbox: str, queries: Dict[str, List[str]]) -> int:
    logger = jiramail.setup_logger(multiprocessing.get_logger(),
                                   level=jiramail.logger.level,
                                   fmt="[%(asctime)s] pid=%(process)d: %(message)s")
    jiramail.logger = logger
    jiramail.mbox.logger = logger

    logger.critical("process started for `%s'", mailbox)

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        logger.critical("unable to connect to jira: %s", e)
        return jiramail.EX_FAILURE

    try:
        mbox = jiramail.Mailbox(mailbox)
    except Exception as e:
        logger.critical("unable to open mailbox: %s", e)
        return jiramail.EX_FAILURE

    for target in queries.keys():
        logger.info("syncing subscription `%s' to `%s' ...", target, mailbox)

        for query in queries[target]:
            jiramail.mbox.process_query(query, mbox)

        logger.critical("section `%s' synced", target)

    mbox.close()

    return jiramail.EX_SUCCESS


# pylint: disable-next=unused-argument
def main(cmdargs: argparse.Namespace) -> int:
    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        logger.critical("%s", config.message)
        return jiramail.EX_FAILURE

    if config_section not in config:
        return jiramail.EX_SUCCESS

    mailboxes: Dict[str, Dict[str, List[str]]] = {}

    for target in config[config_section]:
        section = config[config_section][target]

        if "skip" in section and re.match(r'^(1|on|yes|true)$', section["skip"], re.IGNORECASE):
            logger.info("syncing section `%s' skipped", target)
            continue

        if "mbox" not in section:
            logger.critical("section `%s.%s' does not contain the 'mbox' parameter which specifies the output mbox file.",
                            config_section, target)
            return jiramail.EX_FAILURE

        mailbox = section["mbox"]

        if mailbox not in mailboxes:
            mailboxes[mailbox] = {}

        if target not in mailboxes[mailbox]:
            mailboxes[mailbox][target] = []

        if "assignee" in section:
            username = section["assignee"]
            mailboxes[mailbox][target].append(f"assignee = '{username}'")

        if "query" in section:
            mailboxes[mailbox][target].append(section["query"])

    nprocs = min(5, len(mailboxes.keys()))

    if nprocs == 0:
        return jiramail.EX_SUCCESS

    ret = jiramail.EX_SUCCESS

    with multiprocessing.Pool(processes=nprocs) as pool:
        results = []

        for mailbox, queries in mailboxes.items():
            results.append(pool.apply_async(sync_mailbox, (config, mailbox, queries,)))

        for result in results:
            rc = result.get()

            if rc != jiramail.EX_SUCCESS:
                ret = rc

    return ret
