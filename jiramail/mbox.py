#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import email
import mailbox
import os.path
import re
import sys
import time
import tomllib
import pprint

import jiramail

from datetime import datetime
from datetime import timedelta

try:
    import jira
    import jira.resources
except ModuleNotFoundError as e:
    print("No module named 'jira' (https://github.com/pycontribs/jira).")
    print(" - in altlinux install: python3-module-jira")
    print(" - in opensuse install: python-jira")
    print(" - in debian install: python3-jira")
    print(" - in fedora install: python-jira")
    exit(1)


jserv = None
verbosity = 0


class Subject:
    def __init__(self, key, text):
        self.version = 1
        self.key = key
        self.text = text
        self.action = ""

    def __str__(self):
        subj = [ f"[{self.key}]" ]
        if self.action:
            subj.append(self.action)
        if self.text:
            subj.append(self.text)
        return " ".join(subj)


def chain(*iterables):
    for it in iterables:
        for element in it:
            yield element


def has_attrs(o, attrs):
    for attr in attrs:
        if not hasattr(o, attr):
            return False
    return True


def get_issue_field(issue, name):
    try:
        return issue.get_field(field_name=name)
    except AttributeError:
        pass
    field = jserv.field_by_name(name.lower(), None)
    if field:
        try:
            return issue.get_field(field["id"])
        except AttributeError:
            pass
    return None


def get_user(user):
    name = ""
    addr = "unknown"

    if hasattr(user, "displayName"):
        name = user.displayName
    if hasattr(user, "emailAddress"):
        addr = user.emailAddress

    return email.utils.formataddr((name, addr), charset='utf-8')


def get_date(data):
    dt = datetime.fromisoformat(data)
    return email.utils.format_datetime(dt)


def get_issue_info(issue, fields):
    ret = []
    for field in fields:
        value = get_issue_field(issue, field['name'])
        if value:
            ret.append( (field['label'], field['getter'](value)) )
    return ret


def decode_markdown(message):
    body = []
    links = []

    def repl_link(m):
        links.append(m.group(2))
        return f"\"{m.group(1)}\"[{len(links)}]"

    def repl_quote(m):
        return "\n" + "\n".join([ f"> {x}" for x in m.group(1).splitlines() ]) + "\n"

    def repl_code(m):
        return "\n" + "\n".join([ f"| {x}" for x in m.group(1).splitlines() ]) + "\n"

    message = re.sub(r'\[([^|]+)\|([^\]]+)\]', repl_link, message)
    message = re.sub(r'{{(.*?)}}', r"\1", message)
    message = re.sub(r'{quote}(.*?){quote}', repl_quote, message, flags=re.M|re.S)
    message = re.sub(r'{code:[^}]*}\s*(.*?){code}', repl_code, message, flags=re.M|re.S)

    body.append(message)

    if links:
        body.append("")
        for i,link in enumerate(links):
            body.append(f"[{i+1}] {link}")

    return body


def issue_email(issue, date, author, subject, message):
    mail = email.message.EmailMessage()

    mail.add_header("Date", get_date(date))
    mail.add_header("From", get_user(author))
    mail.add_header("Message-Id", f"<v{subject.version}-{issue.id}@issue.jira>")

    if subject.version > 1:
        parent_msg_id = f"<v1-{issue.id}@issue.jira>"

        mail.add_header("In-Reply-To", parent_msg_id)
        mail.add_header("References", "{parent_id} {msg_id}".format(
            parent_id = parent_msg_id,
            msg_id = mail.get("Message-Id")))

        subject.action = "U:"
    else:
        subject.action = ""

    mail.add_header("Subject", str(subject))

    body = []

    info = get_issue_info(issue, [
        { "label": "Type"    , "name": "issuetype", "getter": lambda a: a.name },
        { "label": "Severity", "name": "severity" , "getter": lambda a: a.value },
        { "label": "Priority", "name": "priority" , "getter": lambda a: a.name },
        { "label": "Labels"  , "name": "labels"   , "getter": lambda a: ", ".join(map(lambda b: f'"{b}"', a)) },
        { "label": "Keywords", "name": "keywords" , "getter": lambda a: ", ".join(map(lambda b: f'"{b}"', a)) },
        ])
    if info:
        name_width  = max([ len(el[0]) for el in info ]) + 1
        for el in info:
            body.append("{:>{name_width}}: {}".format(*el, name_width = name_width))

        body.append("---")
        body.append("")

    body += decode_markdown(message)

    body.append("")
    body.append("-- ")
    body.append(issue.permalink())
    body.append("")

    mail.set_content("\n".join(body))

    return mail


def changes_email(issue_id, change_id, date, author, subject, changes):
    mail = email.message.EmailMessage()

    subject.action = "U:"
    status = ""

    mail.add_header("Date", get_date(date))
    mail.add_header("From", get_user(author))
    mail.add_header("Message-Id", f"<{issue_id}-{change_id}@changes.issue.jira>")

    parent_msg_id = f"<v1-{issue_id}@issue.jira>"

    mail.add_header("In-Reply-To", parent_msg_id)
    mail.add_header("References", "{parent_id} {msg_id}".format(
        parent_id = parent_msg_id,
        msg_id = mail.get("Message-Id")))

    name_len = 0
    old_len  = 0

    for item in changes:
        if name_len < len(item.field):
            name_len = len(item.field)
        if item.fromString and old_len < len(item.fromString):
            old_len = len(item.fromString)
        if item.fieldtype == "jira" and item.field == "status" and item.toString:
            status = f" [{item.toString}]"

    name_len += 1
    old_len  += 1

    body = []
    for item in changes:
        body.append("{name:>{name_len}}: {old:>{old_len}} -> {new}".format(
            name = item.field,
            old = item.fromString or '""',
            new = item.toString   or '""',
            name_len = name_len,
            old_len = old_len))

    body.append("")
    body.append("-- ")
    body.append("")

    mail.add_header("Subject", str(subject) + status)
    mail.set_content("\n".join(body))

    return mail


def comment_email(issue, comment, date, author, subject, message):
    mail = email.message.EmailMessage()

    parent_msg_id = f"<v1-{issue.id}@issue.jira>"
    subject.action = "C:"

    mail.add_header("Subject", str(subject))
    mail.add_header("Date", get_date(date))
    mail.add_header("From", get_user(author))
    mail.add_header("Message-Id", f"<{issue.id}-{comment.id}@comment.issue.jira>")

    mail.add_header("In-Reply-To", parent_msg_id)
    mail.add_header("References", "{parent_id} {msg_id}".format(
        parent_id = parent_msg_id,
        msg_id = mail.get("Message-Id")))

    body = []

    if hasattr(comment, "visibility") and hasattr(comment.visibility, "value"):
        body.append(f"[Visible only to {comment.visibility.value}]")
        body.append("---")

    body += decode_markdown(message)

    body.append("")
    body.append("-- ")
    body.append("{url}?focusedId={commentid}#comment-{commentid}".format(
        url = issue.permalink(),
        commentid = comment.id))
    body.append("")

    mail.set_content("\n".join(body))

    return mail


def add_issue(issue, mbox):
    jiramail.verbose(2, f"processing issue {issue.key} ...")
    #pprint.pprint(issue.raw)

    date = get_issue_field(issue, "created")
    summary = get_issue_field(issue, "summary")
    description = get_issue_field(issue, "description")

    history = None
    changes = []

    subject = Subject(issue.key, summary)

    for el in sorted(
            chain(issue.changelog.histories, issue.fields.comment.comments),
            key = lambda x: datetime.fromisoformat(x.created),
            reverse = False):

        if isinstance(el, jira.resources.PropertyHolder):
            if not has_attrs(el, ["author", "created", "items"]):
                # The object doesn't look like an issue state change.
                continue

            if history:
                t1 = datetime.fromisoformat(history.created)
            else:
                t1 = datetime.fromisoformat("1970-01-01T00:00:01.000+0000")
            t2 = datetime.fromisoformat(el.created)

            if changes and (
                    el.author.emailAddress != history.author.emailAddress or
                    (t2 - t1) >= timedelta(hours = 1)):
                mail = changes_email(issue.id, history.id, history.created, history.author, subject, changes)
                mbox.append(mail)
                changes = []

            for item in el.items:
                if not has_attrs(item, ["fieldtype", "field"]):
                    continue

                if item.fieldtype == "jira" and item.field == "description":
                    if changes:
                        mail = changes_email(issue.id, el.id + "-0", el.created, el.author, subject, changes)
                        mbox.append(mail)
                        changes = []

                    mail = issue_email(issue, date, el.author, subject, item.fromString or "")
                    mbox.append(mail)

                    date = el.created
                    subject.version += 1
                    continue

                if item.fieldtype == "jira" and item.field == "Comment":
                    continue

                if item.fieldtype == "jira" and item.field == "summary":
                    subject.text = item.toString

                if item.fromString or item.toString:
                    changes.append(item)

            history = el
            continue

        if isinstance(el, jira.resources.Comment):
            if not has_attrs(el, ["id", "created", "author", "body"]):
                # Something strange with this object
                continue

            mail = comment_email(issue, el, el.created, el.author, subject, el.body)
            mbox.append(mail)
            continue

        jiramail.verbose(0, f"unknown history item: {repr(el)}")

    if history and changes:
        mail = changes_email(issue.id, history.id, history.created, history.author, subject, changes)
        mbox.append(mail)

    history = None
    changes = []

    mail = issue_email(issue, date, issue.fields.reporter, subject, description or "")
    mail.add_header("To", get_user(issue.fields.assignee))
    mbox.append(mail)


def process_query(query, jserv, mbox):
    pos = 0
    chunk = 50

    jiramail.verbose(2, f"processing query `{query}` ...")

    while True:
        res = jserv.jira.search_issues(query,
                                       expand = "changelog",
                                       startAt = pos,
                                       maxResults = chunk)
        if not res:
            break

        if pos == 0:
            jiramail.verbose(1, f"query `{query}` found {res.total} issues")

        for issue in res:
            add_issue(issue, mbox)

        if res.isLast:
            break
        pos += chunk


def main(cmdargs: argparse.Namespace) -> int:
    global jserv, verbosity

    jiramail.verbosity = cmdargs.verbose

    config = jiramail.read_config()
    jserv = jiramail.Connection(config.get("jira", {}))
    mbox = jiramail.Mailbox(cmdargs.mailbox)

    for username in cmdargs.assignee:
        process_query(f"assignee = '{username}'", jserv, mbox)

    for query in cmdargs.queries:
        process_query(query, jserv, mbox)

    for key in cmdargs.issues:
        issue = jserv.jira.issue(key, expand = "changelog")
        add_issue(issue, mbox)

    mbox.close()

    return 0
