# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

import email
import mailbox
import os
import os.path
import subprocess
import sys
import time
import tomllib

from typing import Optional, Dict, Tuple, List, Union, Any
from collections.abc import Iterator

import jira


__VERSION__ = '1'

EX_SUCCESS = 0 # Successful exit status.
EX_FAILURE = 1 # Failing exit status.


class Error:
    def __init__(self, message: str):
        self.message = message


class Connection:
    def __init__(self, config_jira: Dict[str, Any]):
        verbose(2, "connecting to JIRA ...")

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

        verbose(1, "connected to JIRA")

        self._fields_by_name: Dict[str, Any] = {}

    def field_by_name(self, name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._fields_by_name:
            for v in self.jira.fields():
                if "clauseNames" in v:
                    for n in v["clauseNames"]:
                        self._fields_by_name[n.lower()] = v
                self._fields_by_name[v["name"].lower()] = v

        return self._fields_by_name.get(name, default)


class Mailbox:
    def __init__(self, path: str):
        verbose(2, f"openning the mailbox {path} ...")

        self.mbox = mailbox.mbox(path)
        self.msgid = {}

        for key in self.mbox.iterkeys():
            mail = self.mbox.get_message(key)
            if "Message-Id" in mail:
                msg_id = mail.get("Message-Id")
                self.msgid[msg_id] = True

        verbose(1, "mailbox is ready")

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


verbosity: int = 0


def verbose(level: int, text: str) -> None:
    if verbosity >= level:
        print(time.strftime("[%H:%M:%S]"), f"level={level}", text,
              file=sys.stderr, flush=True)


def _run_command(cmdargs: List[str], stdin: Optional[bytes] = None,
                 rundir: Optional[str] = None) -> Tuple[int, bytes, bytes]:
    if rundir:
        verbose(2, f"changing dir to {rundir}")
        curdir = os.getcwd()
        os.chdir(rundir)
    else:
        curdir = None

    verbose(2, f"running {cmdargs}")
    sp = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, error) = sp.communicate(input=stdin)
    if curdir:
        verbose(2, f"changing back into {curdir}")
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
        verbose(0, f"Stderr: {error}")
        output += error

    return ecode, output


def read_config() -> Dict[str, Any] | Error:
    config = None

    for config_file in ["~/.jiramail", "~/.config/jiramail/config"]:
        config_file = os.path.expanduser(config_file)

        if not os.path.exists(config_file):
            continue

        verbose(2, f"picking config file `{config_file}' ...")

        with open(config_file, "rb") as fd:
            config = tomllib.load(fd)
            break

    if not config:
        return Error("config file not found")

    verbose(1, "config has been read")
    return config
