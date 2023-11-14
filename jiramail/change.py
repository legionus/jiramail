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

from typing import Optional, Dict, List, Tuple, Callable, Any, TextIO

import jira
import jira.resources
import jira.resilientsession

import jiramail

logger = jiramail.logger

dry_run: bool = False
no_reply: bool = False


def set_mail_flags(mail: email.message.Message, flags: str) -> None:
    header_status = ""
    header_xstatus = ""

    for flag in ('R', 'O'):
        if flag in flags:
            header_status += flag

    for flag in ('D', 'F', 'A'):
        if flag in flags:
            header_xstatus += flag

    del mail["Status"]
    del mail["X-Status"]

    mail["Status"] = header_status
    mail["X-Status"] = header_xstatus


def command_issue_assign(issue: jira.resources.Issue,
                         user_id: str) -> jira.resources.Issue | jiramail.Error:
    try:
        if user_id != "%me":
            user = jiramail.jserv.jira.user(user_id)
        else:
            user = jiramail.jserv.jira.session()

    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to get \"{user_id}\" user: {e.text}")

    try:
        if not dry_run:
            jiramail.jserv.jira.assign_issue(issue.key, user.name)

    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to assign issue: {e}")

    return issue


def command_issue_comment(issue: jira.resources.Issue,
                          text: str) -> jira.resources.Issue | jiramail.Error:
    try:
        if not dry_run:
            jiramail.jserv.jira.add_comment(issue, text)

    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to add comment to issue {issue.key}: {e}")

    return issue


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


def fields_from_words(words: List[str],
                      issue: Optional[jira.resources.Issue],
                      meta_info: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | jiramail.Error:
    fields: Dict[str, Any] = {}

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

        meta = meta_info["ids"].get(name, None)
        if not meta:
            meta = meta_info["names"].get(name.lower(), None)
            if not meta:
                return jiramail.Error(f"the field \"{name}\" not found")
            f_id = meta["id"]
        else:
            f_id = name

        if len(meta["operations"]) > 0 and action not in meta["operations"]:
            return jiramail.Error(f"operation \"{action}\" not supported for field \"{meta['name']}\"")

        logger.debug("FIELD id=(%s) name=(%s)", f_id, meta['name'])

        if len(value) == 0:
            fields[f_id] = None
            continue

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
                        if action == "add" and issue:
                            fields[f_id] += append_from(issue, f_id, lambda x: x)
                        fields[f_id].append(value)

                    case "option":
                        if action == "add" and issue:
                            fields[f_id] += append_from(issue, f_id, lambda x: {"value": x.value})
                        fields[f_id].append({"value": value})

                    case _:
                        if action == "add" and issue:
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

    return fields


def command_issue_change(issue: jira.resources.Issue,
                         words: List[str]) -> jira.resources.Issue | jiramail.Error:

    meta_info: Dict[str, Dict[str, Any]] = {
            "names": {},
            "ids": {},
            }

    for i, v in jiramail.jserv.jira.editmeta(issue.key)["fields"].items():
        if "id" not in v:
            v["id"] = i
        meta_info["names"][v["name"].lower()] = v
        meta_info["ids"][i] = v

    fields = fields_from_words(words, issue, meta_info)

    if isinstance(fields, jiramail.Error):
        return fields

    try:
        if fields:
            if not dry_run:
                issue.update(fields=fields)
            else:
                logger.debug(pprint.pformat(fields))

    except jira.exceptions.JIRAError as e:
        err = e.response.json()["errors"]
        return jiramail.Error(f"unable to change fields of issue {issue.key}: {err}")

    return issue


def command_issue_create(subject: str,
                         content: List[str],
                         words: List[str]) -> jira.resources.Issue | jiramail.Error:
    jiramail.jserv.fill_fields()

    meta_info: Dict[str, Dict[str, Any]] = {
            "names": jiramail.jserv.fields_by_name,
            "ids": {},
            }

    for v in meta_info["names"].values():
        meta_info["ids"][v["id"]] = v

    fields = fields_from_words(words, None, meta_info)

    if isinstance(fields, jiramail.Error):
        return fields

    if "summary" not in fields:
        fields["summary"] = subject

    if "description" not in fields:
        fields["description"] = "\n".join(content)

    try:
        if dry_run:
            logger.debug(pprint.pformat(fields))

            issue = jira.resources.Issue(options={},
                                         session=jira.resilientsession.ResilientSession())
            issue.id = "0"
            issue.key = "NONE-0"
        else:
            issue = jiramail.jserv.jira.create_issue(fields=fields)

    except jira.exceptions.JIRAError as e:
        err = e.response.json()["errors"]
        return jiramail.Error(f"unable to create issue: {err}")

    return issue


def find_issue_key(mail: email.message.Message) -> Any:
    for val in ("X-Jiramail-Issue-Id", "X-Jiramail-Issue-Key"):
        if val in mail:
            return mail[val]

    for val in mail.get_all("References", []):
        for ref in val.split():
            m = re.match(r'^[<]?v\d+-(?P<issue_id>[^@]+)@issue.jira[>]?', ref)
            if not m:
                continue
            return m.group('issue_id')
    return ""


def command_issue(mail: email.message.Message,
                  content: List[str],
                  args: List[str]) -> None | jiramail.Error:
    if len(args) < 1:
        return jiramail.Error(f"issue command is too short: {args}")

    if args[0] in ("create"):
        args.pop(0)

        if len(args) % 3 != 0:
            return jiramail.Error("'create' keyword requires at least 3 arguments")

        issue = command_issue_create(mail.get("Subject", ""), content, args)

        if isinstance(issue, jiramail.Error):
            return issue

        del mail["X-Jiramail-Issue-Id"]
        del mail["X-Jiramail-Issue-Key"]

        mail["X-Jiramail-Issue-Id"] = f"{issue.id}"
        mail["X-Jiramail-Issue-Key"] = f"{issue.key}"

        return None

    if args[0] in ("assign", "comment", "change"):
        key = find_issue_key(mail)
        if not key:
            return jiramail.Error("issue number not found. Maybe it's because you don't reply to the generated email.")
    else:
        key = args.pop(0)

    if len(args) < 1:
        return jiramail.Error("issue command requires action")

    action = args.pop(0)

    try:
        issue = jiramail.jserv.jira.issue(key)
    except jira.exceptions.JIRAError as e:
        return jiramail.Error(f"unable to get {key} issue: {e.text}")

    match action:
        case "assign":
            if len(args) < 1:
                return jiramail.Error("'assign' keyword requires argument")
            res = command_issue_assign(issue, args[0])
        case "comment":
            if len(args) < 1:
                return jiramail.Error("'comment' keyword requires argument")
            res = command_issue_comment(issue, args[0])
        case "change":
            if len(args) % 3 != 0:
                return jiramail.Error("'change' keyword requires at least 3 arguments")
            res = command_issue_change(issue, args)
        case _:
            res = jiramail.Error(f"issue: unknown action: {action}")

    if isinstance(res, jiramail.Error):
        return res
    return None


def get_words(s: str) -> List[str]:
    return [x for x in re.split(r'("[^"]+"|\'[^\']+\'|\S+)', s) if len(x.strip()) > 0]


class Command:
    def __init__(self) -> None:
        self.words: List[str] = []
        self.raw: List[str] = []
        self.error: Optional[jiramail.Error] = None

    def name(self) -> str:
        if len(self.words) > 1:
            return self.words[0]
        return "None"

    def args(self) -> List[str]:
        if len(self.words) > 1:
            return self.words[1:]
        return []

    def add_raw(self, line: str) -> None:
        if line.endswith("\r\n"):
            self.raw.append(line[:-2])
        elif line.endswith("\n"):
            self.raw.append(line[:-1])
        else:
            self.raw.append(line)

    def __str__(self) -> str:
        return f"{self.__class__}: {self.name()} {self.args()}"

    def __repr__(self) -> str:
        return self.__str__()


def parse_commands(fd: TextIO) -> Tuple[List[Command], List[str]]:
    commands: List[Command] = []
    content: List[str] = []

    for value in fd:
        m = re.match(r'^\s*jira\s+(.*)\s*$', value)
        if not m:
            content.append(value[:-1])
            continue

        command = Command()
        command.add_raw(value)
        command.words += get_words(m.group(1))

        while len(command.words) > 0 and command.words[-1] == "\\":
            value = fd.readline()
            if not value:
                break

            command.words.pop()
            command.add_raw(value)
            command.words += get_words(command.raw[-1])

        for i, word in enumerate(command.words):
            if word.startswith("<<"):
                token = word[2:]
                token_found = False
                heredoc = []

                for value in fd:
                    command.add_raw(value)

                    token_found = command.raw[-1] == token
                    if token_found:
                        break

                    heredoc.append(command.raw[-1])

                if not token_found:
                    command.error = jiramail.Error(f"enclosing token '{token}' not found")
                    continue

                command.words[i] = "\n".join(heredoc)

            elif word.startswith('"') or word.startswith("'"):
                command.words[i] = word[1:-1]

        if not command.error:
            if len(command.words) < 1:
                command.error = jiramail.Error(f"command is too short: {command.words}")
                continue

            if command.name() != "issue":
                command.error = jiramail.Error(f"ERROR: unknown keyword \"{command.name()}\"")

        commands.append(command)

    return commands, content


def process_commands(mail: email.message.Message, fd: TextIO,
                     replies: List[email.message.EmailMessage]) -> bool:
    ret = True

    commands, content = parse_commands(fd)

    for command in commands:
        logger.debug("processing command: %s", command.words)

        if isinstance(command.error, jiramail.Error):
            logger.critical("%s", command.error.message)
            ret = False
            continue

        if command.name() == "issue":
            r = command_issue(mail, content, command.args())
            if isinstance(r, jiramail.Error):
                logger.critical("%s", r.message)
                command.error = r
                ret = False

    if commands and not no_reply:
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
        set_mail_flags(resp, "ROA")

        subj = mail.get("Subject")
        if subj:
            subject.append(re.sub(r'[\r\n]', '', subj))
        resp.add_header("Subject", " ".join(subject))

        parent_id = mail.get("Message-Id")
        if parent_id:
            resp.add_header("In-Reply-To", parent_id)
            resp.add_header("References", f"{parent_id} {msg_id}")

        out: List[str] = []

        for command in commands:
            out += [f"> {line}" for line in command.raw]
            out.append("")
            if isinstance(command.error, jiramail.Error):
                out.append(f"ERROR: {command.error.message}")
            else:
                out.append("DONE")
            out.append("")

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
    global dry_run, no_reply

    dry_run = cmdargs.dry_run
    no_reply = cmdargs.no_reply

    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        logger.critical("%s", config.message)
        return jiramail.EX_FAILURE

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        logger.critical("unable to connect to jira: %s", e)
        return jiramail.EX_FAILURE

    rc = jiramail.EX_SUCCESS

    if cmdargs.mailbox != "-":
        replies: List[email.message.EmailMessage] = []

        try:
            mbox = jiramail.Mailbox(cmdargs.mailbox)
        except Exception as e:
            logger.critical("unable to open mailbox: %s", e)
            return jiramail.EX_FAILURE

        for key in mbox.iterkeys():
            mail = mbox.get_message(key)

            flags = mail.get_flags()
            if "A" in flags:
                continue

            if not process_mail(mail, replies):
                rc = jiramail.EX_FAILURE

            set_mail_flags(mail, "ROA")
            mbox.update_message(key, mail)

        if cmdargs.stdin:
            stdin_mail = email.message_from_file(sys.stdin)
            set_mail_flags(stdin_mail, "ROA")
            mbox.append(stdin_mail)

            if not process_mail(stdin_mail, replies):
                rc = jiramail.EX_FAILURE

        for reply in replies:
            mbox.append(reply)

        mbox.close()

    else:
        no_reply = True
        empty = email.message.EmailMessage()

        if not process_commands(empty, sys.stdin, []):
            rc = jiramail.EX_FAILURE

    return rc
