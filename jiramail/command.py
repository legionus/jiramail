#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import sys
import logging

import jiramail

logger = jiramail.logger


def cmd_mbox(cmdargs: argparse.Namespace) -> int:
    import jiramail.mbox
    return jiramail.mbox.main(cmdargs)


def cmd_change(cmdargs: argparse.Namespace) -> int:
    import jiramail.change
    return jiramail.change.main(cmdargs)


def cmd_subs(cmdargs: argparse.Namespace) -> int:
    import jiramail.subs
    return jiramail.subs.main(cmdargs)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose",
                        dest="verbose", action='count', default=0,
                        help="print a message for each action")
    parser.add_argument('-q', '--quiet',
                        dest="quiet", action='store_true', default=False,
                        help='Output critical information only')
    parser.add_argument("-V", "--version",
                        action='version',
                        version=jiramail.__VERSION__)


def setup_parser() -> argparse.ArgumentParser:
    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(
            prog="jiramail",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
Saves JIRA issues in mailbox format. Issues are saved along with all comments.
Changes made to the issue are also saved in the form of emails.
""",
            epilog="Report bugs to authors.",
            allow_abbrev=True)

    add_common_arguments(parser)

    subparsers = parser.add_subparsers(dest="subcmd", help="sub-command help")

    # jiramail mbox
    sp0 = subparsers.add_parser("mbox",
                                help="download one or more jira issue as an mbox file",
                                epilog="Report bugs to authors.")
    sp0.set_defaults(func=cmd_mbox)
    add_common_arguments(sp0)

    sp0.add_argument("--assignee",
                     dest="assignee", action="append", default=[], metavar="USER",
                     help="search for all issues that belong to the USER")
    sp0.add_argument("--query",
                     dest="queries", action="append", default=[], metavar="JQL",
                     help="jira query string.")
    sp0.add_argument("--issue",
                     dest="issues", action="append", default=[], metavar="ISSUE-123",
                     help="specify the issues to export")
    sp0.add_argument("mailbox",
                     help="path to mbox where emails should be added")

    # jiramail change
    sp1 = subparsers.add_parser("change",
                                help="reads mailbox and makes changes in JIRA.",
                                epilog="Report bugs to authors.")
    sp1.set_defaults(func=cmd_change)
    add_common_arguments(sp1)

    sp1.add_argument("-n", "--dry-run",
                     dest="dry_run", action="store_true",
                     help="do not act, just print what would happen")
    sp1.add_argument("-r", "--no-reply",
                     dest="no_reply", action="store_true",
                     help="do not add a reply message with the status of command execution")
    sp1.add_argument("-s", "--stdin",
                     dest="stdin", action="store_true",
                     help="accept a mail stream on standard input, process commands from it and write it to mailbox")
    sp1.add_argument("mailbox",
                     help="path to mbox with commands")

    # jiramail subs
    sp2 = subparsers.add_parser("subs",
                                help="synchronizes subscriptions with saved queries with their mboxes.",
                                epilog="Report bugs to authors.")
    sp2.set_defaults(func=cmd_subs)
    add_common_arguments(sp2)

    return parser


def setup_logger(cmdargs: argparse.Namespace) -> None:
    match cmdargs.verbose:
        case 0:
            level = logging.WARNING
        case 1:
            level = logging.INFO
        case _:
            level = logging.DEBUG

    if cmdargs.quiet:
        level = logging.CRITICAL

    fmt = logging.Formatter(fmt="%(asctime)s %(message)s",  datefmt="[%H:%M:%S]")

    handlr = logging.StreamHandler()
    handlr.setLevel(level)
    handlr.setFormatter(fmt)

    logger.setLevel(level)
    logger.addHandler(handlr)


def cmd() -> int:
    parser = setup_parser()
    cmdargs = parser.parse_args()

    setup_logger(cmdargs)

    if 'func' not in cmdargs:
        parser.print_help()
        return jiramail.EX_FAILURE

    ret: int = cmdargs.func(cmdargs)

    return ret


if __name__ == '__main__':
    # We're running from a checkout, so reflect git commit in the version
    import os
    # noinspection PyBroadException
    try:
        if jiramail.__VERSION__.find('-dev') > 0:
            base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            dotgit = os.path.join(base, '.git')
            ecode, short = jiramail.git_run_command(dotgit, ['rev-parse', '--short', 'HEAD'])
            if ecode == 0:
                ver = jiramail.__VERSION__
                sha = short.strip()
                jiramail.__VERSION__ = f"{ver}-{sha:.5s}"
    except Exception as ex:
        # Any failures above are non-fatal
        pass
    sys.exit(cmd())
