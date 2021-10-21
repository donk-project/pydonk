# Donk Project
# Copyright (c) 2021 Warriorstar Orion <orion@snowfrost.garden>
# SPDX-License-Identifier: MIT
from mapparse.reader import TreeToDmmData, path, resource


class DMLargeNumber:
    def __init__(self, val):
        self.val = val

    def __format__(self, format_spec):
        ss = ('{0:'+format_spec+'}').format(self.val)
        if ('e' in ss):
            mantissa, exp = ss.split('e')
            return mantissa + 'e' + exp[0] + '0' + exp[1:]
        return ss


class Writer(object):
    def __init__(self, dmm: TreeToDmmData):
        self.dmm = dmm

    def write_file(self, filename):
        with open(filename, 'w') as f:
            f.write(
                "//MAP CONVERTED BY dmm2tgm.py THIS HEADER COMMENT PREVENTS RECONVERSION, DO NOT REMOVE\n")
            f.write(self.write_keys())
            f.write('\n\n')
            f.write(self.write_map())
            f.write('\n')

    def write_tile(self, tile):
        datums = []
        for datum in tile.d:
            datums.append(self.write_datum(datum))
        return ',\n'.join(datums)

    def write_key(self, key, tile):
        parts = [f'"{key}" = (\n']
        parts.append(self.write_tile(tile))
        parts.append(')')
        return ''.join(parts)

    def write_keys(self):
        result = []
        for key, tile in self.dmm.keys.items():
            result.append(self.write_key(key, tile))
        return '\n'.join(result)

    def write_val(self, v):
        if isinstance(v, resource):
            return f"'{v}'"
        elif isinstance(v, path):
            return str(v)
        elif isinstance(v, str):
            return f'"{v}"'
        elif isinstance(v, dict):
            parts = []
            for k, kv in v.items():
                parts.append(f'{self.write_val(k)} = {self.write_val(kv)}')
            return ", ".join(parts)
        elif isinstance(v, list):
            result = ["list("]
            parts = []
            add_spacing = ""
            for i in v:
                if isinstance(i, dict):
                    add_spacing = " "
                parts.append(self.write_val(i))
            result.append(f',{add_spacing}'.join(parts))
            result.append(")")
            return ''.join(result)
        elif isinstance(v, (float, int)):
            if v > 999999:
                return '{0:.0e}'.format(DMLargeNumber(v))
            return str(v)
        elif v is None:
            return "null"

        return v

    def write_datum(self, datum):
        parts = [str(datum['name'])]
        if 'values' in datum:
            parts.append("{\n\t")
            attrs = []
            for k, v in datum['values'].items():
                attrs.append(f"{k} = {self.write_val(v)}")
            parts.append(";\n\t".join(attrs))
            parts.append("\n\t}")
        return "".join(parts)

    def write_map(self):
        result = []
        for coords, rows in self.dmm.map.items():
            c = f"({coords[0]},{coords[1]},{coords[2]})"
            parts = [c, ' = {"\n']
            parts.append('\n'.join([k for k in rows]))
            parts.append('\n"}')
            result.append(''.join(parts))
        return '\n'.join(result)
