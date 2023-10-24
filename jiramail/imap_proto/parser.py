#!/usr/bin/env python3

import re
import logging

from typing import Dict, Any

import ply.lex as lex   # type: ignore
import ply.yacc as yacc # type: ignore

from ply.lex import TOKEN

logger = logging.getLogger("imap_proto")
logger.setLevel(logging.DEBUG)


class Node(Dict[str, Any]):
    def __init__(self, name: str, value: Any):
        self["name"] = name
        self["value"] = value

class _ParserError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return f"Error: {self.message}"

class _LexError(_ParserError):
    pass

class _YaccError(_ParserError):
    pass


class Error(BaseException):
    def __init__(self, err: _ParserError):
        self.err = err

    def __str__(self) -> str:
        return str(self.err)


class IMAPParser:
    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        debuglog = None

        if "debug" in kwargs and kwargs["debug"]:
            debuglog = logger

        self.lex = lex.lex(reflags=re.IGNORECASE, module=self, errorlog=logger,
                           lextab="_imaplex_tab", optimize=True, **kwargs)

        self.yacc = yacc.yacc(start="command", module=self,
                              errorlog=logger, debuglog=debuglog,
                              tabmodule="_imapyacc_tab", optimize=True, **kwargs)


    commands = [
            "FETCH", "CAPABILITY", "CHECK", "CLOSE", "NOOP", "LOGOUT",
            "EXPUNGE", "SELECT", "LIST", "LOGIN", "UID", "STORE", "CREATE",
            "DELETE", "RENAME", "COPY", "EXAMINE", "STATUS", "SUBSCRIBE",
            "UNSUBSCRIBE", "LSUB", "AUTHENTICATE",
            ]

    tokens = [
            "SP", "EOL", "NUMBER", "WORD", "MAILBOX", "QUOTED",
            "COLON", "COMMA", "DOT", "STAR", "PLUS", "MINUS", "BSLASH",
            "LSBRACKET", "RSBRACKET", "LPAREN", "RPAREN", "LTSIGN", "GTSIGN",
            ] + commands

    t_INITIAL_EOL = r'\s*\r?\n'
    t_ANY_SP = r'\ '
    t_ANY_STAR = r'\*'
    t_ANY_COLON = r':'
    t_ANY_COMMA = r','
    t_ANY_DOT = r'\.'
    t_ANY_PLUS = r'\+'
    t_ANY_MINUS = r'\-'
    t_ANY_BSLASH = r'\\'
    t_ANY_QUOTED = r'"[^"]*"'

    states = (
            ('paren','inclusive'),
            ('bracket','inclusive'),
            ('sign','inclusive'),
            )

    @TOKEN(r'\d+') # type: ignore
    def t_ANY_NUMBER(self, t: lex.LexToken) -> lex.LexToken:
        try:
            t.value = int(t.value)
        except ValueError:
            print("Integer value to large %d", t.value)
            t.value = 0
        return t


    @TOKEN(r'[0-9a-z?#%~_.-]+') # type: ignore
    def t_ANY_WORD(self, t: lex.LexToken) -> lex.LexToken:
        if not t.lexer.lexstatestack:
            v = t.value.upper()
            if v in self.commands:
                t.type = v
                t.value = v
                return t

        if re.match(r'^[0-9a-z](?:[0-9a-z_.-]*[0-9a-z])?$', t.value, re.IGNORECASE):
            t.type = "WORD"
            return t

        t.type = "MAILBOX"
        return t


    @TOKEN(r'\(') # type: ignore
    def t_ANY_LPAREN(self, t: lex.LexToken) -> lex.LexToken:
        t.type = "LPAREN"
        t.lexer.push_state('paren')
        return t


    @TOKEN(r'\)') # type: ignore
    def t_ANY_RPAREN(self, t: lex.LexToken) -> lex.LexToken:
        t.type = "RPAREN"
        t.lexer.pop_state()
        return t


    @TOKEN(r'\[') # type: ignore
    def t_ANY_LSBRACKET(self, t: lex.LexToken) -> lex.LexToken:
        t.type = "LSBRACKET"
        t.lexer.push_state('bracket')
        return t


    @TOKEN(r'\]') # type: ignore
    def t_ANY_RSBRACKET(self, t: lex.LexToken) -> lex.LexToken:
        t.type = "RSBRACKET"
        t.lexer.pop_state()
        return t

    @TOKEN(r'\<') # type: ignore
    def t_ANY_LTSIGN(self, t: lex.LexToken) -> lex.LexToken:
        t.type = "LTSIGN"
        t.lexer.push_state('sign')
        return t


    @TOKEN(r'\>') # type: ignore
    def t_ANY_GTSIGN(self, t: lex.LexToken) -> lex.LexToken:
        t.type = "GTSIGN"
        t.lexer.pop_state()
        return t


    def t_error(self, t: lex.LexToken) -> None:
        t.lexer.skip(1)
        raise _LexError(f"illegal character '{t.value[0]}'")


    def rule_list(self, name: str, p: yacc.YaccProduction,
                  maxlen: int=4, recurpos: int=1,
                  startpos: int=1, appendpos: int=3) -> None:
        if len(p) == maxlen:
            p[recurpos]["value"].append(p[appendpos])
            p[0] = p[recurpos]
        else:
            p[0] = Node(name, [p[startpos]])


    def unquote(self, data: str) -> str:
        if data.startswith('"') and data.endswith('"'):
            return data[1:-1]
        return data


    def p_command(self, p: yacc.YaccProduction) -> None:
        '''
        command : tag SP cmd_noop EOL
                | tag SP cmd_authenticate EOL
                | tag SP cmd_capability EOL
                | tag SP cmd_check EOL
                | tag SP cmd_close EOL
                | tag SP cmd_copy EOL
                | tag SP cmd_create EOL
                | tag SP cmd_delete EOL
                | tag SP cmd_examine EOL
                | tag SP cmd_expunge EOL
                | tag SP cmd_fetch EOL
                | tag SP cmd_list EOL
                | tag SP cmd_login EOL
                | tag SP cmd_logout EOL
                | tag SP cmd_lsub EOL
                | tag SP cmd_rename EOL
                | tag SP cmd_select EOL
                | tag SP cmd_status EOL
                | tag SP cmd_store EOL
                | tag SP cmd_subscribe EOL
                | tag SP cmd_uid EOL
                | tag SP cmd_unsubscribe EOL
        '''
        p[0] = Node("command", {
            "tag": p[1],
            "cmd": p[3],
            })


    def p_tag(self, p: yacc.YaccProduction) -> None:
        '''
        tag : WORD
            | NUMBER
        '''
        p[0] = p[1]


    def p_cmd_COMMON_NOARGS(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_capability : CAPABILITY
        cmd_check      : CHECK
        cmd_close      : CLOSE
        cmd_expunge    : EXPUNGE
        cmd_logout     : LOGOUT
        cmd_noop       : NOOP
        '''
        p[0] = Node(p[1], {})


    def p_cmd_COMMON_MAILBOX_ARG(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_create      : CREATE SP mailbox
        cmd_delete      : DELETE SP mailbox
        cmd_select      : SELECT SP mailbox
        cmd_examine     : EXAMINE SP mailbox
        cmd_subscribe   : SUBSCRIBE SP mailbox
        cmd_unsubscribe : UNSUBSCRIBE SP mailbox
        '''
        p[0] = Node(p[1], {
            "mailbox": p[3],
            })


    def p_cmd_authenticate(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_authenticate : AUTHENTICATE SP WORD
        '''
        p[0] = Node(p[1], p[3])


    def p_cmd_login(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_login : LOGIN SP QUOTED SP QUOTED
        '''
        p[0] = Node(p[1], {
            "username": self.unquote(p[3]),
            "password": self.unquote(p[5]),
            })


    def p_cmd_list(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_list : LIST SP mailbox SP mailbox
        cmd_lsub : LSUB SP mailbox SP mailbox
        '''
        p[0] = Node(p[1], {
            "refname": p[3],
            "mailbox": p[5],
            })


    def p_cmd_rename(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_rename : RENAME SP mailbox SP mailbox
        '''
        p[0] = Node(p[1], {
            "mailbox_old": p[3],
            "mailbox_new": p[5],
            })


    def p_cmd_copy(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_copy : COPY SP sequence SP mailbox
        '''
        p[0] = Node(p[1], {
            "sequence": p[3],
            "mailbox": p[5],
            })


    def p_cmd_status(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_status  : STATUS SP mailbox SP LPAREN status-items RPAREN
        '''
        p[0] = Node(p[1], {
            "mailbox": p[3],
            "items": p[6],
            })


    def p_status_items(self, p: yacc.YaccProduction) -> None:
        '''
        status-items : status-items SP WORD
                     | WORD
        '''
        self.rule_list("status-items", p)


    def p_mailbox(self, p: yacc.YaccProduction) -> None:
        '''
        mailbox : QUOTED
                | MAILBOX
                | WORD
        '''
        p[0] = self.unquote(p[1])


    def p_cmd_uid(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_uid : UID SP FETCH SP sequence SP LPAREN fetch-attrs RPAREN
                | UID SP FETCH SP sequence SP fetch-attrs
                | UID SP STORE SP sequence SP store_args
        '''
        p[0] = Node(f"{p[1]} {p[3]}", { "name": p[3].lower() })

        match p[0]["value"]["name"]:
            case "fetch":
                p[0]["value"]["sequence"] = p[5]

                if len(p) == 8:
                    p[0]["value"]["attrs"] = p[7]
                elif len(p) == 10:
                    p[0]["value"]["attrs"] = p[8]
                p[0]["value"]["attrs"]["value"].insert(0, Node("attr", "UID"))

            case "store":
                p[0]["value"]["sequence"] = p[5]
                p[0]["value"]["value"] = p[7]


    def p_cmd_store(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_store : STORE SP sequence SP store_args
        '''
        p[0] = Node(p[1], {
            "sequence": p[3],
            "value": p[5],
            })


    def p_store_args(self, p: yacc.YaccProduction) -> None:
        '''
        store_args : PLUS  WORD SP LPAREN flag-list RPAREN
                   | MINUS WORD SP LPAREN flag-list RPAREN
                   | WORD SP LPAREN flag-list RPAREN
        '''
        p[0] = Node("store-args", {})
        p[0]["value"]["op"] = "replace"
        pos_word = 1

        if p[1] == "+":
            p[0]["value"]["op"] = "add"
            pos_word += 1
        elif p[1] == "-":
            p[0]["value"]["op"] = "remove"
            pos_word += 1

        if p[pos_word] not in ("FLAGS", "FLAGS.SILENT"):
            self.p_error(p.slice[pos_word])

        p[0]["value"]["item"] = p[pos_word].upper()
        p[0]["value"]["flags"] = p[pos_word+3]


    def p_flag_list(self, p: yacc.YaccProduction) -> None:
        '''
        flag-list : flag-value SP flag-value
                  | flag-value
        '''
        self.rule_list("flags", p)


    def p_flag_value(self, p: yacc.YaccProduction) -> None:
        '''
        flag-value : BSLASH WORD
                   | WORD
        '''
        if len(p) == 3:
            p[0] = Node("flag", p[2])
        else:
            p[0] = Node("flag", p[1])


    def p_cmd_fetch(self, p: yacc.YaccProduction) -> None:
        '''
        cmd_fetch : FETCH SP sequence SP LPAREN fetch-attrs RPAREN
                  | FETCH SP sequence SP WORD
        '''
        p[0] = Node(p[1], {})
        p[0]["value"]["sequence"] = p[3]

        if len(p) == 8:
            p[0]["value"]["attrs"] = p[6]
        else:
            vals = []
            match p[5]:
                case "FAST":
                    vals = [Node("attr", "FLAGS"),
                            Node("attr", "INTERNALDATE"),
                            Node("attr", "RFC822.SIZE")]
                case "ALL":
                    vals = [Node("attr", "FLAGS"),
                            Node("attr", "INTERNALDATE"),
                            Node("attr", "RFC822.SIZE"),
                            Node("attr", "ENVELOPE")]
                case "FULL":
                    vals = [Node("attr", "FLAGS"),
                            Node("attr", "INTERNALDATE"),
                            Node("attr", "RFC822.SIZE"),
                            Node("attr", "ENVELOPE"),
                            Node("attr", "BODY")]
            p[0]["value"]["attrs"] = vals


    def p_sequence(self, p: yacc.YaccProduction) -> None:
        '''
        sequence : sequence COMMA range
                 | range
        '''
        self.rule_list("sequence", p)


    def p_range(self, p: yacc.YaccProduction) -> None:
        '''
        range : NUMBER COLON NUMBER
              | NUMBER COLON STAR
              | NUMBER
        '''
        p[0] = Node("range", { "begin": p[1], "end": p[1] })
        if len(p) == 4:
            p[0]["value"]["end"] = p[3]


    def p_fetch_attrs(self, p: yacc.YaccProduction) -> None:
        '''
        fetch-attrs : fetch-attrs SP fetch-attr
                    | fetch-attr
        '''
        self.rule_list("attrs", p)


    def p_fetch_attr(self, p: yacc.YaccProduction) -> None:
        '''
        fetch-attr : WORD LSBRACKET NUMBER RSBRACKET fetch-partial
        fetch-attr : WORD LSBRACKET section RSBRACKET fetch-partial
                   | WORD
        '''
        if len(p) >= 5:
            if p[1].upper() not in ("BODY", "BODY.PEEK"):
                self.p_error(p.slice[1])

            p[0] = Node(p[1].lower(), {})

            if isinstance(p[3], int):
                p[0]["value"]["section"] = Node("part", p[3])
            else:
                p[0]["value"]["section"] = p[3]

            if len(p) == 6 and p[5]:
                p[0]["value"]["partial"] = p[5]
        else:
            v = p[1].upper()
            if v not in ("BODYSTRUCTURE", "ENVELOPE", "FLAGS", "INTERNALDATE", "RFC822.HEADER", "RFC822.SIZE", "RFC822.TEXT", "UID"):
                self.p_error(p.slice[1])

            p[0] = Node("attr", v)


    def p_fetch_partial(self, p: yacc.YaccProduction) -> None:
        '''
        fetch-partial : LTSIGN NUMBER DOT NUMBER GTSIGN
                      | LTSIGN NUMBER GTSIGN
                      | empty
        '''
        if len(p) == 6:
            p[0] = Node("partial", {"number": p[2], "size": p[4] })
        elif len(p) == 4:
            p[0] = Node("partial", {"number": p[2], "size": 2**64 })


    def p_section_spec(self, p: yacc.YaccProduction) -> None:
        '''
        section : WORD SP header-list
                | WORD
                | empty
        '''
        if len(p) > 1 and p[1]:
            p1 = p[1].upper()

            if p1 not in ("HEADER.FIELDS", "HEADER.FIELDS.NOT", "HEADER", "TEXT", "MIME"):
                self.p_error(p.slice[1])

            if len(p) == 4:
                p[0] = Node(p1.lower(), p[3])
            elif len(p) == 2:
                p[0] = Node(p1.lower(), p1)
        else:
            p[0] = Node("_full", [])


    def p_header_list(self, p: yacc.YaccProduction) -> None:
        '''
        header-list : LPAREN headers RPAREN
        '''
        p[0] = p[2]["value"] = [x.upper() for x in p[2]["value"]]


    def p_headers(self, p: yacc.YaccProduction) -> None:
        '''
        headers : headers SP WORD
                | WORD
        '''
        self.rule_list("headers", p)


    def p_empty(self, p: yacc.YaccProduction) -> None:
        '''
        empty :
        '''


    def p_error(self, p: lex.LexToken) -> None:
        if p:
            raise _YaccError(f"syntax error at token {p.type} (line={p.lineno}:{p.lexpos}): {p.value}")
        else:
            raise _YaccError("unexpected EOF")


    def tokenize(self, data: str) -> None:
        self.lex.input(data)
        while True:
            tok = self.lex.token()
            if not tok:
                break
            print(tok.type, tok.value, tok.lineno, tok.lexpos)


    def parse(self, data: str) -> Node | Error:
        try:
            node = self.yacc.parse(data)
        except _ParserError as e:
            return Error(e)
        if not isinstance(node, Node):
            return Error(_ParserError(f"unexpected parser result {node}"))
        return node
