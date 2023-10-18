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


def cmd_info(cmdargs: argparse.Namespace) -> int:
    import jiramail.info
    return jiramail.info.main(cmdargs)


def cmd_smtp(cmdargs: argparse.Namespace) -> int:
    import jiramail.smtp
    return jiramail.smtp.main(cmdargs)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose",
                        dest="verbose", action='count', default=0,
                        help="print a message for each action.")
    parser.add_argument('-q', '--quiet',
                        dest="quiet", action='store_true', default=False,
                        help='output critical information only.')
    parser.add_argument("-V", "--version",
                        action='version',
                        help="show program's version number and exit.",
                        version=jiramail.__VERSION__)
    parser.add_argument("-h", "--help",
                        action='help',
                        help="show this help message and exit.")


def setup_parser() -> argparse.ArgumentParser:
    epilog = "Report bugs to authors."

    description = """\
The utility provides transport between JIRA and mailbox. It saves JIRA issues in
mailbox format. Issues are saved along with all comments. Changes made to the
issue are also saved in the form of emails. All issue changes are grouped into
one thread.

Changes are made to JIRA by executing commands that are read from emails from
the mailbox or from stdin.
"""
    parser = argparse.ArgumentParser(
            prog="jiramail",
            formatter_class=argparse.RawTextHelpFormatter,
            description=description,
            epilog=epilog,
            add_help=False,
            allow_abbrev=True)

    add_common_arguments(parser)

    subparsers = parser.add_subparsers(dest="subcmd", help="")

    # jiramail mbox
    sp0_description = """\
retrieves one or more jira issues as an mailbox file. The entire history of
changes will also be saved.

"""
    sp0 = subparsers.add_parser("mbox",
                                description=sp0_description,
                                help=sp0_description,
                                epilog=epilog,
                                add_help=False)
    sp0.set_defaults(func=cmd_mbox)

    sp0.add_argument("--assignee",
                     dest="assignee", action="append", default=[], metavar="USER",
                     help="search for all issues that belong to the USER.")
    sp0.add_argument("--query",
                     dest="queries", action="append", default=[], metavar="JQL",
                     help="jira query string.")
    sp0.add_argument("--issue",
                     dest="issues", action="append", default=[], metavar="ISSUE-123",
                     help="specify the issues to export.")
    sp0.add_argument("mailbox",
                     help="path to mailbox where emails should be added.")
    add_common_arguments(sp0)

    # jiramail change
    sp1_description = """\
reads mailbox and makes changes in JIRA. If commands are read from mailbox, then
by default the utility will add a letter with a report on the executed commands.

"""
    sp1 = subparsers.add_parser("change",
                                description=sp1_description,
                                help=sp1_description,
                                epilog=epilog,
                                add_help=False)
    sp1.set_defaults(func=cmd_change)

    sp1.add_argument("-n", "--dry-run",
                     dest="dry_run", action="store_true",
                     help="do not act, just print what would happen.")
    sp1.add_argument("-r", "--no-reply",
                     dest="no_reply", action="store_true",
                     help="do not add a reply message with the status of command execution.")
    sp1.add_argument("-s", "--stdin",
                     dest="stdin", action="store_true",
                     help="accept a mail stream on standard input, process commands from it and write it to mailbox.")
    sp1.add_argument("mailbox",
                     help="path to mailbox with commands.")
    add_common_arguments(sp1)

    # jiramail subs
    sp2_description = """\
receives updates based on saved queries. Saved queries aka substriptions are
read from the configuration file.

"""
    sp2 = subparsers.add_parser("subs",
                                description=sp2_description,
                                help=sp2_description,
                                epilog=epilog,
                                add_help=False)
    sp2.set_defaults(func=cmd_subs)
    add_common_arguments(sp2)

    # jiramail info
    sp3_description = """\
retrieves issue information from the jira API.

"""
    sp3 = subparsers.add_parser("info",
                                description=sp3_description,
                                help=sp3_description,
                                epilog=epilog,
                                add_help=False)
    sp3.set_defaults(func=cmd_info)

    sp3.add_argument("--issue",
                     dest="issue", action="store", default=None, metavar="ISSUE-123",
                     help="specify the issue to export.")
    add_common_arguments(sp3)

    # jiramail smtp
    sp4_description = """\
fake smtp server for receiving commands in sent emails. This is an alternative,
easier way to send commands.
"""
    sp4 = subparsers.add_parser("smtp",
                                description=sp4_description,
                                help=sp4_description,
                                epilog=epilog,
                                add_help=False)
    sp4.set_defaults(func=cmd_smtp)

    sp4.add_argument("-n", "--dry-run",
                     dest="dry_run", action="store_true",
                     help="do not act, just print what would happen.")
    sp4.add_argument("-1", "--one-message",
                     dest="one_message", action="store_true",
                     help="exit after processing one incoming email.")
    sp4.add_argument("-m", "--mailbox",
                     dest="mailbox", action="store", default="",
                     help="path to mailbox to store a reply messages with the status of command execution.")
    add_common_arguments(sp4)

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

    jiramail.setup_logger(logger, level=level, fmt="[%(asctime)s] %(message)s")


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
