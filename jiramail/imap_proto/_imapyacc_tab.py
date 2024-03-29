
# _imapyacc_tab.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'commandAUTHENTICATE BSLASH CAPABILITY CHECK CLOSE COLON COMMA COPY CREATE DELETE DOT EOL EXAMINE EXPUNGE FETCH GTSIGN LIST LOGIN LOGOUT LPAREN LSBRACKET LSUB LTSIGN MAILBOX MINUS NOOP NUMBER PLUS QUOTED RENAME RPAREN RSBRACKET SELECT SP STAR STATUS STORE SUBSCRIBE UID UNSUBSCRIBE WORD\n        command : tag SP cmd_noop EOL\n                | tag SP cmd_authenticate EOL\n                | tag SP cmd_capability EOL\n                | tag SP cmd_check EOL\n                | tag SP cmd_close EOL\n                | tag SP cmd_copy EOL\n                | tag SP cmd_create EOL\n                | tag SP cmd_delete EOL\n                | tag SP cmd_examine EOL\n                | tag SP cmd_expunge EOL\n                | tag SP cmd_fetch EOL\n                | tag SP cmd_list EOL\n                | tag SP cmd_login EOL\n                | tag SP cmd_logout EOL\n                | tag SP cmd_lsub EOL\n                | tag SP cmd_rename EOL\n                | tag SP cmd_select EOL\n                | tag SP cmd_status EOL\n                | tag SP cmd_store EOL\n                | tag SP cmd_subscribe EOL\n                | tag SP cmd_uid EOL\n                | tag SP cmd_unsubscribe EOL\n        \n        tag : WORD\n            | NUMBER\n        \n        cmd_capability : CAPABILITY\n        cmd_check      : CHECK\n        cmd_close      : CLOSE\n        cmd_expunge    : EXPUNGE\n        cmd_logout     : LOGOUT\n        cmd_noop       : NOOP\n        \n        cmd_create      : CREATE SP mailbox\n        cmd_delete      : DELETE SP mailbox\n        cmd_select      : SELECT SP mailbox\n        cmd_examine     : EXAMINE SP mailbox\n        cmd_subscribe   : SUBSCRIBE SP mailbox\n        cmd_unsubscribe : UNSUBSCRIBE SP mailbox\n        \n        cmd_authenticate : AUTHENTICATE SP WORD\n        \n        cmd_login : LOGIN SP QUOTED SP QUOTED\n        \n        cmd_list : LIST SP mailbox SP mailbox\n        cmd_lsub : LSUB SP mailbox SP mailbox\n        \n        cmd_rename : RENAME SP mailbox SP mailbox\n        \n        cmd_copy : COPY SP sequence SP mailbox\n        \n        cmd_status  : STATUS SP mailbox SP LPAREN status-items RPAREN\n        \n        status-items : status-items SP WORD\n                     | WORD\n        \n        mailbox : QUOTED\n                | MAILBOX\n                | WORD\n        \n        cmd_uid : UID SP FETCH SP sequence SP LPAREN fetch-attrs RPAREN\n                | UID SP FETCH SP sequence SP fetch-attrs\n                | UID SP STORE SP sequence SP store_args\n        \n        cmd_store : STORE SP sequence SP store_args\n        \n        store_args : PLUS  WORD SP LPAREN flag-list RPAREN\n                   | MINUS WORD SP LPAREN flag-list RPAREN\n                   | WORD SP LPAREN flag-list RPAREN\n        \n        flag-list : flag-value SP flag-value\n                  | flag-value\n        \n        flag-value : BSLASH WORD\n                   | WORD\n        \n        cmd_fetch : FETCH SP sequence SP LPAREN fetch-attrs RPAREN\n                  | FETCH SP sequence SP WORD\n        \n        sequence : sequence COMMA range\n                 | range\n        \n        range : NUMBER COLON NUMBER\n              | NUMBER COLON STAR\n              | NUMBER\n        \n        fetch-attrs : fetch-attrs SP fetch-attr\n                    | fetch-attr\n        \n        fetch-attr : WORD LSBRACKET NUMBER RSBRACKET fetch-partial\n        fetch-attr : WORD LSBRACKET section RSBRACKET fetch-partial\n                   | WORD\n        \n        fetch-partial : LTSIGN NUMBER DOT NUMBER GTSIGN\n                      | LTSIGN NUMBER GTSIGN\n                      | empty\n        \n        section : WORD SP header-list\n                | WORD\n                | empty\n        \n        header-list : LPAREN headers RPAREN\n        \n        headers : headers SP WORD\n                | WORD\n        \n        empty :\n        '
    
_lr_action_items = {'WORD':([0,72,74,75,76,78,80,81,82,83,85,87,110,113,114,116,117,119,126,132,134,136,147,148,149,151,152,155,157,166,170,171,178,183,195,],[3,88,95,95,95,95,95,95,95,95,95,95,95,127,95,95,95,135,141,143,144,146,141,135,141,161,165,167,141,167,179,167,167,192,198,]),'NUMBER':([0,73,77,84,111,112,120,121,151,185,196,],[4,91,91,91,91,124,91,91,162,193,199,]),'$end':([1,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,],[0,-1,-2,-3,-4,-5,-6,-7,-8,-9,-10,-11,-12,-13,-14,-15,-16,-17,-18,-19,-20,-21,-22,]),'SP':([2,3,4,29,33,34,35,36,38,39,40,42,43,44,45,46,47,48,49,89,90,91,93,94,95,98,99,100,101,102,104,105,107,108,123,124,125,135,137,138,139,140,141,142,143,144,146,158,160,161,165,167,169,172,174,175,179,184,186,187,191,192,197,198,200,],[5,-23,-24,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,110,-63,-66,-46,-47,-48,113,114,115,116,117,118,119,120,121,-62,-64,-65,145,147,148,149,-68,-71,152,-45,154,156,149,-67,173,-44,-59,178,149,-81,-81,-58,-69,-74,-70,195,-80,-73,-79,-72,]),'NOOP':([5,],[28,]),'AUTHENTICATE':([5,],[29,]),'CAPABILITY':([5,],[30,]),'CHECK':([5,],[31,]),'CLOSE':([5,],[32,]),'COPY':([5,],[33,]),'CREATE':([5,],[34,]),'DELETE':([5,],[35,]),'EXAMINE':([5,],[36,]),'EXPUNGE':([5,],[37,]),'FETCH':([5,86,],[38,107,]),'LIST':([5,],[39,]),'LOGIN':([5,],[40,]),'LOGOUT':([5,],[41,]),'LSUB':([5,],[42,]),'RENAME':([5,],[43,]),'SELECT':([5,],[44,]),'STATUS':([5,],[45,]),'STORE':([5,86,],[46,108,]),'SUBSCRIBE':([5,],[47,]),'UID':([5,],[48,]),'UNSUBSCRIBE':([5,],[49,]),'EOL':([6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,30,31,32,37,41,88,92,93,94,95,96,97,103,106,109,122,127,128,129,130,131,133,140,141,150,153,158,159,160,174,175,177,181,184,186,187,188,190,197,200,],[50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,-30,-25,-26,-27,-28,-29,-37,-31,-46,-47,-48,-32,-34,-33,-35,-36,-42,-61,-39,-38,-40,-41,-52,-68,-71,-60,-43,-50,-51,-67,-81,-81,-55,-49,-69,-74,-70,-53,-54,-73,-72,]),'QUOTED':([74,75,76,78,79,80,81,82,83,85,87,110,114,115,116,117,],[93,93,93,93,100,93,93,93,93,93,93,93,93,129,93,93,]),'MAILBOX':([74,75,76,78,80,81,82,83,85,87,110,114,116,117,],[94,94,94,94,94,94,94,94,94,94,94,94,94,94,]),'COMMA':([89,90,91,98,105,123,124,125,137,138,],[111,-63,-66,111,111,-62,-64,-65,111,111,]),'COLON':([91,],[112,]),'STAR':([112,],[125,]),'LPAREN':([113,118,145,147,154,156,173,],[126,132,155,157,166,171,183,]),'PLUS':([119,148,],[134,134,]),'MINUS':([119,148,],[136,136,]),'RPAREN':([139,140,141,142,143,160,165,167,168,169,172,174,175,176,179,180,184,186,187,189,191,192,197,198,200,],[150,-68,-71,153,-45,-67,-44,-59,177,-57,181,-81,-81,188,-58,190,-69,-74,-70,-56,194,-80,-73,-79,-72,]),'LSBRACKET':([141,],[151,]),'RSBRACKET':([151,161,162,163,164,182,194,],[-81,-76,174,175,-77,-75,-78,]),'BSLASH':([155,166,171,178,],[170,170,170,170,]),'LTSIGN':([174,175,],[185,185,]),'DOT':([193,],[196,]),'GTSIGN':([193,199,],[197,200,]),}

_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {'command':([0,],[1,]),'tag':([0,],[2,]),'cmd_noop':([5,],[6,]),'cmd_authenticate':([5,],[7,]),'cmd_capability':([5,],[8,]),'cmd_check':([5,],[9,]),'cmd_close':([5,],[10,]),'cmd_copy':([5,],[11,]),'cmd_create':([5,],[12,]),'cmd_delete':([5,],[13,]),'cmd_examine':([5,],[14,]),'cmd_expunge':([5,],[15,]),'cmd_fetch':([5,],[16,]),'cmd_list':([5,],[17,]),'cmd_login':([5,],[18,]),'cmd_logout':([5,],[19,]),'cmd_lsub':([5,],[20,]),'cmd_rename':([5,],[21,]),'cmd_select':([5,],[22,]),'cmd_status':([5,],[23,]),'cmd_store':([5,],[24,]),'cmd_subscribe':([5,],[25,]),'cmd_uid':([5,],[26,]),'cmd_unsubscribe':([5,],[27,]),'sequence':([73,77,84,120,121,],[89,98,105,137,138,]),'range':([73,77,84,111,120,121,],[90,90,90,123,90,90,]),'mailbox':([74,75,76,78,80,81,82,83,85,87,110,114,116,117,],[92,96,97,99,101,102,103,104,106,109,122,128,130,131,]),'store_args':([119,148,],[133,159,]),'fetch-attrs':([126,147,157,],[139,158,172,]),'fetch-attr':([126,147,149,157,],[140,140,160,140,]),'status-items':([132,],[142,]),'section':([151,],[163,]),'empty':([151,174,175,],[164,186,186,]),'flag-list':([155,166,171,],[168,176,180,]),'flag-value':([155,166,171,178,],[169,169,169,189,]),'header-list':([173,],[182,]),'fetch-partial':([174,175,],[184,187,]),'headers':([183,],[191,]),}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
  ("S' -> command","S'",1,None,None,None),
  ('command -> tag SP cmd_noop EOL','command',4,'p_command','parser.py',180),
  ('command -> tag SP cmd_authenticate EOL','command',4,'p_command','parser.py',181),
  ('command -> tag SP cmd_capability EOL','command',4,'p_command','parser.py',182),
  ('command -> tag SP cmd_check EOL','command',4,'p_command','parser.py',183),
  ('command -> tag SP cmd_close EOL','command',4,'p_command','parser.py',184),
  ('command -> tag SP cmd_copy EOL','command',4,'p_command','parser.py',185),
  ('command -> tag SP cmd_create EOL','command',4,'p_command','parser.py',186),
  ('command -> tag SP cmd_delete EOL','command',4,'p_command','parser.py',187),
  ('command -> tag SP cmd_examine EOL','command',4,'p_command','parser.py',188),
  ('command -> tag SP cmd_expunge EOL','command',4,'p_command','parser.py',189),
  ('command -> tag SP cmd_fetch EOL','command',4,'p_command','parser.py',190),
  ('command -> tag SP cmd_list EOL','command',4,'p_command','parser.py',191),
  ('command -> tag SP cmd_login EOL','command',4,'p_command','parser.py',192),
  ('command -> tag SP cmd_logout EOL','command',4,'p_command','parser.py',193),
  ('command -> tag SP cmd_lsub EOL','command',4,'p_command','parser.py',194),
  ('command -> tag SP cmd_rename EOL','command',4,'p_command','parser.py',195),
  ('command -> tag SP cmd_select EOL','command',4,'p_command','parser.py',196),
  ('command -> tag SP cmd_status EOL','command',4,'p_command','parser.py',197),
  ('command -> tag SP cmd_store EOL','command',4,'p_command','parser.py',198),
  ('command -> tag SP cmd_subscribe EOL','command',4,'p_command','parser.py',199),
  ('command -> tag SP cmd_uid EOL','command',4,'p_command','parser.py',200),
  ('command -> tag SP cmd_unsubscribe EOL','command',4,'p_command','parser.py',201),
  ('tag -> WORD','tag',1,'p_tag','parser.py',211),
  ('tag -> NUMBER','tag',1,'p_tag','parser.py',212),
  ('cmd_capability -> CAPABILITY','cmd_capability',1,'p_cmd_COMMON_NOARGS','parser.py',219),
  ('cmd_check -> CHECK','cmd_check',1,'p_cmd_COMMON_NOARGS','parser.py',220),
  ('cmd_close -> CLOSE','cmd_close',1,'p_cmd_COMMON_NOARGS','parser.py',221),
  ('cmd_expunge -> EXPUNGE','cmd_expunge',1,'p_cmd_COMMON_NOARGS','parser.py',222),
  ('cmd_logout -> LOGOUT','cmd_logout',1,'p_cmd_COMMON_NOARGS','parser.py',223),
  ('cmd_noop -> NOOP','cmd_noop',1,'p_cmd_COMMON_NOARGS','parser.py',224),
  ('cmd_create -> CREATE SP mailbox','cmd_create',3,'p_cmd_COMMON_MAILBOX_ARG','parser.py',231),
  ('cmd_delete -> DELETE SP mailbox','cmd_delete',3,'p_cmd_COMMON_MAILBOX_ARG','parser.py',232),
  ('cmd_select -> SELECT SP mailbox','cmd_select',3,'p_cmd_COMMON_MAILBOX_ARG','parser.py',233),
  ('cmd_examine -> EXAMINE SP mailbox','cmd_examine',3,'p_cmd_COMMON_MAILBOX_ARG','parser.py',234),
  ('cmd_subscribe -> SUBSCRIBE SP mailbox','cmd_subscribe',3,'p_cmd_COMMON_MAILBOX_ARG','parser.py',235),
  ('cmd_unsubscribe -> UNSUBSCRIBE SP mailbox','cmd_unsubscribe',3,'p_cmd_COMMON_MAILBOX_ARG','parser.py',236),
  ('cmd_authenticate -> AUTHENTICATE SP WORD','cmd_authenticate',3,'p_cmd_authenticate','parser.py',245),
  ('cmd_login -> LOGIN SP QUOTED SP QUOTED','cmd_login',5,'p_cmd_login','parser.py',252),
  ('cmd_list -> LIST SP mailbox SP mailbox','cmd_list',5,'p_cmd_list','parser.py',262),
  ('cmd_lsub -> LSUB SP mailbox SP mailbox','cmd_lsub',5,'p_cmd_list','parser.py',263),
  ('cmd_rename -> RENAME SP mailbox SP mailbox','cmd_rename',5,'p_cmd_rename','parser.py',273),
  ('cmd_copy -> COPY SP sequence SP mailbox','cmd_copy',5,'p_cmd_copy','parser.py',283),
  ('cmd_status -> STATUS SP mailbox SP LPAREN status-items RPAREN','cmd_status',7,'p_cmd_status','parser.py',293),
  ('status-items -> status-items SP WORD','status-items',3,'p_status_items','parser.py',303),
  ('status-items -> WORD','status-items',1,'p_status_items','parser.py',304),
  ('mailbox -> QUOTED','mailbox',1,'p_mailbox','parser.py',311),
  ('mailbox -> MAILBOX','mailbox',1,'p_mailbox','parser.py',312),
  ('mailbox -> WORD','mailbox',1,'p_mailbox','parser.py',313),
  ('cmd_uid -> UID SP FETCH SP sequence SP LPAREN fetch-attrs RPAREN','cmd_uid',9,'p_cmd_uid','parser.py',320),
  ('cmd_uid -> UID SP FETCH SP sequence SP fetch-attrs','cmd_uid',7,'p_cmd_uid','parser.py',321),
  ('cmd_uid -> UID SP STORE SP sequence SP store_args','cmd_uid',7,'p_cmd_uid','parser.py',322),
  ('cmd_store -> STORE SP sequence SP store_args','cmd_store',5,'p_cmd_store','parser.py',343),
  ('store_args -> PLUS WORD SP LPAREN flag-list RPAREN','store_args',6,'p_store_args','parser.py',353),
  ('store_args -> MINUS WORD SP LPAREN flag-list RPAREN','store_args',6,'p_store_args','parser.py',354),
  ('store_args -> WORD SP LPAREN flag-list RPAREN','store_args',5,'p_store_args','parser.py',355),
  ('flag-list -> flag-value SP flag-value','flag-list',3,'p_flag_list','parser.py',377),
  ('flag-list -> flag-value','flag-list',1,'p_flag_list','parser.py',378),
  ('flag-value -> BSLASH WORD','flag-value',2,'p_flag_value','parser.py',385),
  ('flag-value -> WORD','flag-value',1,'p_flag_value','parser.py',386),
  ('cmd_fetch -> FETCH SP sequence SP LPAREN fetch-attrs RPAREN','cmd_fetch',7,'p_cmd_fetch','parser.py',396),
  ('cmd_fetch -> FETCH SP sequence SP WORD','cmd_fetch',5,'p_cmd_fetch','parser.py',397),
  ('sequence -> sequence COMMA range','sequence',3,'p_sequence','parser.py',427),
  ('sequence -> range','sequence',1,'p_sequence','parser.py',428),
  ('range -> NUMBER COLON NUMBER','range',3,'p_range','parser.py',435),
  ('range -> NUMBER COLON STAR','range',3,'p_range','parser.py',436),
  ('range -> NUMBER','range',1,'p_range','parser.py',437),
  ('fetch-attrs -> fetch-attrs SP fetch-attr','fetch-attrs',3,'p_fetch_attrs','parser.py',446),
  ('fetch-attrs -> fetch-attr','fetch-attrs',1,'p_fetch_attrs','parser.py',447),
  ('fetch-attr -> WORD LSBRACKET NUMBER RSBRACKET fetch-partial','fetch-attr',5,'p_fetch_attr','parser.py',454),
  ('fetch-attr -> WORD LSBRACKET section RSBRACKET fetch-partial','fetch-attr',5,'p_fetch_attr','parser.py',455),
  ('fetch-attr -> WORD','fetch-attr',1,'p_fetch_attr','parser.py',456),
  ('fetch-partial -> LTSIGN NUMBER DOT NUMBER GTSIGN','fetch-partial',5,'p_fetch_partial','parser.py',481),
  ('fetch-partial -> LTSIGN NUMBER GTSIGN','fetch-partial',3,'p_fetch_partial','parser.py',482),
  ('fetch-partial -> empty','fetch-partial',1,'p_fetch_partial','parser.py',483),
  ('section -> WORD SP header-list','section',3,'p_section_spec','parser.py',493),
  ('section -> WORD','section',1,'p_section_spec','parser.py',494),
  ('section -> empty','section',1,'p_section_spec','parser.py',495),
  ('header-list -> LPAREN headers RPAREN','header-list',3,'p_header_list','parser.py',513),
  ('headers -> headers SP WORD','headers',3,'p_headers','parser.py',520),
  ('headers -> WORD','headers',1,'p_headers','parser.py',521),
  ('empty -> <empty>','empty',0,'p_empty','parser.py',528),
]
