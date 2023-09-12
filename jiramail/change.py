#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import email
import email.utils
import io
import pprint
import re
import sys

from datetime import datetime

from typing import Optional, Dict, List, Callable, Any, TextIO

import jira
import jira.resources

import jiramail


jserv: jiramail.Connection
dry_run: bool = False
no_reply: bool = False


def get_issue(key: str) -> jira.resources.Issue | jiramail.Error:
    try:
        issue = jserv.jira.issue(key)
    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to get {key} issue: {e.text}")
    return issue


def command_issue_assign(issue: jira.resources.Issue, user_id: str) -> None | jiramail.Error:
    try:
        if user_id != "%me":
            user = jserv.jira.user(user_id)
        else:
            user = jserv.jira.session()

    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to get \"{user_id}\" user: {e.text}")

    try:
        if not dry_run:
            jserv.jira.assign_issue(issue.key, user.name)

    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to assign issue: {e}")

    return None


def command_issue_comment(issue: jira.resources.Issue, text: str) -> None | jiramail.Error:
    try:
        if not dry_run:
            jserv.jira.add_comment(issue, text)

    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to add comment to issue {issue.key}: {e}")

    return None


def valid_resource(kind: str, value: str, res: List[Dict[str, Any]],
                   getter: Optional[Callable[[Dict[str, Any]], str]] = None) -> Dict[str, Any] | jiramail.Error:
    if not getter:
        getter = lambda x: x["name"]

    value = value.lower()

    for x in res:
        if value == getter(x).lower():
            return x

    names = ", ".join([f"\"{getter(x)}\"" for x in res])
    return jiramail.Error(f"invalid {kind} \"{value}\" for project. Valid: {names}")


def append_from(issue: jira.resources.Issue, f_id: str,
                getter: Callable[[jira.resources.Resource], Any]) -> List[Any]:
    try:
        return [getter(o) for o in issue.get_field(f_id)]
    except AttributeError:
        return []


def command_issue_change(issue: jira.resources.Issue,
                         words: List[str]) -> None | jiramail.Error:
    fields: Dict[str, Any] = {}

    fields_by_id = jserv.jira.editmeta(issue.key)["fields"]
    fields_by_name = {}

    for i, v in fields_by_id.items():
        fields_by_name[v["name"].lower()] = i

    for i in list(range(0, len(words), 3)):
        name = words[i]
        action = words[i+1].lower()
        value = words[i+2]

        match action:
            case "add" | "+=":
                action = "add"
            case "set" | "=":
                action = "set"
            case _:
                return jiramail.Error(f"unknown operator \"{action}\"")

        if len(value) == 0:
            value = None

        f_id = fields_by_name.get(name.lower(), None)
        if not f_id:
            obj = fields_by_id.get(name, None)
            if not obj:
                return jiramail.Error(f"the field \"{name}\" not found")
            f_id = name

        meta = fields_by_id[f_id]

        if len(meta["operations"]) > 0 and action not in meta["operations"]:
            return jiramail.Error(f"operation \"{action}\" not supported for field \"{meta['name']}\"")

        jiramail.verbose(3, f"FIELD id=({f_id}) name=({meta['name']})")

        if "allowedValues" in meta:
            def get_value(x: Dict[str, Any]) -> str:
                return str(x["value"]) if "value" in x else str(x["name"])

            obj = valid_resource(meta["name"], value,
                                 meta["allowedValues"],
                                 get_value)

            if isinstance(obj, jiramail.Error):
                return obj

            value = get_value(obj)

        match meta["schema"]["type"]:
            case "array":
                if f_id not in fields:
                    fields[f_id] = []

                match meta["schema"]["items"]:
                    case "string":
                        if action == "add":
                            fields[f_id] += append_from(issue, f_id, lambda x: x)
                        fields[f_id].append(value)

                    case "option":
                        if action == "add":
                            fields[f_id] += append_from(issue, f_id, lambda x: {"value": x.value})
                        fields[f_id].append({"value": value})

                    case _:
                        if action == "add":
                            fields[f_id] += append_from(issue, f_id, lambda x: {"name": x.name})
                        fields[f_id].append({"name": value})

            case "option":
                fields[f_id] = {"value": value}

            case "issuetype" | "priority" | "resolution":
                fields[f_id] = {"name": value}

            case "number":
                if "custom" in meta["schema"]:
                    if meta["schema"]["custom"].endswith(":float"):
                        fields[f_id] = float(value)
                        continue
                fields[f_id] = int(value)

            case _:
                fields[f_id] = value

    try:
        if fields:
            if not dry_run:
                issue.update(fields=fields)
            else:
                jiramail.verbose(3, pprint.pformat(fields))

    except jira.exceptions.JIRAError as e:
        err = e.response.json()["errors"]
        return jiramail.Error(f"unable to change fields of issue {issue.key}: {err}")

    return None


def command_issue(args: List[str]) -> None | jiramail.Error:
    if len(args) < 2:
        return jiramail.Error(f"issue command is too short: {args}")

    key = args.pop(0)
    action = args.pop(0)

    issue = get_issue(key)
    if isinstance(issue, jiramail.Error):
        return issue

    match action:
        case "assign":
            if len(args) < 1:
                return jiramail.Error("'assign' keyword requires argument")
            return command_issue_assign(issue, args[0])
        case "comment":
            if len(args) < 1:
                return jiramail.Error("'comment' keyword requires argument")
            return command_issue_comment(issue, args[0])
        case "change":
            if len(args) % 3 != 0:
                return jiramail.Error("'change' keyword requires at least 3 arguments")
            return command_issue_change(issue, args)

    return jiramail.Error(f"issue: unknown action: {action}")


def get_words(s: str) -> List[str]:
    return [x for x in re.split(r'("[^"]+"|\'[^\']+\'|\S+)', s) if len(x.strip()) > 0]


def process_commands(mail: Optional[email.message.Message], fd: TextIO,
                     replies: List[email.message.EmailMessage]) -> bool:
    ret = True
    out = []

    while True:
        value = fd.readline()
        if not value:
            break

        line = str(value[:-1])

        m = re.match(r'^\s*jira\s+(.*)\s*$', line)
        if not m:
            continue

        out.append(f"> {line}")

        words = []
        words += get_words(m.group(1))

        while True:
            if len(words) == 0 or words[-1] != "\\":
                break
            words.pop()

            value = fd.readline()
            line = str(value[:-1])

            out.append(f"> {line}")

            words += get_words(line)

        for i, word in enumerate(words):
            if word.startswith('"') or word.startswith("'"):
                words[i] = word[1:-1]

        jiramail.verbose(2, f"processing command: {words}")

        words_valid = True

        for i, word in enumerate(words):
            if word.startswith("<<"):
                token = word[2:]
                token_found = False
                heredoc = []

                while True:
                    value = fd.readline()
                    if not value:
                        break

                    line = str(value[:-1])
                    out.append(f"> {line}")

                    token_found = line == token
                    if token_found:
                        break

                    heredoc.append(line)

                if not token_found:
                    jiramail.verbose(0, f"enclosing token '{token}' not found")
                    words_valid = False
                    continue

                words[i] = "\n".join(heredoc)

        if words_valid:
            if len(words) < 1:
                jiramail.verbose(0, f"command is too short: {words}")
                words_valid = False

        if words_valid:
            out.append("")

            if words[0] == "issue":
                r = command_issue(words[1:])
                if isinstance(r, jiramail.Error):
                    jiramail.verbose(0, f"{r.message}")
                    out.append(f"ERROR: {r.message}")
                    ret = False
                else:
                    out.append("DONE")
            else:
                out.append(f"ERROR: unknown keyword \"{words[0]}\"")
                ret = False

            out.append("")

    if out and mail and not no_reply:
        subject = []
        if ret:
            subject.append("[DONE]")
        else:
            subject.append("[FAIL]")
        if dry_run:
            subject.append("[TEST]")

        msg_id = email.utils.make_msgid()

        resp = email.message.EmailMessage()
        resp.add_header("From", "jirachange")
        resp.add_header("Date", email.utils.format_datetime(datetime.now()))
        resp.add_header("Message-Id", msg_id)
        resp.add_header("Status", "RO")
        resp.add_header("X-Status", "A")

        subj = mail.get("Subject")
        if subj:
            subject.append(subj)
        resp.add_header("Subject", " ".join(subject))

        parent_id = mail.get("Message-Id")
        if parent_id:
            resp.add_header("In-Reply-To", parent_id)
            resp.add_header("References", f"{parent_id} {msg_id}")

        resp.set_content("\n".join(out))
        replies.append(resp)

    return ret


def process_mail(mail: email.message.Message,
                 replies: List[email.message.EmailMessage]) -> bool:
    rc = True

    for part in mail.walk():
        if part.get_content_type() != "text/plain":
            continue

        fd = io.StringIO(
                initial_value=part.get_payload(),
                newline='\n')

        if not process_commands(mail, fd, replies):
            rc = False

    return rc


def main(cmdargs: argparse.Namespace) -> int:
    global jserv, dry_run, no_reply

    jiramail.verbosity = cmdargs.verbose
    dry_run = cmdargs.dry_run
    no_reply = cmdargs.no_reply

    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        jiramail.verbose(0, f"{config.message}")
        return jiramail.EX_FAILURE

    try:
        jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        jiramail.verbose(0, f"unable to connect to jira: {e}")
        return jiramail.EX_FAILURE

    rc = jiramail.EX_SUCCESS

    if cmdargs.mailbox != "-":
        replies: List[email.message.EmailMessage] = []

        try:
            mbox = jiramail.Mailbox(cmdargs.mailbox)
        except Exception as e:
            jiramail.verbose(0, f"unable to open mailbox: {e}")
            return jiramail.EX_FAILURE

        for key in mbox.iterkeys():
            mail = mbox.get_message(key)

            flags = mail.get_flags()
            if "A" in flags:
                continue

            if not process_mail(mail, replies):
                rc = jiramail.EX_FAILURE

            mail.set_flags("ROA")
            mbox.update_message(key, mail)

        if cmdargs.stdin:
            stdin_mail = email.message_from_file(sys.stdin)
            stdin_mail["Status"] = "RO"
            stdin_mail["X-Status"] = "A"

            mbox.append(stdin_mail)

            if not process_mail(stdin_mail, replies):
                rc = jiramail.EX_FAILURE

        for reply in replies:
            mbox.append(reply)

        mbox.close()

    elif not process_commands(None, sys.stdin, []):
        rc = jiramail.EX_FAILURE

    return rc
