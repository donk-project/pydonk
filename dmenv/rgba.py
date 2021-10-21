# Donk Project
# Copyright (c) 2021 Warriorstar Orion <orion@snowfrost.garden>
# SPDX-License-Identifier: MIT
import re
from typing import NamedTuple


class rgba(NamedTuple):

    r: int
    g: int
    b: int
    a: int

    def __str__(self):
        return f"rgba({self.r} {self.g} {self.b} {self.a})"

    def __repr__(self):
        return f"rgba({self.r} {self.g} {self.b} {self.a})"


hex_re = re.compile('^#([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})?$')


def normalize_rgba(c):
    return (c.r/255.0, c.g/255.0, c.b/255.0, c.a/255.0)


def unnormalize_rgba(r, g, b, a):
    return rgba(int(r * 255.0), int(g * 255.0), int(b * 255.0), int(a * 255.0))


def from_hexstring(hexstring):
    """
    >>> from_hexstring('#000000')
    rgba(0 0 0 255)

    >>> from_hexstring('#09080706')
    rgba(9 8 7 6)

    >>> from_hexstring('#abcdef9a')
    rgba(171 205 239 154)
    """
    r, g, b, a = hex_re.search(hexstring).groups()
    return rgba(int(r, 16), int(g, 16), int(b, 16), 255 if a is None else int(a, 16))
