#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

import os.path
import sys
import argparse
import time
import tomllib
import email
import mailbox
import pprint

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


def verbose(level: int, text: str):
	if verbosity > level:
		print(time.strftime("[%H:%M:%S]"), f"level={level}", text, file = sys.stderr, flush = True)


class Connection:
	def __init__(self, config_jira):
		self.config = config_jira
		self._fields = None

		options = {
			"check_update": False,
		}

		verbose(2, f"connecting to JIRA ...")

		if self.config["auth"] == "token":
			self.jira = jira.JIRA(self.config["server"],
					token_auth=self.config["token"],
					options = options)
		elif self.config["auth"] == "basic":
			self.jira = jira.JIRA(self.config["server"],
					basic_auth=(
						self.config["user"],
						self.config["password"]),
					options = options)
		else:
			raise KeyError(f"Unknown method: jira.auth: " + self.config.get("auth", "<missing>"))

		verbose(1, "connected to JIRA")

	def fields(self):
		if not self._fields:
			self._fields = self.jira.fields()
		return self._fields


class Mailbox:
	def __init__(self, path):
		verbose(2, f"openning the mailbox {path} ...")

		self.mbox = mailbox.mbox(path)
		self.msgid = {}

		for key in self.mbox.iterkeys():
			mail = self.mbox.get_message(key)
			if "Message-Id" in mail:
				msg_id = mail.get("Message-Id")
				self.msgid[msg_id] = True

		verbose(1, "mailbox is ready")

	def append(self, mail):
		if mail.get("Message-Id") not in self.msgid:
			self.mbox.add(mail)

	def close(self):
		self.mbox.close()


class Subject:
	def __init__(self, key, text):
		self.version = 1
		self.key = key
		self.text = text
		self.action = ""

	def __str__(self):
		return "".join([ f"[{self.key}] ", self.action, self.text ])


def read_config():
	config = None

	for config_file in [ "~/.jiramail", "~/.config/jiramail/config" ]:
		config_file = os.path.expanduser(config_file)

		if not os.path.exists(config_file):
			continue

		verbose(2, f"picking config file `{config_file}' ...")

		with open(config_file, "rb") as fd:
			config = tomllib.load(fd)
			break

	if not config:
		raise Exception("config file not found")

	verbose(1, "config has been read")
	return config


def chain(*iterables):
	for it in iterables:
		for element in it:
			yield element


def get_issue_field(issue: any, name: str) -> str:
	try:
		return issue.get_field(field_name=name)
	except AttributeError:
		pass
	for f_id in [ f["schema"]["customId"] for f in jserv.fields() if f["name"].lower() == name.lower() ]:
		try:
			return issue.get_field(f"customfield_{f_id}")
		except AttributeError:
			pass
	return None


def get_user(user) -> str:
	name = ""
	addr = "unknown"

	if hasattr(user, "displayName"):
		name = user.displayName
	if hasattr(user, "emailAddress"):
		addr = user.emailAddress

	return email.utils.formataddr((name, addr), charset='utf-8')


def get_date(data: str) -> str:
	dt = datetime.fromisoformat(data)
	return email.utils.format_datetime(dt)


def get_issue_info(issue, fields):
	ret = []
	for field in fields:
		value = get_issue_field(issue, field['name'])
		if value:
			ret.append( (field['label'], field['getter'](value)) )
	return ret


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

		subject.action = "U: "
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

	body.append(message)
	body.append("")
	body.append("-- ")
	body.append(issue.permalink())
	body.append("")

	mail.set_content("\n".join(body))

	return mail


def changes_email(issue_id, change_id, date, author, subject, changes):
	mail = email.message.EmailMessage()

	subject.action = "U: "

	mail.add_header("Subject", str(subject))
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

	mail.set_content("\n".join(body))

	return mail


def comment_email(issue, comment_id, date, author, subject, message):
	mail = email.message.EmailMessage()

	parent_msg_id = f"<v1-{issue.id}@issue.jira>"
	subject.action = "C: "

	mail.add_header("Subject", str(subject))
	mail.add_header("Date", get_date(date))
	mail.add_header("From", get_user(author))
	mail.add_header("Message-Id", f"<{issue.id}-{comment_id}@comment.issue.jira>")

	mail.add_header("In-Reply-To", parent_msg_id)
	mail.add_header("References", "{parent_id} {msg_id}".format(
			parent_id = parent_msg_id,
			msg_id = mail.get("Message-Id")))

	body = [ message ]
	body.append("")
	body.append("-- ")
	body.append("{url}?focusedId={commentid}#comment-{commentid}".format(
			url = issue.permalink(),
			commentid = comment_id))
	body.append("")

	mail.set_content("\n".join(body))

	return mail


def add_issue(issue, mbox):
	verbose(2, f"processing issue {issue.key} ...")

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
			if not hasattr(el, "author") or not hasattr(el, "created") or not hasattr(el, "items"):
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
				if item.fieldtype == "jira" and item.field == "description":
					if changes:
						mail = changes_email(issue.id, el.id, el.created, el.author, subject, changes)
						mbox.append(mail)
						changes = []

					if item.fromString:
						mail = issue_email(issue, date, el.author, subject, item.fromString)
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
			mail = comment_email(issue, el.id, el.created, el.author, subject, el.body)
			mbox.append(mail)
			continue

		verbose(0, "unknown history item:", repr(el), file = sys.stderr)

	if history and changes:
		mail = changes_email(issue.id, history.id, history.created, history.author, subject, changes)
		mbox.append(mail)

	history = None
	changes = []

	if description:
		mail = issue_email(issue, date, issue.fields.reporter, subject, description)
		mail.add_header("To", get_user(issue.fields.assignee))
		mbox.append(mail)

	return True


def parse_aruments():
	parser = argparse.ArgumentParser(
			prog = "jiramail",
			description = "Saves jira issues in mailbox format.",
			epilog = "Report bugs to authors.",
			allow_abbrev = True)

	parser.add_argument('-v', '--verbose',
			dest = "verbose", action = 'count', default = 0,
			help = "print a message for each action.")

	parser.add_argument("--query",
			dest = "queries", default = [], action = "append", metavar = "JQL",
			help = "jira query string.")

	parser.add_argument("--issue",
			dest = "issues", default = [], action = "append", metavar = "ISSUE-123",
			help = "issues to export.")

	parser.add_argument("outname",
			help = "path to mbox where emails should be added.")

	return parser.parse_args()



def main():
	global jserv, verbosity

	args = parse_aruments()
	verbosity = args.verbose

	config = read_config()
	jserv = Connection(config.get("jira", {}))
	mbox = Mailbox(args.outname)

	for query in args.queries:
		pos = 0
		chunk = 50

		verbose(2, f"processing query `{query}` ...")

		while True:
			res = jserv.jira.search_issues(query,
					expand = "changelog",
					startAt = pos,
					maxResults = chunk)
			if not res:
				break

			if pos == 0:
				verbose(1, f"query `{query}` found {res.total} issues")

			for issue in res:
				add_issue(issue, mbox)

			if res.isLast:
				break
			pos += chunk

	for key in args.issues:
		issue = jserv.jira.issue(key, expand = "changelog")
		add_issue(issue, mbox)

	mbox.close()


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		exit(1)

# vim: ft=python tw=200 noexpandtab
