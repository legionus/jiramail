#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import email
import email.utils
import io
import mailbox
import os.path
import re
import sys
import time
import tomllib
import pprint

from datetime import datetime

import jiramail

import jira
import jira.resources


jserv = None
dry_run = False
no_reply = False


def get_issue(key):
	try:
		issue = jserv.jira.issue(key)
	except jira.exceptions.JIRAError as e:
		return jiramail.Error(f"unable to get {key} issue: {e.text}")
	return issue


def command_issue_assign(issue, user_id):
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


def command_issue_comment(issue, text):
	try:
		if not dry_run:
			jserv.jira.add_comment(issue, text)

	except jira.exceptions.JIRAError as e:
		return jiramail.Error(f"unable to add comment to issue {issue.key}: {e}")

	return None


def valid_resource(kind, value, res, getter = None):
	if not getter:
		getter = lambda x: x.name

	value = value.lower()

	for x in res:
		if value == getter(x).lower():
			return x

	names = ", ".join([ "\"{}\"".format(getter(x)) for x in res ])
	return jiramail.Error(f"invalid {kind} \"{value}\" for project. Valid: {names}")


def append_from(issue, f_id, getter):
	try:
		return [ getter(o) for o in issue.get_field(f_id) ]
	except AttributeError:
		return []


def command_issue_change(issue, words):
	fields = {}

	fields_by_id = jserv.jira.editmeta(issue.key)["fields"]
	fields_by_name = {}

	for i, v in fields_by_id.items():
		fields_by_name[v["name"].lower()] = i

	for i in list(range(0, len(words), 3)):
		name   = words[i+0]
		action = words[i+1].lower()
		value  = words[i+2]

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
			obj = valid_resource(meta["name"], value,
					meta["allowedValues"],
					lambda x: x["value"] if "value" in x else x["name"])

			if isinstance(obj, jiramail.Error):
				return obj

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
							fields[f_id] += append_from(issue, f_id, lambda x: {"value": x.value })
						fields[f_id].append({"value": value})

					case _:
						if action == "add":
							fields[f_id] += append_from(issue, f_id, lambda x: {"name": x.name })
						fields[f_id].append({"name": value})

			case "option":
				fields[f_id] = {"value": value}

			case "issuetype" | "priority" | "resolution":
				fields[f_id] = {"name": value}

			case "number":
				if f["custom"]:
					if f["schema"]["custom"].endswith(":float"):
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


def command_issue(args):
	if len(args) < 2:
		return jiramail.Error("issue command is too short: {}".format(" ".join(args)))

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


def get_words(s):
	return [ x for x in re.split(r'("[^"]+"|\'[^\']+\'|\S+)', s) if len(x.strip()) > 0 ]


def process_commands(mail, fd, replies):
	ret = True
	out = []

	while True:
		value = fd.readline()
		if not value:
			break

		m = re.match("^\s*jira\s+(.*)\s*$", value[:-1])
		if not m:
			continue

		out.append(f"> {value[:-1]}")

		words = []
		words += get_words(m.group(1))

		while True:
			if len(words) == 0 or words[-1] != "\\":
				break
			words.pop()

			value = fd.readline()
			out.append(f"> {value[:-1]}")

			words += get_words(value)

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

					out.append(f"> {value[:-1]}")

					token_found = value[:-1] == token
					if token_found:
						break

					heredoc.append(value)

				if not token_found:
					jiramail.verbose(0, f"enclosing token '{token}' not found")
					words_valid = False
					continue

				words[i] = "".join(heredoc)

		if words_valid:
			if len(words) < 1:
				jiramail.verbose(0, "command is too short: {}".format(" ".join(words)))
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
					out.append(f"DONE")
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

		subject.append(mail.get("Subject"))

		resp = email.message.EmailMessage()
		resp.add_header("From", "jirachange")
		resp.add_header("Subject", " ".join(subject))
		resp.add_header("Date", email.utils.format_datetime(datetime.now()))
		resp.add_header("Message-Id", email.utils.make_msgid())
		resp.add_header("In-Reply-To", mail.get("Message-Id"))
		resp.add_header("References", "{parent_id} {msg_id}".format(
				parent_id = mail.get("Message-Id"),
				msg_id = resp.get("Message-Id")))
		resp.add_header("Status", "RO")
		resp.add_header("X-Status", "A")
		resp.set_content("\n".join(out))

		replies.append(resp)

	return ret


def main(cmdargs):
	global jserv, dry_run, no_reply

	jiramail.verbosity = cmdargs.verbose
	dry_run = cmdargs.dry_run
	no_reply = cmdargs.no_reply

	config = jiramail.read_config()
	jserv = jiramail.Connection(config.get("jira", {}))

	rc = 0

	if cmdargs.mailbox != "-":
		replies = []

		mbox = jiramail.Mailbox(cmdargs.mailbox)

		for key in mbox.iterkeys():
			mail = mbox.get_message(key)

			flags = mail.get_flags()
			if "A" in flags:
				continue

			for part in mail.walk():
				if part.get_content_type() != "text/plain":
					continue

				fd = io.StringIO(
					initial_value = part.get_payload(),
					newline = '\n')

				if not process_commands(mail, fd, replies):
					rc = 1

				mail.set_flags("ROA")
				mbox.update_message(key, mail)

		for mail in replies:
			mbox.append(mail)

		mbox.close()

	elif not process_commands(None, sys.stdin, []):
		rc = 1

	return rc

# vim: ft=python tw=200 noexpandtab