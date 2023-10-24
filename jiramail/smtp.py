#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import email
import email.message
import re
import socket

from typing import Tuple, Dict, List, Any

import jiramail
import jiramail.auth as auth
import jiramail.change

logger = jiramail.logger


class SMTPAnswer:
    def __init__(self, message: str):
        self.message = message


def parse_line(line: str) -> Tuple[str, str]:
    verb = ""
    args = ""
    if " " in line:
        (verb, args) = line.split(" ", 1)
    else:
        verb = line.strip()
    return (verb.upper(), args.strip())


def send(conn: socket.socket, msg: str) -> None:
    logger.debug("SEND: %s", msg.encode())
    conn.sendall(msg.encode())


def recv_line(state: Dict[str, Any]) -> Any:
    line = state["reader"].readline()
    logger.debug("RECV: %s", line.encode())
    return line


def reset(state: Dict[str, Any]) -> None:
    state["from"] = ""
    state["to"] = []
    state["auth"] = False
    state["authorized"] = False


def command_helo(state: Dict[str, Any], args: str) -> SMTPAnswer:
    state["remote"] = args

    # RFC 2821 section 4.1.4 specifies that EHLO has the same effect as RSET,
    # so reset for HELO too.
    reset(state)

    return SMTPAnswer(f"250 jiramail greets {state['addr'][0]}\r\n")


# pylint: disable-next=unused-argument
def command_quit(state: Dict[str, Any], args: str) -> SMTPAnswer:
    state["quit"] = True
    reset(state)

    return SMTPAnswer("221 2.0.0 ESMTP Service closing transmission channel\r\n")


def command_ehlo(state: Dict[str, Any], args: str) -> SMTPAnswer:
    state["remote"] = args

    ans = [f"250-{state['saddr'][0]} greets {state['addr'][0]}\r\n"]

    # RFC 1870 specifies that "SIZE 0" indicates no maximum size is in force.
    ans.append(f"250-SIZE {state['max_size']}\r\n")

    if "user" in state and "password" in state:
        ans.append("250-AUTH CRAM-MD5\r\n")

    ans.append("250 ENHANCEDSTATUSCODES\r\n")

    # RFC 2821 section 4.1.4 specifies that EHLO has the same effect as RSET.
    reset(state)

    return SMTPAnswer("".join(ans))


def auth_interact(state: Dict[str, Any], shared: str) -> Any:
    send(state["conn"], f"334 {shared}\r\n")
    return recv_line(state)


def command_auth(state: Dict[str, Any], args: str) -> SMTPAnswer:
    # Handle case where AUTH is called more than once (in violation of RFC 4954).
    if state.get("auth", False) is True:
        return SMTPAnswer("503 Bad sequence of commands (AUTH already specified for this session)\r\n")

    (auth_type, _) = parse_line(args)

    if not auth_type:
        return SMTPAnswer("501 Malformed auth input (argument required)\r\n")

    # RFC 4945 is very strict about the use of unprotected Userids/Passwords during
    # the SMTP Auth dialoge:
    # If an implementation supports SASL mechanisms that are vulnerable to passive
    # eavesdropping attacks (such as [PLAIN]), then the implementation MUST support
    # at least one configuration where these SASL mechanisms are not advertised or
    # used without the presence of an external security layer such as [TLS].
    match auth_type:
        case "CRAM-MD5":
            (state["authorized"], msg) = auth.cram_md5(state["user"], state["password"], auth_interact, state)
            if not state["authorized"]:
                return SMTPAnswer(f"535 {msg}\r\n")
            ans = SMTPAnswer("235 2.7.0 Authentication successful\r\n")
        case _:
            return SMTPAnswer("504 5.5.2 Unrecognized authentication type\r\n")

    if state["authorized"]:
        state["auth"] = True

    return ans


def command_mail(state: Dict[str, Any], args: str) -> SMTPAnswer:
    if "user" in state and not state["authorized"]:
        return SMTPAnswer("530 Authentication required\r\n")

    m = re.match(r'From:<(.+)>(\s(.*))?', args, re.I)
    if not m:
        return SMTPAnswer("501 5.5.4 Syntax error in parameters or arguments (invalid FROM parameter)\r\n")

    if m.group(2):
        # Validate the SIZE parameter if one was sent.
        szm = re.match(r'Size=(\d+)', m.group(3), re.I)
        if not szm:
            return SMTPAnswer("501 5.5.4 Syntax error in parameters or arguments (invalid SIZE parameter)\r\n")

        size = int(szm.group(1))

        # Enforce the maximum message size if one is set.
        if state["max_size"] > 0 and size > state["max_size"]:
            return SMTPAnswer(f"552 5.3.4 Requested mail action aborted: exceeded storage allocation ({state['max_size']})\r\n")

    state["from"] = m.group(1)
    state["to"] = []

    return SMTPAnswer("250 2.1.5 Ok\r\n")


def command_rcpt(state: Dict[str, Any], args: str) -> SMTPAnswer:
    if "user" in state and not state["authorized"]:
        return SMTPAnswer("530 Authentication required\r\n")

    if len(state["from"]) == 0:
        return SMTPAnswer("503 5.5.1 Bad senuence of commands (MAIL required before RCPT)\r\n")

    m = re.match(r'To:<(.+)>', args, re.I)
    if not m:
        return SMTPAnswer("501 5.5.4 Syntax error in parameters or arguments (invalid TO parameter)\r\n")

    # RFC 5321 specifies 100 minimum recipients
    if len(state["to"]) == 100:
        return SMTPAnswer("452 4.5.3 Too many recipients\r\n")

    state["to"].append(m.group(1))
    return SMTPAnswer("250 2.1.5 Ok\r\n")


def command_data(state: Dict[str, Any]) -> SMTPAnswer:
    if "user" in state and not state["authorized"]:
        return SMTPAnswer("530 Authentication required\r\n")

    if len(state["from"]) == 0 or len(state["to"]) == 0:
        return SMTPAnswer("503 5.5.1 Bad sequence of commands (MAIL & RCPT required before DATA)\r\n")

    send(state["conn"], "354 Start mail input; end with <CR><LF>.<CR><LF>\r\n")

    data = []
    size = 0

    while True:
        line = recv_line(state)

        if line == ".\r\n":
            break

        # Remove leading period (RFC 5321 section 4.5.2)
        if line.startswith("."):
            line = line[1:]

        if state["max_size"] > 0 and (size + len(line)) > state["max_size"]:
            return SMTPAnswer(f"552 5.3.4 Renuested mail action aborted: exceeded storage allocation ({state['max_size']})\r\n")

        data.append(line)
        size += len(line)

    mail = email.message_from_string("".join(data))
    reset(state)

    replies: List[email.message.EmailMessage] = []

    if not jiramail.change.process_mail(mail, replies):
        logger.critical("error: mail processing failed")
        return SMTPAnswer("451 4.3.0 Requested action aborted: local error in processing\r\n")

    if "mbox" in state:
        for reply in replies:
            state["mbox"].append(reply)

    return SMTPAnswer("250 2.0.0 Ok: processed\r\n")


def connection(state: Dict[str, Any]) -> None:
    logger.info("new connection")

    reset(state)
    state["remote"] = ""
    state["quit"] = False

    send(state["conn"], f"220 {state['saddr'][0]} ESMTP Service Ready\r\n")

    while not state["quit"]:
        line = recv_line(state)
        (cmd, args) = parse_line(line)

        logger.info("Got command `%s` with arguments `%s`", cmd, args)

        match cmd:
            case "HELO":
                ret = command_helo(state, args)
            case "EHLO":
                ret = command_ehlo(state, args)
            case "RSET":
                reset(state)
                ret = SMTPAnswer("250 2.0.0 Ok\r\n")
            case "QUIT":
                ret = command_quit(state, args)
            case "NOOP":
                ret = SMTPAnswer("250 2.0.0 Ok\r\n")
            case "HELP" | "VRFY" | "EXPN" | "STARTTLS":
                # See RFC 5321 section 4.2.4 for usage of 500 & 502 reply codes
                ret = SMTPAnswer("502 5.5.1 Command not implemented\r\n")
            case "AUTH":
                ret = command_auth(state, args)
            # RFC 5321 4.5.4.1: That is, the SMTP client SHOULD use the command
            # sequence: MAIL, RCPT, RCPT, ..., RCPT, DATA
            case "MAIL":
                ret = command_mail(state, args)
            case "RCPT":
                ret = command_rcpt(state, args)
            case "DATA":
                ret = command_data(state)
            case _:
                # See RFC 5321 section 4.2.4 for usage of 500 & 502 reply codes
                ret = SMTPAnswer("502 5.5.2 Error: command not recognized\r\n")

        send(state["conn"], ret.message)


def main(cmdargs: argparse.Namespace) -> int:
    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        logger.critical("%s", config.message)
        return jiramail.EX_FAILURE

    jiramail.change.logger = logger
    jiramail.change.dry_run = cmdargs.dry_run
    jiramail.change.no_reply = cmdargs.mailbox == ""

    state: Dict[str, Any] = {
        "port": 10025,
        "max_size": 0,
    }

    if cmdargs.mailbox != "":
        try:
            state["mbox"] = jiramail.Mailbox(cmdargs.mailbox)
        except Exception as e:
            logger.critical("unable to open mailbox: %s", e)
            return jiramail.EX_FAILURE

    if "smtp" in config:
        for param in ("user", "password", "port", "max_size"):
            if param in config["smtp"]:
                state[param] = config["smtp"][param]

    state["saddr"] = ("localhost", state["port"])

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(state["saddr"])
    sock.listen(0)

    logger.info("listening on %s", state["saddr"])

    try:
        jiramail.jserv = jiramail.Connection(config.get("jira", {}))
    except Exception as e:
        logger.critical("unable to connect to jira: %s", e)
        return jiramail.EX_FAILURE

    try:
        while True:
            logger.info("waiting for a connection")
            (conn, addr) = sock.accept()

            with conn:
                state["addr"] = addr
                state["conn"] = conn
                state["reader"] = conn.makefile(newline="\n")

                try:
                    connection(state)
                except BrokenPipeError:
                    pass

            if cmdargs.one_message:
                break
    except KeyboardInterrupt:
        pass

    if "mbox" in state:
        state["mbox"].close()

    return jiramail.EX_SUCCESS
