# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

import jira
import mailbox
import os
import os.path
import subprocess
import sys
import time
import tomllib

from typing import Optional, Tuple, Set, List, BinaryIO, Union, Sequence


__VERSION__ = '1'


class Error:
    def __init__(self, message):
        self.message = message


class Connection:
    def __init__(self, config_jira):
        self.config = config_jira

        verbose(2, f"connecting to JIRA ...")

        match self.config["auth"]:
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
                raise KeyError(f"Unknown method: jira.auth: " + self.config.get("auth", "<missing>"))

        verbose(1, "connected to JIRA")

        self._fields_by_name = {}

    def field_by_name(self, name: str, default: Optional[dict] = None):
        if not self._fields_by_name:
            for v in self.jira.fields():
                self._fields_by_name[v["name"].lower()] = v

        return self._fields_by_name.get(name, default)


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

    def get_message(self, key):
        return self.mbox.get_message(key)

    def update_message(self, key, mail):
        self.mbox.update([(key, mail)])

    def append(self, mail):
        msg_id = mail.get("Message-Id")

        if msg_id not in self.msgid:
            self.mbox.add(mail)
            self.msgid[msg_id] = True

    def iterkeys(self):
        return self.mbox.iterkeys()

    def close(self):
        self.mbox.close()


verbosity: int = 0


def verbose(level: int, text: str):
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


def read_config():
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
        raise Exception("config file not found")

    verbose(1, "config has been read")
    return config
