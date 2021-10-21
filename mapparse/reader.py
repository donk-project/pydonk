# Donk Project
# Copyright (c) 2021 Warriorstar Orion <orion@snowfrost.garden>
# SPDX-License-Identifier: MIT
from collections import OrderedDict

from lark import Lark, Transformer

DMM_GRAMMAR = r"""
start          : dmm_header dmm_keydecls dmm_map
dmm_header     : "//MAP CONVERTED BY dmm2tgm.py THIS HEADER COMMENT PREVENTS RECONVERSION, DO NOT REMOVE"
dmm_keydecls   : dmm_keydecl*
dmm_keydecl    : "\"" dmm_key "\"" "=" "(" key_tile ")"
key_tile       : tile_datum ("," tile_datum)*
tile_datum     : (treepath | treepath datum_props)
treepath       : ("/" CNAME)+
datum_props    : "{" datum_prop (";" datum_prop)* "}"
datum_prop     : CNAME "=" prop_value
prop_value     : dmlist | SIGNED_INT | INT | FLOAT | STRING | treepath | NULL | resource
dmlist         : "list(" (prop_value | kv_pair) ("," (prop_value | kv_pair))* ")"
resource       : /'((?:.(?!(?<![\\\\])'))*.?)'/
kv_pair        : STRING "=" prop_value
dmm_key        : CNAME
NULL           : "null"
dmm_map        : dmm_row*
dmm_row        : "(" INT "," INT "," INT ")" "=" "{\"" dmm_key* "\"}"

%import common.CNAME   -> CNAME
%import common.ESCAPED_STRING   -> STRING
%import common.FLOAT
%import common.INT    -> INT
%import common.SIGNED_INT    -> SIGNED_INT
%import common.WS
%ignore WS
"""


class resource(object):
    def __init__(self, n):
        self.name = n

    def __str__(self):
        return self.name


class path(object):
    def __init__(self, p):
        self.path = p

    def __str__(self):
        return self.path

    def __repr__(self):
        return f"`{self.path}`"

    def __eq__(self, o: object) -> bool:
        if isinstance(o, path):
            return self.path == o.path
        if isinstance(o, str):
            return self.path == o

    def startswith(self, k):
        return self.path.startswith(k)


class Tile(object):
    def __init__(self, d):
        self.d = d

    def get_datums_with_prefix(self, prefix):
        return [idx for idx, datum in enumerate(self.d) if datum['name'].startswith(prefix)]

    def get_datums_of_type(self, path):
        return [idx for idx, datum in enumerate(self.d) if datum['name'] == path]

    def set_value(self, datum_idx, k, v):
        d = self.d[datum_idx]
        if 'values' not in d:
            d['values'] = dict()
        d['values'][k] = v

    def get_value(self, datum_idx, k):
        return self.d[datum_idx]['values'][k]

    def get_propnames(self, datum_idx):
        if 'values' not in self.d[datum_idx]:
            return []
        return self.d[datum_idx]['values'].keys()

    def del_datums_of_type(self, path):
        dels = []
        for idx, datum in enumerate(self.d):
            if datum['name'] == path:
                dels.append(idx)

        for idx in sorted(dels, reverse=True):
            self.d.pop(idx)


class Reader:
    def __init__(self, dmm_filename):
        self.dmm_filename = dmm_filename
        self.parser = Lark(DMM_GRAMMAR, parser='lalr',
                           start="start", transformer=TreeToDmmData())
        self.parsed = False

    def Read(self):
        if self.parsed:
            raise RuntimeError("DMM already parsed")

        dmm_data = open(self.dmm_filename).read()

        data = self.parser.parse(dmm_data)
        self.parsed = True

        return data


class TreeToDmmData(Transformer):
    def __init__(self):
        self.keys = OrderedDict()
        self.map = OrderedDict()

    def start(self, sk):
        return self

    def dmm_key(self, sk):
        return sk.pop(0)

    def dmm_keydecl(self, sk):
        self.keys[sk[0]] = sk[1]

    def INT(self, sk):
        return int(sk.value)

    def SIGNED_INT(self, sk):
        return int(sk.value)

    def CNAME(self, sk):
        return sk.value

    def STRING(self, sk):
        # remove leading and trailing quotes, *not* equivalent to .strip('"')
        return sk.value[1:-1]

    def FLOAT(self, sk):
        return float(sk.value)

    def NULL(self, sk):
        return None

    def treepath(self, sk):
        return path('/' + '/'.join(sk))

    def tile_datum(self, sk):
        # from ipdb import set_trace; set_trace()
        result = {'name': sk.pop(0)}
        if sk:
            result['values'] = OrderedDict()
            for k, v in sk[0].items():
                result['values'][k] = v

        return result

    def key_tile(self, sk):
        return Tile(sk)

    def datum_props(self, sk):
        result = dict()
        for kv in sk:
            result.update(kv)
        return result

    def datum_prop(self, sk):
        return {sk[0]: sk[1]}

    def prop_value(self, sk):
        return sk[0]

    def dmlist(self, sk):
        l = list()
        for k in sk:
            l.append(k)
        return l

    def resource(self, sk):
        return resource(sk[0].value[1:-1])

    def kv_pair(self, sk):
        return {sk[0]: sk[1]}

    def dmm_row(self, sk):
        coords = tuple(sk[:3])
        self.map[coords] = sk[3:]
