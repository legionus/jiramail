# _imaplex_tab.py. This file automatically created by PLY (version 3.11). Don't edit!
_tabversion   = '3.10'
_lextokens    = set(('AUTHENTICATE', 'BSLASH', 'CAPABILITY', 'CHECK', 'CLOSE', 'COLON', 'COMMA', 'COPY', 'CREATE', 'DELETE', 'DOT', 'EOL', 'EXAMINE', 'EXPUNGE', 'FETCH', 'GTSIGN', 'LIST', 'LOGIN', 'LOGOUT', 'LPAREN', 'LSBRACKET', 'LSUB', 'LTSIGN', 'MAILBOX', 'MINUS', 'NOOP', 'NUMBER', 'PLUS', 'QUOTED', 'RENAME', 'RPAREN', 'RSBRACKET', 'SELECT', 'SP', 'STAR', 'STATUS', 'STORE', 'SUBSCRIBE', 'UID', 'UNSUBSCRIBE', 'WORD'))
_lexreflags   = 2
_lexliterals  = ''
_lexstateinfo = {'INITIAL': 'inclusive', 'paren': 'inclusive', 'bracket': 'inclusive', 'sign': 'inclusive'}
_lexstatere   = {'INITIAL': [('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_INITIAL_EOL>\\s*\\r?\\n)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'EOL'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')])], 'paren': [('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')]), ('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_INITIAL_EOL>\\s*\\r?\\n)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'EOL'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')])], 'bracket': [('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')]), ('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_INITIAL_EOL>\\s*\\r?\\n)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'EOL'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')])], 'sign': [('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')]), ('(?P<t_ANY_NUMBER>\\d+)|(?P<t_ANY_WORD>[0-9a-z?#%~_.-]+)|(?P<t_ANY_LPAREN>\\()|(?P<t_ANY_RPAREN>\\))|(?P<t_ANY_LSBRACKET>\\[)|(?P<t_ANY_RSBRACKET>\\])|(?P<t_ANY_LTSIGN>\\<)|(?P<t_ANY_GTSIGN>\\>)|(?P<t_INITIAL_EOL>\\s*\\r?\\n)|(?P<t_ANY_QUOTED>"[^"]*")|(?P<t_ANY_BSLASH>\\\\)|(?P<t_ANY_DOT>\\.)|(?P<t_ANY_MINUS>\\-)|(?P<t_ANY_PLUS>\\+)|(?P<t_ANY_SP>\\ )|(?P<t_ANY_STAR>\\*)|(?P<t_ANY_COLON>:)|(?P<t_ANY_COMMA>,)', [None, ('t_ANY_NUMBER', 'NUMBER'), ('t_ANY_WORD', 'WORD'), ('t_ANY_LPAREN', 'LPAREN'), ('t_ANY_RPAREN', 'RPAREN'), ('t_ANY_LSBRACKET', 'LSBRACKET'), ('t_ANY_RSBRACKET', 'RSBRACKET'), ('t_ANY_LTSIGN', 'LTSIGN'), ('t_ANY_GTSIGN', 'GTSIGN'), (None, 'EOL'), (None, 'QUOTED'), (None, 'BSLASH'), (None, 'DOT'), (None, 'MINUS'), (None, 'PLUS'), (None, 'SP'), (None, 'STAR'), (None, 'COLON'), (None, 'COMMA')])]}
_lexstateignore = {'INITIAL': '', 'paren': '', 'bracket': '', 'sign': ''}
_lexstateerrorf = {'INITIAL': 't_error', 'paren': 't_error', 'bracket': 't_error', 'sign': 't_error'}
_lexstateeoff = {}