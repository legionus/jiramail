# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

import configparser
import email
import logging
import mailbox
import os
import os.path
import re
import subprocess
import sys
import time

from typing import Optional, Dict, Tuple, List, Union, Any
from collections.abc import Iterator

import jira


__VERSION__ = '3'

EX_SUCCESS = 0 # Successful exit status.
EX_FAILURE = 1 # Failing exit status.

logger = logging.getLogger("jiramail")


class Error:
    def __init__(self, message: str):
        self.message = message


class Connection:
    def __init__(self, config_jira: Dict[str, Any]):
        logger.debug("connecting to JIRA ...")

        self.config = config_jira
        jira_auth = self.config.get("auth", "<missing>")

        match jira_auth:
            case "token":
                self.jira = jira.JIRA(self.config["server"],
                                      token_auth=self.config["token"],
                                      options={"check_update": False})
            case "basic":
                self.jira = jira.JIRA(self.config["server"],
                                      basic_auth=(
                                          self.config["user"],
                                          self.config["password"]),
                                      options={"check_update": False})
            case _:
                raise KeyError(f"unknown method: jira.auth: {jira_auth}")

        logger.info("connected to JIRA")

        self.fields_by_name: Dict[str, Dict[str, Any]] = {}

    def fill_fields(self) -> None:
        if self.fields_by_name:
            return

        for v in self.jira.fields():
            if "clauseNames" in v:
                for n in v["clauseNames"]:
                    self.fields_by_name[n.lower()] = v
            self.fields_by_name[v["name"].lower()] = v

    def field_by_name(self, name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        self.fill_fields()
        return self.fields_by_name.get(name, default)


jserv: Connection


class Mailbox:
    def __init__(self, path: str):
        logger.debug("openning the mailbox `%s' ...", path)

        self.mbox = mailbox.mbox(path)
        self.msgid = {}

        for key in self.mbox.iterkeys():
            mail = self.mbox.get_message(key)
            if "Message-Id" in mail:
                msg_id = mail.get("Message-Id")
                self.msgid[msg_id] = True

        logger.info("mailbox is ready")

    def get_message(self, key: str) -> mailbox.mboxMessage:
        return self.mbox.get_message(key)

    def update_message(self, key: str, mail: email.message.Message) -> None:
        self.mbox.update([(key, mail)])

    def append(self, mail: email.message.Message) -> None:
        msg_id = mail.get("Message-Id")

        if msg_id not in self.msgid:
            self.mbox.add(mail)
            self.msgid[msg_id] = True

    def iterkeys(self) -> Iterator[Any]:
        return self.mbox.iterkeys()

    def close(self) -> None:
        self.mbox.close()


def _run_command(cmdargs: List[str], stdin: Optional[bytes] = None,
                 rundir: Optional[str] = None) -> Tuple[int, bytes, bytes]:
    if rundir:
        logger.debug("changing dir to %s", rundir)
        curdir = os.getcwd()
        os.chdir(rundir)
    else:
        curdir = None

    logger.debug("running %s", cmdargs)
    sp = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, error) = sp.communicate(input=stdin)
    if curdir:
        logger.debug("changing back into %s", curdir)
        os.chdir(curdir)

    return sp.returncode, output, error


def git_run_command(gitdir: Optional[str], args: List[str],
                    stdin: Optional[bytes] = None) -> Tuple[int, str]:
    cmdargs = ["git", "--no-pager"]
    if gitdir:
        if os.path.exists(os.path.join(gitdir, ".git")):
            gitdir = os.path.join(gitdir, ".git")
        cmdargs += ["--git-dir", gitdir]
    cmdargs += args

    ecode, out, err = _run_command(cmdargs, stdin=stdin)

    output = out.decode(errors="replace")

    if len(err.strip()):
        error = err.decode(errors="replace")
        logger.critical("Stderr: %s", error)
        output += error

    return ecode, output


def parse_config(file: str) -> Dict[str, Any]:
    parser = configparser.ConfigParser()
    parser.SECTCRE = re.compile(r"\[ *(?P<header>[^]]+?) *\]")
    parser.read([file])

    config: Dict[str, Any] = {}
    for name in parser.sections():
        m = re.match(r'(?P<name>\S+)\s+"(?P<subname>[^"]+)"', name)
        if not m:
            config[name] = dict(parser.items(name))
            continue

        section =  m.group("name")
        subname = m.group("subname")

        if section not in config:
            config[section] = {}

        config[section][subname] = dict(parser.items(name))

    return config


def read_config() -> Dict[str, Any] | Error:
    config = None

    for config_file in ["~/.jiramail", "~/.config/jiramail/config"]:
        config_file = os.path.expanduser(config_file)

        if not os.path.exists(config_file):
            continue

        logger.debug("picking config file `%s' ...", config_file)

        config = parse_config(config_file)
        break

    if not config:
        return Error("config file not found")

    logger.info("config has been read")
    return config


def setup_logger(logger: logging.Logger, level: int, fmt: str) -> logging.Logger:
    formatter = logging.Formatter(fmt=fmt, datefmt="%H:%M:%S")

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
