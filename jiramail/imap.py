#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2023  Alexey Gladkov <gladkov.alexey@gmail.com>

__author__ = 'Alexey Gladkov <gladkov.alexey@gmail.com>'

import argparse
import email.policy
import mailbox
import os
import os.path
import re
import socket
import socketserver

from typing import Generator, Callable, Optional, Pattern, Dict, List, Set, Any

import jiramail
import jiramail.auth as auth
import jiramail.imap_proto.parser as imap_proto
import jiramail.mbox
import jiramail.subs

CRLF = '\r\n'
imap_policy = email.policy.default.clone(linesep=CRLF)

logger = jiramail.logger


class ImapResponse:
    def __init__(self, tag: str, status: str, message: str):
        self.tag = tag
        self.status = status
        self.message = message

    def __str__(self) -> str:
        parts = []

        if self.tag:
            parts.extend([self.tag, " "])

        if self.status:
            parts.extend([self.status, " "])

        parts.append(self.message)
        parts.append(CRLF)

        return "".join(parts)


class Context(Dict[str, Any]):
    def send(self, ans: ImapResponse) -> None:
        msg = str(ans)
        logger.debug("SEND: %s: %s", self["addr"], msg.encode())
        self["wfile"].write(msg.encode())

    def recv_line(self) -> Any:
        line = self["rfile"].readline()
        logger.debug("RECV: %s: %s", self["addr"], line)
        return line.decode()

    def send_result(self, message: str) -> None:
        self.send(ImapResponse("*", "", message))

    def resp_ok(self, message: str) -> ImapResponse:
        return ImapResponse(self["tag"], "OK", message)

    def resp_no(self, message: str) -> ImapResponse:
        return ImapResponse(self["tag"], "NO", message)

    def resp_bad(self, message: str) -> ImapResponse:
        return ImapResponse(self["tag"], "BAD", message)


class CommonResponse:
    def __init__(self, name: str, data: Any):
        self.name = name
        self.data = data

    def __str__(self) -> str:
        return f"{self.name} {self.data}"


class NumberResponse(CommonResponse):
    pass


class StringResponse(CommonResponse):
    def __str__(self) -> str:
        s = [self.name, " "]
        if "\n" in self.data:
            s.extend(['{', str(len(self.data)), '}', CRLF, self.data])
        else:
            s.extend(['"', re.sub(r'([\\"])',r'\\\1', self.data), '"'])
        return "".join(s)


class ListResponse(CommonResponse):
    def __str__(self) -> str:
        s = []
        if self.name:
            s.extend([self.name, " "])
        s.append('(')
        for i,v in enumerate(self.data):
            if i:
                s.extend([" ", str(v)])
            else:
                s.append(str(v))
        s.append(')')
        return "".join(s)

    def append(self, val: Any) -> None:
        self.data.append(val)


class MailFlags(Set[str]):
    # https://datatracker.ietf.org/doc/html/rfc3501#section-2.3.2
    @staticmethod
    def supported() -> List[str]:
        return ["Seen", "Deleted", "Flagged", "Answered", "Recent"]

    def __init__(self, data: str):
        self |= set(["Recent"])
        for char in data.upper():
            if   char == "R": self |= set(["Seen"])     # pylint: disable=multiple-statements
            elif char == "D": self |= set(["Deleted"])  # pylint: disable=multiple-statements
            elif char == "F": self |= set(["Flagged"])  # pylint: disable=multiple-statements
            elif char == "A": self |= set(["Answered"]) # pylint: disable=multiple-statements
            elif char == "O": self -= set(["Recent"])   # pylint: disable=multiple-statements

    def __str__(self) -> str:
        s = []
        if "Seen"       in self: s.append("R") # pylint: disable=multiple-statements
        if "Deleted"    in self: s.append("D") # pylint: disable=multiple-statements
        if "Flagged"    in self: s.append("F") # pylint: disable=multiple-statements
        if "Answered"   in self: s.append("A") # pylint: disable=multiple-statements
        if "Recent" not in self: s.append("O") # pylint: disable=multiple-statements
        return "".join(s)

    def set(self, other: List[str]) -> None:
        self &= set()
        self |= set(other)


def reset(ctx: Context) -> None:
    if "mbox" in ctx:
        ctx["mbox"].close()
        del ctx["mbox"]

    ctx["from"] = ""
    ctx["to"] = []
    ctx["authorized"] = False
    ctx["subscribed"] = set()
    ctx["deleted"] = set()
    ctx["select"] = ""
    ctx["tag"] = ""


def authorized(ctx: Context) -> bool:
    if "user" in ctx and "password" in ctx:
        return ctx["authorized"] is True
    return True


def wildcard2re(wildcard: str, delim: Optional[str] = None) -> Pattern[str]:
    wildcard = wildcard.replace("*", "(?:.*?)")
    if delim is None:
        wildcard = wildcard.replace("%", "(?:.*?)")
    else:
        wildcard = wildcard.replace("%", "(?:(?:[^{re.escape(delim)}])*?)")
    return re.compile(wildcard, re.I)


def sequence(node: imap_proto.Node, maxnum: int) -> Generator[int, None, None]:
    for seq in node["value"]:
        if seq["value"]["begin"] == '*':
            seq["value"]["begin"] = maxnum

        if seq["value"]["end"] == '*':
            seq["value"]["end"] = maxnum

        if seq["value"]["begin"] < seq["value"]["end"]:
            it = range(seq["value"]["begin"], seq["value"]["end"]+1)
        elif seq["value"]["begin"] > seq["value"]["end"]:
            it = range(seq["value"]["end"], seq["value"]["begin"]+1)
        else:
            it = range(seq["value"]["end"], seq["value"]["begin"]+1)

        for i in it:
            yield i


def get_mail_headers(mail: mailbox.mboxMessage,
                     filter_only: List[str],
                     filter_not: List[str]) -> str:
    ans: List[str] = []
    for header in mail.keys():
        if filter_only and header.upper() not in filter_only:
            continue
        if filter_not and header.upper() in filter_not:
            continue
        ans += [header, ": "] + mail.get_all(header, failobj=[]) + ["\n"]

    ret = "".join(ans)

    return re.sub(r'\n', CRLF, ret)


def get_mail_body(mail: mailbox.mboxMessage, only_part: int=0) -> str:
    if mail.is_multipart():
        arr = []
        i = 0
        for part in mail.get_payload():
            i += 1
            if only_part and i != only_part:
                continue
            arr.append(part.as_string())
        return CRLF.join(arr)
    else:
        return str(mail.get_payload())


def get_mail_full(mail: mailbox.mboxMessage) -> str:
    return mail.as_string(policy=imap_policy)


def send_fetch_resp(ctx: Context,
                    seqs: imap_proto.Node,
                    attrs: imap_proto.Node) -> None:
    for key in sequence(seqs, ctx["mbox"].n_msgs):
        index = key - 1
        mail = ctx["mbox"].get_message(index)

        fields = set()
        resp: CommonResponse

        ans = ListResponse(f"{key} FETCH", [])

        for attr in attrs["value"]:
            if attr["name"] == "attr":
                name = attr["value"].upper()

                match name:
                    case "UID":
                        # A number expressing the unique identifier of the message.
                        resp = NumberResponse(name, key)
                    case "FLAGS":
                        # A parenthesized list of flags that are set for this
                        # message.
                        resp = ListResponse(name, [f"\\{x}" for x in MailFlags(mail.get_flags())])
                    case "INTERNALDATE":
                        # A string representing the internal date of the message.
                        continue
                    case "ENVELOPE":
                        # A parenthesized list that describes the envelope structure
                        # of a message.
                        continue
                    case "BODY" | "BODYSTRUCTURE":
                        # The [MIME-IMB] body structure of the message.
                        continue
                    case "RFC822":
                        # Equivalent to BODY[].
                        resp = StringResponse(name, get_mail_full(mail))
                    case "RFC822.HEADER":
                        # Equivalent to BODY[HEADER].
                        resp = StringResponse(name, get_mail_headers(mail, [], []))
                    case "RFC822.TEXT":
                        # Equivalent to BODY[TEXT].
                        resp = StringResponse(name, get_mail_body(mail))
                    case "RFC822.SIZE":
                        # A number expressing the [RFC-2822] size of the message.
                        resp = NumberResponse(name, len(get_mail_full(mail)))

                if name not in fields:
                    ans.append(resp)
                    fields |= set([name])

            if attr["name"] in ("body", "body.peek"):
                val = attr["value"]["section"]

                match val["name"]:
                    case "header":
                        name = "BODY[HEADER]"
                        resp = StringResponse(name, get_mail_headers(mail, [], []))
                    case "header.fields":
                        name = "BODY[HEADER]"
                        resp = StringResponse(name, get_mail_headers(mail, val["value"], []))
                    case "header.fields.not":
                        name = "BODY[HEADER]"
                        resp = StringResponse(name, get_mail_headers(mail, [], val["value"]))
                    case "text":
                        name = "BODY[TEXT]"
                        resp = StringResponse(name, get_mail_body(mail))
                    case "_full":
                        name = "BODY[]"
                        resp = StringResponse(name, get_mail_full(mail))

                if name not in fields:
                    ans.append(resp)
                    fields |= set([name])

        ctx.send_result(str(ans))


def send_store_resp(ctx: Context, seqs: imap_proto.Node, data: imap_proto.Node) -> None:
    if data["value"]["item"] not in ("FLAGS", "FLAGS.SILENT"):
        return

    for seq in sequence(seqs, ctx["mbox"].n_msgs):
        index = seq - 1
        mail = ctx["mbox"].get_message(index)

        flags = MailFlags(mail.get_flags())

        match data["value"]["op"]:
            case "add":
                flags |= set([x["value"] for x in data["value"]["flags"]["value"]])
            case "remove":
                flags -= set([x["value"] for x in data["value"]["flags"]["value"]])
            case "replace":
                flags.set([x["value"] for x in data["value"]["flags"]["value"]])

        if "Deleted" in flags:
            ctx["deleted"] |= set([index])
        elif seq in ctx["deleted"]:
            ctx["deleted"] -= set([index])

        mail.set_flags(str(flags))
        ctx["mbox"].update_message(index, mail)

        if data["value"]["item"] == "FLAGS":
            resp = ListResponse(f"{seq} STORE", [])
            resp.append(NumberResponse("UID", seq))
            resp.append(ListResponse("FLAGS", [ f"\\{x}" for x in flags ]))
            ctx.send_result(str(resp))


def get_mbox_stats(mbox: jiramail.Mailbox) -> Dict[str,int]:
    ret = {
            "uid_valid": int(os.path.getmtime(mbox.path)),
            "uid_next": 0,
            "msgs": 0,
            "recent": 0,
            }

    for seq in mbox.iterkeys():
        mail = mbox.get_message(seq)
        flags = MailFlags(mail.get_flags())
        if "Recent" in flags:
            ret["recent"] += 1
        ret["msgs"] += 1
        ret["uid_next"] = seq

    ret["uid_next"] += 1

    return ret


def send_examine_resp(ctx: Context, mbox: jiramail.Mailbox) -> None:
    flags_supported = " ".join([f"\\{x}" for x in MailFlags.supported()])
    stats = get_mbox_stats(mbox)

    ctx.send_result(f"FLAGS ({flags_supported})")
    ctx.send_result(f"OK [PERMANENTFLAGS ({flags_supported})] Limited")
    ctx.send_result(f"OK [UIDVALIDITY {stats['uid_valid']}] UIDs valid")
    ctx.send_result(f"OK [UIDNEXT {stats['uid_next']}] Predicted next UID")
    ctx.send_result(f"{stats['msgs']} EXISTS")
    ctx.send_result(f"{stats['recent']} RECENT")


def send_status_resp(ctx: Context,
                     mbox: jiramail.Mailbox,
                     mailbox: str,
                     items: List[str]) -> None:
    infos = get_mbox_stats(mbox)
    fields = {
            "MESSAGES"    : "msgs",
            "RECENT"      : "recent",
            "UIDNEXT"     : "uid_next",
            "UIDVALIDITY" : "uid_valid",
            "UNSEEN"      : "msgs",
            }
    resp = ListResponse(f"STATUS \"{mailbox}\"", [])

    for n in items:
        n = n.upper()

        if n in fields:
            resp.append(NumberResponse(n, infos[fields[n]]))

    ctx.send_result(str(resp))


def send_list_resp(ctx: Context, cmdname: str, mailbox: str, items: List[str]) -> bool:
    wildcard = None
    found = False

    if mailbox:
        wildcard = wildcard2re(mailbox, "/")

    # RFC-5258: Internet Message Access Protocol version 4 - LIST Command Extensions
    # RFC-6154: IMAP LIST Extension for Special-Use Mailboxes

    if not wildcard or wildcard.match(""):
        ctx.send_result(f'{cmdname} (\\Noselect \\HasChildren) "/" ""')
        found = True

    for name in items:
        if not wildcard or wildcard.match(name):
            folder_flags = ["\\Marked", "\\HasNoChildren"]
            ctx.send_result(f'{cmdname} ({" ".join(folder_flags)}) "/" "{name}"')
            found = True

    return found


def command__always_fail(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    return ctx.resp_no(f"{cmd['name']} failed")


def command_noop(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    return ctx.resp_ok(f"{cmd['name']} completed")


def command_capability(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    caps = ["CAPABILITY", "IMAP4rev1"] # "LOGINDISABLED"

    if not ctx["authorized"] and "user" in ctx and "password" in ctx:
        caps.extend(["AUTH=CRAM-MD5", "AUTH=PLAIN"])

    ctx.send_result(" ".join(caps))
    return ctx.resp_ok(f"{cmd['name']} completed")


def auth_interact(ctx: Context, shared: str) -> Any:
    ctx.send(ImapResponse("+", "", shared))
    return ctx.recv_line()


def command_authenticate(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["authorized"] = False

    if cmd["value"] not in ("CRAM-MD5"):
        return ctx.resp_no("unsupported authentication mechanism")

    (ret, msg) = auth.cram_md5(ctx["user"], ctx["password"], auth_interact, ctx)
    if not ret:
        return ctx.resp_no(msg)

    ctx["authorized"] = True
    return ctx.resp_ok("CRAM-MD5 authentication successful")


def command_login(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["authorized"] = False
    user_ok = ctx["user"]     == cmd["value"]["username"]
    pass_ok = ctx["password"] == cmd["value"]["password"]

    if user_ok and pass_ok:
        ctx["authorized"] = True
        return ctx.resp_ok("LOGIN authentication successful")

    return ctx.resp_no(f"{cmd['name']} user name or password rejected")


def command_logout(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["quit"] = True
    ctx.send_result("BYE IMAP4rev1 Server logging out")
    return ctx.resp_ok(f"{cmd['name']} completed")


def command_list(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    found = send_list_resp(ctx, cmd["name"],
                           cmd["value"]["mailbox"],
                           ctx["config"]["sub"].keys())
    if not found:
        return ctx.resp_no(f"{cmd['name']} nothing found")

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_lsub(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    found = send_list_resp(ctx, cmd["name"],
                           cmd["value"]["mailbox"],
                           ctx["subscribed"])
    if not found:
        return ctx.resp_no(f"{cmd['name']} nothing found")

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_subscribe(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["subscribed"] |= set([cmd["value"]["mailbox"]])
    return ctx.resp_ok(f"{cmd['name']} completed")


def command_unsubscribe(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["subscribed"] -= set([cmd["value"]["mailbox"]])
    return ctx.resp_ok(f"{cmd['name']} completed")


def command_status(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    mailbox = jiramail.subs.get_mailbox(ctx["config"], cmd["value"]["mailbox"])

    if not mailbox:
        return ctx.resp_no(f"{cmd['name']} no such mailbox")

    try:
        mbox = jiramail.Mailbox(mailbox)
    except Exception as e:
        err = f"unable to open mailbox: {e}"
        logger.critical(err)
        return ctx.resp_no(err)

    send_status_resp(ctx, mbox,
                     cmd["value"]["mailbox"],
                     cmd["value"]["items"]["value"])
    mbox.close()

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_examine(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    mailbox = jiramail.subs.get_mailbox(ctx["config"], cmd["value"]["mailbox"])

    if not mailbox:
        return ctx.resp_no(f"{cmd['name']} no such mailbox")

    try:
        mbox = jiramail.Mailbox(mailbox)
    except Exception as e:
        err = f"unable to open mailbox: {e}"
        logger.critical(err)
        return ctx.resp_no(err)

    send_examine_resp(ctx, mbox)
    mbox.close()

    return ctx.resp_ok(f"[READ-WRITE] {cmd['name']} completed")


def command_select(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    mailbox = jiramail.subs.get_mailbox(ctx["config"], cmd["value"]["mailbox"])

    if not mailbox:
        return ctx.resp_no(f"{cmd['name']} no such mailbox")

    if "mbox" in ctx:
        ctx["mbox"].close()

    try:
        ctx["mbox"] = jiramail.Mailbox(mailbox)
    except Exception as e:
        err = f"unable to open mailbox: {e}"
        logger.critical(err)
        return ctx.resp_no(err)

    #logger.info("Command SELECT: `%s` synchronization ...", cmd["value"]["mailbox"])

    #for query in jiramail.subs.get_queries(ctx["config"], cmd["value"]["mailbox"]):
    #    logger.debug("Command SELECT: processing query: %s", query)
    #    jiramail.mbox.process_query(query, ctx["mbox"])

    logger.info("Command SELECT: `%s` synchronization is complete.", cmd["value"]["mailbox"])
    ctx["select"] = cmd["value"]["mailbox"]
    ctx["deleted"] = set()

    send_examine_resp(ctx, ctx["mbox"])

    return ctx.resp_ok(f"[READ-WRITE] {cmd['name']} completed")


def command_close(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["select"] = ""

    if "mbox" in ctx:
        ctx["mbox"].close()
        del ctx["mbox"]

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_check(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    ctx["mbox"].sync()
    return ctx.resp_ok(f"{cmd['name']} completed")


def command_copy(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    return ctx.resp_no(f"{cmd['name']} failed")


def command_fetch(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    seqs = cmd["value"]["sequence"]
    attrs = cmd["value"]["attrs"]

    if len(attrs["value"]) > 0:
        send_fetch_resp(ctx, seqs, attrs)

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_uid_fetch(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    seqs = cmd["value"]["sequence"]
    attrs = cmd["value"]["attrs"]

    if len(attrs["value"]) > 0:
        send_fetch_resp(ctx, seqs, attrs)

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_uid_store(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    send_store_resp(ctx,
                    cmd["value"]["sequence"],
                    cmd["value"]["value"])

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_store(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    send_store_resp(ctx,
                    cmd["value"]["sequence"],
                    cmd["value"]["value"])

    return ctx.resp_ok(f"{cmd['name']} completed")


def command_expunge(ctx: Context, cmd: imap_proto.Node) -> ImapResponse:
    for seq in ctx["deleted"]:
        ctx["mbox"].del_message(seq)

    ctx["mbox"].sync()

    return ctx.resp_ok(f"{cmd['name']} completed")


class ImapCMD:
    handler: Callable[[Context, imap_proto.Node], ImapResponse]

    def __init__(self, handler: Callable[[Context, imap_proto.Node], ImapResponse], need_auth: bool, need_mailbox: bool):
        self.need_auth = need_auth
        self.need_mailbox = need_mailbox
        self.handler = handler


commands: Dict[str, ImapCMD] = {
        "AUTHENTICATE" : ImapCMD(command_authenticate ,  need_auth=False ,  need_mailbox=False ),
        "CAPABILITY"   : ImapCMD(command_capability   ,  need_auth=False ,  need_mailbox=False ),
        "CHECK"        : ImapCMD(command_check        ,  need_auth=False ,  need_mailbox=True  ),
        "CLOSE"        : ImapCMD(command_close        ,  need_auth=True  ,  need_mailbox=True  ),
        "COPY"         : ImapCMD(command_copy         ,  need_auth=True  ,  need_mailbox=True  ),
        "CREATE"       : ImapCMD(command__always_fail ,  need_auth=True  ,  need_mailbox=False ),
        "DELETE"       : ImapCMD(command__always_fail ,  need_auth=True  ,  need_mailbox=False ),
        "EXAMINE"      : ImapCMD(command_examine      ,  need_auth=True  ,  need_mailbox=False ),
        "EXPUNGE"      : ImapCMD(command_expunge      ,  need_auth=True  ,  need_mailbox=True  ),
        "FETCH"        : ImapCMD(command_fetch        ,  need_auth=True  ,  need_mailbox=True  ),
        "LIST"         : ImapCMD(command_list         ,  need_auth=True  ,  need_mailbox=False ),
        "LOGIN"        : ImapCMD(command_login        ,  need_auth=False ,  need_mailbox=False ),
        "LOGOUT"       : ImapCMD(command_logout       ,  need_auth=False ,  need_mailbox=False ),
        "LSUB"         : ImapCMD(command_lsub         ,  need_auth=True  ,  need_mailbox=False ),
        "NOOP"         : ImapCMD(command_noop         ,  need_auth=False ,  need_mailbox=False ),
        "RENAME"       : ImapCMD(command__always_fail ,  need_auth=True  ,  need_mailbox=False ),
        "SELECT"       : ImapCMD(command_select       ,  need_auth=True  ,  need_mailbox=False ),
        "STATUS"       : ImapCMD(command_status       ,  need_auth=True  ,  need_mailbox=False ),
        "STORE"        : ImapCMD(command_store        ,  need_auth=True  ,  need_mailbox=True  ),
        "SUBSCRIBE"    : ImapCMD(command_subscribe    ,  need_auth=True  ,  need_mailbox=False ),
        "UID FETCH"    : ImapCMD(command_uid_fetch    ,  need_auth=True  ,  need_mailbox=True  ),
        "UID STORE"    : ImapCMD(command_uid_store    ,  need_auth=True  ,  need_mailbox=True  ),
        "UNSUBSCRIBE"  : ImapCMD(command_unsubscribe  ,  need_auth=True  ,  need_mailbox=False ),
        }


class ImapTCPHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        config = getattr(self.server, "config")

        ctx = Context({
            "config" : config,
            "addr"   : self.client_address,
            "rfile"  : self.rfile,
            "wfile"  : self.wfile,
            "quit"   : False,
            })

        if "imap" in config:
            for param in ("user", "password"):
                if param in config["imap"]:
                    ctx[param] = config["imap"][param]

        reset(ctx)

        #try:
        #    jiramail.jserv = jiramail.Connection(config.get("jira", {}))
        #except Exception as e:
        #    logger.critical("unable to connect to jira: %s", e)
        #    return jiramail.EX_FAILURE

        parser = imap_proto.IMAPParser()

        try:
            logger.info("%s: new connection", ctx["addr"])

            ctx.send(ImapResponse("*", "OK", "IMAP4rev1 Service Ready"))

            while not ctx["quit"]:
                line = ctx.recv_line()

                if line == '':
                    break

                node = parser.parse(line)

                if not isinstance(node, imap_proto.Node):
                    logger.critical("parser failed: %s", node)
                    break

                ctx["tag"] = str(node["value"]["tag"])
                cmd = node["value"]["cmd"]

                if cmd["name"] in commands:
                    if commands[cmd["name"]].need_auth and not authorized(ctx):
                        resp = ctx.resp_no(f"{cmd['name']} Authentication required")
                    elif commands[cmd["name"]].need_mailbox and ctx["select"] == "":
                        resp = ctx.resp_no("mailbox not selected")
                    else:
                        resp = commands[cmd["name"]].handler(ctx, cmd)
                else:
                    resp = ctx.resp_ok("command not recognized")

                ctx.send(resp)

        except (BrokenPipeError, ConnectionResetError) as e:
            logger.debug("%s: connection error: %s", ctx["addr"], e)

        logger.debug("%s: finish", ctx["addr"])


class ImapServer(socketserver.ForkingTCPServer):
    config: Dict[str, Any]

    def __init__(self, addr: Any, handler: Any):
        self.address_family = socket.AF_INET
        self.socket_type = socket.SOCK_STREAM
        self.allow_reuse_address = True
        super().__init__(addr, handler)


# pylint: disable-next=unused-argument
def main(cmdargs: argparse.Namespace) -> int:
    config = jiramail.read_config()

    if isinstance(config, jiramail.Error):
        logger.critical("%s", config.message)
        return jiramail.EX_FAILURE

    jiramail.auth.logger = logger
    jiramail.mbox.logger = logger
    jiramail.subs.logger = logger

    saddr = ("localhost", config.get("imap", {}).get("port", 10143))

    with ImapServer(saddr, ImapTCPHandler) as server:
        server.config = config
        server.serve_forever()

    return jiramail.EX_SUCCESS
