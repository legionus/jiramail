#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import email
import email.utils
import re

from datetime import datetime
from datetime import timedelta

from typing import Optional, Dict, List, Tuple, Union, Any

from collections.abc import Iterator, Iterable

import jira
import jira.resources

import jiramail


class Subject:
    def __init__(self, key: str, text: str) -> None:
        self.version = 1
        self.key = key
        self.text = text
        self.action = ""

    def __str__(self) -> str:
        subj = [f"[{self.key}]"]
        if self.action:
            subj.append(self.action)
        if self.text:
            subj.append(self.text)
        return " ".join(subj)


class User:
    def __init__(self, user: Any):
        self.name = ""
        self.addr = "unknown"

        if isinstance(user, jira.resources.UnknownResource) or \
                isinstance(user, jira.resources.User):
            self.from_resource(user)

    def __str__(self) -> str:
        return email.utils.formataddr((self.name, self.addr), charset='utf-8')

    def to_string(self) -> str:
        return str(self)

    def from_resource(self, user: Union[jira.resources.UnknownResource,
                                        jira.resources.User]) -> None:
        if hasattr(user, "displayName"):
            self.name = user.displayName
        if hasattr(user, "emailAddress"):
            self.addr = user.emailAddress


class Property:
    def __init__(self, prop: jira.resources.PropertyHolder):
        self.prop = prop
        self.id = getattr(prop, "id")
        self.created = getattr(prop, "created")
        self.author = getattr(prop, "author")
        self.items = getattr(prop, "items", [])


def chain(*iterables: Iterable[Any]) -> Iterator[Any]:
    for it in iterables:
        for element in it:
            yield element


def has_attrs(o: object, attrs: List[str]) -> bool:
    for attr in attrs:
        if not hasattr(o, attr):
            return False
    return True


def get_issue_field(issue: jira.resources.Issue, name: str) -> Optional[Any]:
    try:
        return issue.get_field(field_name=name)
    except AttributeError:
        pass
    field = jiramail.jserv.field_by_name(name.lower(), None)
    if field:
        try:
            return issue.get_field(field["id"])
        except AttributeError:
            pass
    return None


def get_date(data: str) -> str:
    dt = datetime.fromisoformat(data)
    return email.utils.format_datetime(dt)


def get_issue_info(issue: jira.resources.Issue,
                   items: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    ret = []
    for item in items:
        field = jiramail.jserv.field_by_name(item['name'])
        value = get_issue_field(issue, item['name'])
        if value:
            ret.append((field['name'], item['getter'](value)))
    return ret


def decode_markdown(message: str) -> List[str]:
    body = []
    links = []

    def repl_link(m: re.Match[str]) -> str:
        links.append(m.group(2))
        return f"\"{m.group(1)}\"[{len(links)}]"

    def repl_quote(m: re.Match[str]) -> str:
        return "\n" + "\n".join([f"> {x}" for x in m.group(1).splitlines()]) + "\n"

    def repl_code(m: re.Match[str]) -> str:
        return "\n" + "\n".join([f"| {x}" for x in m.group(1).splitlines()]) + "\n"

    def repl_noformat(m: re.Match[str]) -> str:
        return m.group(1)

    message = re.sub(r'\[([^|]+)\|([^\]]+)\]', repl_link, message)
    message = re.sub(r'{{(.*?)}}', r"\1", message)
    message = re.sub(r'{quote}(.*?){quote}', repl_quote, message, flags=re.M | re.S)
    message = re.sub(r'{code:[^}]*}\s*(.*?){code}', repl_code, message, flags=re.M | re.S)
    message = re.sub(r'{noformat}(.*?){noformat}', repl_noformat, message, flags=re.M | re.S)

    body.append(message)

    if links:
        body.append("")
        for i, link in enumerate(links):
            body.append(f"[{i+1}] {link}")

    return body


def issue_email(issue: jira.resources.Issue, date: str, author: User,
                subject: Subject, message: str) -> email.message.EmailMessage:
    mail = email.message.EmailMessage()

    msg_id = f"<v{subject.version}-{issue.id}@issue.jira>"

    mail.add_header("Date", get_date(date))
    mail.add_header("From", str(author))
    mail.add_header("Message-Id", msg_id)
    mail.add_header("Reply-To", "change@jira")
    mail.add_header("X-Jiramail-Issue-Id", f"{issue.id}")
    mail.add_header("X-Jiramail-Issue-Key", f"{issue.key}")

    if subject.version > 1:
        parent_id = f"<v1-{issue.id}@issue.jira>"

        mail.add_header("In-Reply-To", parent_id)
        mail.add_header("References", f"{parent_id} {msg_id}")

        subject.action = "U:"
    else:
        subject.action = ""

    mail.add_header("Subject", str(subject))

    body = []

    info = get_issue_info(issue, [
        {"name": "issuetype", "getter": lambda a: a.name},
        {"name": "severity",  "getter": lambda a: a.value},
        {"name": "priority",  "getter": lambda a: a.name},
        {"name": "labels",    "getter": lambda a: ", ".join(map(lambda b: f'"{b}"', a))},
        {"name": "keywords",  "getter": lambda a: ", ".join(map(lambda b: f'"{b}"', a))},
        ])
    if info:
        name_width = max([len(el[0]) for el in info]) + 1
        for name, value in info:
            body.append(f"{name:>{name_width}}: {value}")

        body.append("---")
        body.append("")

    body += decode_markdown(message)

    body.append("")
    body.append("-- ")
    body.append(issue.permalink()) # type: ignore
    body.append("")

    mail.set_content("\n".join(body))

    return mail


def changes_email(issue: jira.resources.Issue, change_id: str, date: str, author: User,
                  subject: Subject, changes: List[Any]) -> email.message.EmailMessage:
    mail = email.message.EmailMessage()

    msg_id = f"<{issue.id}-{change_id}@changes.issue.jira>"
    parent_id = f"<v1-{issue.id}@issue.jira>"
    subject.action = "U:"
    status = ""

    mail.add_header("Date", get_date(date))
    mail.add_header("From", str(author))
    mail.add_header("Message-Id", msg_id)
    mail.add_header("Reply-To", "change@jira")
    mail.add_header("In-Reply-To", parent_id)
    mail.add_header("References", f"{parent_id} {msg_id}")
    mail.add_header("X-Jiramail-Issue-Id", f"{issue.id}")
    mail.add_header("X-Jiramail-Issue-Key", f"{issue.key}")

    name_len = 0
    old_len = 0

    for item in changes:
        if name_len < len(item.field):
            name_len = len(item.field)
        if item.fromString and old_len < len(item.fromString):
            old_len = len(item.fromString)
        if item.fieldtype == "jira" and item.field == "status" and item.toString:
            status = f" [{item.toString}]"

    name_len += 1
    old_len += 1

    body = []
    for item in changes:
        old = item.fromString or '""'
        new = item.toString or '""'
        body.append(f"{item.field:>{name_len}}: {old:>{old_len}} -> {new}")

    body.append("")
    body.append("-- ")
    body.append("")

    mail.add_header("Subject", str(subject) + status)
    mail.set_content("\n".join(body))

    return mail


def comment_email(issue: jira.resources.Issue, comment: jira.resources.Comment,
                  date: str, author: User, subject: Subject, message: str) -> email.message.EmailMessage:
    mail = email.message.EmailMessage()

    msg_id = f"<{issue.id}-{comment.id}@comment.issue.jira>"
    parent_id = f"<v1-{issue.id}@issue.jira>"
    subject.action = "C:"

    mail.add_header("Subject", str(subject))
    mail.add_header("Date", get_date(date))
    mail.add_header("From", str(author))
    mail.add_header("Message-Id", msg_id)
    mail.add_header("Reply-To", "change@jira")
    mail.add_header("In-Reply-To", parent_id)
    mail.add_header("References", f"{parent_id} {msg_id}")
    mail.add_header("X-Jiramail-Issue-Id", f"{issue.id}")
    mail.add_header("X-Jiramail-Issue-Key", f"{issue.key}")

    body = []

    if hasattr(comment, "visibility") and hasattr(comment.visibility, "value"):
        body.append(f"[Visible only to {comment.visibility.value}]")
        body.append("---")

    body += decode_markdown(message)

    body.append("")
    body.append("-- ")
    body.append("{url}?focusedId={commentid}#comment-{commentid}".format(
        url=issue.permalink(), # type: ignore
        commentid=comment.id))
    body.append("")

    mail.set_content("\n".join(body))

    return mail


def add_issue(issue: jira.resources.Issue, mbox: jiramail.Mailbox) -> None:
    jiramail.verbose(2, f"processing issue {issue.key} ...")
    # pprint.pprint(issue.raw)

    date = str(get_issue_field(issue, "created"))
    summary = str(get_issue_field(issue, "summary"))
    description = str(get_issue_field(issue, "description"))

    history: Optional[Property] = None
    changes: List[str] = []

    subject = Subject(issue.key, summary)

    for el in sorted(
            chain(issue.changelog.histories, issue.fields.comment.comments),
            key=lambda x: datetime.fromisoformat(x.created),
            reverse=False):

        if isinstance(el, jira.resources.PropertyHolder):
            if not has_attrs(el, ["author", "created", "items"]):
                # The object doesn't look like an issue state change.
                continue

            prop = Property(el)

            if history:
                t1 = datetime.fromisoformat(history.created)
            else:
                t1 = datetime.fromisoformat("1970-01-01T00:00:01.000+0000")
            t2 = datetime.fromisoformat(prop.created)

            if changes and history and (
                    prop.author.emailAddress != history.author.emailAddress or
                    (t2 - t1) >= timedelta(hours=1)):
                mail = changes_email(issue, history.id, history.created,
                                     User(history.author), subject, changes)
                mbox.append(mail)
                changes = []

            for item in prop.items:
                if not has_attrs(item, ["fieldtype", "field"]):
                    continue

                if item.fieldtype == "jira" and item.field == "description":
                    if changes:
                        mail = changes_email(issue, prop.id + "-0",
                                             prop.created, User(prop.author),
                                             subject, changes)
                        mbox.append(mail)
                        changes = []

                    mail = issue_email(issue, date, User(prop.author), subject,
                                       item.fromString or "")
                    mbox.append(mail)

                    date = prop.created
                    subject.version += 1
                    continue

                if item.fieldtype == "jira" and item.field == "Comment":
                    continue

                if item.fieldtype == "jira" and item.field == "summary":
                    subject.text = item.toString

                if item.fromString or item.toString:
                    changes.append(item)

            history = prop
            continue

        if isinstance(el, jira.resources.Comment):
            if not has_attrs(el, ["id", "created", "author", "body"]):
                # Something strange with this object
                continue

            mail = comment_email(issue, el, el.created, User(el.author),
                                 subject, el.body)
            mbox.append(mail)
            continue

        jiramail.verbose(0, f"unknown history item: {repr(el)}")

    if history and changes:
        mail = changes_email(issue, history.id, history.created,
                             User(history.author), subject, changes)
        mbox.append(mail)

    history = None
    changes = []

    mail = issue_email(issue, date, User(issue.fields.reporter), subject,
                       description or "")
    mail.add_header("To", User(issue.fields.assignee).to_string())
    mbox.append(mail)


def process_query(query: str, mbox: jiramail.Mailbox) -> None:
    pos = 0
    chunk = 50

    jiramail.verbose(2, f"processing query `{query}` ...")

    while True:
        res = jiramail.jserv.jira.search_issues(query,
                                       expand="changelog",
                                       startAt=pos,
                                       maxResults=chunk)
        if not res or not isinstance(res, jira.client.ResultList):
            break

        if pos == 0:
            jiramail.verbose(1, f"query `{query}` found {res.total} issues")

        for issue in res:
            add_issue(issue, mbox)

        if res.isLast:
            break
        pos += chunk


def main(cmdargs: argparse.Namespace) -> int:
    jiramail.verbosity = cmdargs.verbose

    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        jiramail.verbose(0, f"{config.message}")
        return jiramail.EX_FAILURE

    try:
        mbox = jiramail.Mailbox(cmdargs.mailbox)
    except Exception as e:
        jiramail.verbose(0, f"unable to open mailbox: {e}")
        return jiramail.EX_FAILURE

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        jiramail.verbose(0, f"unable to connect to jira: {e}")
        return jiramail.EX_FAILURE

    for username in cmdargs.assignee:
        process_query(f"assignee = '{username}'", mbox)

    for query in cmdargs.queries:
        process_query(query, mbox)

    for key in cmdargs.issues:
        issue = jiramail.jserv.jira.issue(key, expand="changelog")
        add_issue(issue, mbox)

    mbox.close()

    return jiramail.EX_SUCCESS
