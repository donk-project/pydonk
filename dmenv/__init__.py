# Donk Project
# Copyright (c) 2021 Warriorstar Orion <orion@snowfrost.garden>
# SPDX-License-Identifier: MIT
from collections import defaultdict
from collections.abc import Iterable
from reprlib import recursive_repr
from numbers import Number
from typing import Any
import uuid


def FullyQualifiedPath(s: str) -> str:
    if not s:
        raise RuntimeError("empty path")
    if s.startswith("/area"):
        s = "/datum/atom" + s
    elif s.startswith("/atom"):
        s = "/datum" + s
    elif s.startswith("/mob"):
        s = "/datum/atom/movable" + s
    elif s.startswith("/turf"):
        s = "/datum/atom" + s
    elif s.startswith("/obj"):
        s = "/datum/atom/movable" + s

    return s


class iota(object):
    """Iota is the core class of all subtypes represented in the DM object tree.

    It is largely concerned with the proper book-keeping of references to
    objects that are deleted by a call to DM's core `del()` proc. `del()`
    actually goes through every field of every known object, and every list, to
    determine if a reference to the object exists. We just have the object track
    these references.
    """

    def __init__(self, *args, **kwargs):
        self._add_lists = set()
        self._add_vars = defaultdict(set)
        self._initials = dict()
        super().__init__(*args, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        x = super().__setattr__(name, value)
        if isinstance(value, iota):
            value._add_vars[self].add(name)
        return x


class dmlist_base(object):
    """A dmlist emulates the behavior of the "list" data structure in Dreammaker.

    Every dmlist has an associated UUID used for hashing and comparing dmlist
    references during object reference book-keeping.

    DM lists are 1-indexed.
    >>> l = dmlist_base()
    >>> l.append("foo")
    >>> l[1] == "foo"
    True

    DM lists can be used as dicts, and element order is preserved.
    >>> l = dmlist_base()
    >>> l["foo"] = "bar"

    >>> l = dmlist_base([("foo", "bar"), ("baz", "quux")])
    >>> l["foo"] == "bar"
    True
    >>> l["baz"] == "quux"
    True

    Only strings and objects are permitted values for keys.
    >>> l = dmlist_base(["foo", "bar", "baz"])
    >>> l[3] = "quux"
    >>> l == ["foo", "bar", "quux"]
    True
    >>> l = dmlist_base([(5, "foo")])
    Traceback (most recent call last):
        ...
    IndexError: list index out of range

    DM lists always return a value for key-indexing, even if it's None.
    >>> l = dmlist_base()
    >>> l["foo"] = 1
    >>> l["baz"] is None
    True

    If a DM list hasn't received a key-value entry, key-indexing into the list
    will still work, but will always return None.
    >>> l = dmlist_base()
    >>> l.append("foo")
    >>> l["foo"] is None
    True

    Appending works as expected.
    >>> l = dmlist_base([4, 5, 6])
    >>> l += [1, 2, 3]
    >>> l == [4, 5, 6, 1, 2, 3]
    True

    >>> l = dmlist_base(["foo", "bar"])
    >>> l += dmlist_base(["baz", "quux"])
    >>> l == ["foo", "bar", "baz", "quux"]
    True

    In-place removal only removes the last instance of an element. This behavior
    gets weird when there are both associated and non-associated elements in the
    list.
    >>> l = dmlist_base(["foo", "bar", "baz", "foo"])
    >>> l -= "foo"
    >>> l == ["foo", "bar", "baz"]
    True

    >>> l = dmlist_base(["foo", "bar", "baz", "foo"])
    >>> l -= dmlist_base(["foo"])
    >>> l == ["foo", "bar", "baz"]
    True

    DM lists support a handful of order-preserving set operations. The first is union:
    >>> l = dmlist_base([1, 2, 3])
    >>> m = dmlist_base([1, 5, 6])
    >>> l | m == [1, 2, 3, 5, 6]
    True

    >>> l = dmlist_base([1, 2, 3])
    >>> m = dmlist_base([1, 5, 6])
    >>> l.append("bar", key="foo")
    >>> l.append(20)
    >>> m.append(20)
    >>> m.append("quux", key="foo")
    >>> l | m == [1, 2, 3, "bar", 20, 5, 6]
    True

    >>> l = dmlist_base()
    >>> l = l | "test"
    >>> l[1] == "test"
    True

    >>> l = dmlist_base(["foo", "bar", "baz"])
    >>> l |= ["bar", "quux"]
    >>> l == ["foo", "bar", "baz", "quux"]
    True

    >>> l = dmlist()
    >>> a = iota()
    >>> l |= a
    >>> l |= a
    >>> len(l) == 1
    True

    When multiple entries share a key, the last value with that key is returned.
    >>> l = dmlist_base([("foo", "bar"), ("foo", "quux")])
    >>> l["foo"] == "quux"
    True

    Expected procs include Find:
    >>> l = dmlist_base(["foo", "bar", "baz", "quux"])
    >>> l.Find("bar")
    2

    >>> l = dmlist([("foo", "bar"), ("baz", "quux")])
    >>> l.Find("baz")
    2
    >>> l.Find("quux")
    0

    >>> l = dmlist()
    >>> l["a"] = 3
    >>> l["b"] = 4
    >>> l["c"] = 5
    >>> i = iota()
    >>> l["b"] = i
    >>> l["b"] == i 
    True

    Containment checks apply to keys, and non-key values, only.
    >>> l = dmlist["foo": "bar"]
    >>> "foo" in l
    True
    >>> "bar" in l
    False
    >>> l = dmlist["foo"]
    >>> "foo" in l
    True

    TODO: Add more specific behavior checks
    """

    def __init__(self, keyvalues=None):
        self.uuid = uuid.uuid4()
        self.keys = list()
        self.values = list()
        if keyvalues is None or len(keyvalues) == 0:
            return
        vt = type(keyvalues[0])
        for kv in keyvalues:
            if type(kv) != vt:
                raise RuntimeError("incompatible types added to dmlist init")
            elif isinstance(kv, str):
                self.keys.append(None)
                self.values.append(kv)
            elif isinstance(kv, Iterable):
                assert len(kv) == 2
                if isinstance(kv[0], Number):
                    raise IndexError("list index out of range")
                self.keys.append(kv[0])
                self.values.append(kv[1])
            else:
                self.keys.append(None)
                self.values.append(kv)

            vt = type(kv)
        self._check_integrity()

    # Keys are only valid if the index is a valid key, or if a key-value
    # pair has been added. If the key is None, then getting a value by index
    # returns the value. If the key is not None, then getting a value by index
    # returns the key.
    def __getitem__(self, key_or_index):
        if key_or_index == 0:
            raise RuntimeError('dmlist indexes start at 1')
        if isinstance(key_or_index, Number):
            key = self.keys[key_or_index - 1]
            if key is None:
                return self.values[key_or_index - 1]
            return self.keys[key_or_index - 1]
        for idx, k in reversed(list(enumerate(self.keys))):
            if k == key_or_index:
                return self.values[idx]

    def __iter__(self):
        return iter([self.values[idx] if self.keys[idx] is None else self.keys[idx] for idx in range(len(self.keys))])

    def __contains__(self, item):
        for idx in range(len(self.keys)):
            k = self.keys[idx]
            v = self.values[idx]
            if k is None:
                if item == v:
                    return True
            elif item == k:
                return True

        return False

    def __setitem__(self, key_or_index, value):
        if isinstance(key_or_index, Number):
            if key_or_index > len(self.keys):
                raise IndexError('index out of range')
            self.values[key_or_index - 1] = value
        else:
            found_key = False
            for idx, k in enumerate(self.keys):
                if k == key_or_index:
                    found_key = True
                    self.values[idx] = value

            if not found_key:
                self.keys.append(key_or_index)
                self.values.append(value)

        if isinstance(key_or_index, iota):
            key_or_index._add_lists.add(self)
        if isinstance(value, iota):
            value._add_lists.add(self)

        self._check_integrity()

    def newlist(*objs):
        return [obj() for obj in objs]

    def _check_integrity(self):
        if len(self.keys) != len(self.values):
            raise RuntimeError("dmlist integrity check failed")

    def _has_none_key_value(self, value):
        for idx, key in enumerate(self.keys):
            if key is None and self.values[idx] == value:
                return True
        return False

    def append(self, value, key=None):
        self.keys.append(key)
        self.values.append(value)
        if isinstance(value, iota):
            value._add_lists.add(self)
        if isinstance(key, iota):
            key._add_lists.add(self)

    def _safe_duplicate(self):
        result = dmlist()
        result.keys = list(self.keys)
        result.values = list(self.values)
        for k in result.keys:
            if isinstance(k, iota):
                k._add_lists.add(result)
        for v in result.values:
            if isinstance(v, iota):
                v._add_lists.add(result)

        return result

    def __hash__(self) -> int:
        return self.uuid.int

    def __eq__(self, o: object) -> bool:
        return self.uuid == o.uuid

    def __bool__(self) -> bool:
        return len(self.values) > 0

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Iterable):
            return self.values == o
        elif isinstance(o, dmlist_base):
            return self.keys == o.keys and self.values == o.values
        return False

    def __add__(self, other):
        result = self._safe_duplicate()
        if isinstance(other, dmlist_base):
            other._check_integrity()
            for i in range(len(other.keys)):
                key = other.keys[i]
                val = other.values[i]
                if key is None:
                    result.append(val)
                else:
                    result[key] = val
        elif isinstance(other, Iterable):
            for k in other:
                result.append(k)
        else:
            result.append(other)

        result._check_integrity()
        return result

    def __iadd__(self, other):
        if isinstance(other, dmlist_base):
            other._check_integrity()
            for i in range(len(other.keys)):
                key = other.keys[i]
                val = other.values[i]
                if key is None:
                    self.append(val)
                else:
                    self[key] = val
        elif isinstance(other, Iterable):
            for k in other:
                self.append(k)
        else:
            self.append(other)

        self._check_integrity()
        return self

    def __sub__(self, other):
        result = self._safe_duplicate()
        if isinstance(other, dmlist_base):
            other._check_integrity()
            for i in range(len(other.keys)):
                val = other.values[i]
                result -= val
                if isinstance(val, iota):
                    val._add_lists.remove(result)
        else:
            if result.values.count(other):
                # Get index of last matching value
                idx = len(result.values) - 1 - result.values[::-1].index(other)
                result.values.pop(idx)
                result.keys.pop(idx)
                # TODO: Since there may still be iota instances of the popped
                # value/key in the list, after removing the last found value, we
                # can't just remove result from the value and key's _add_lists.
                # This is fine because del() will check the list and remove it
                # from the _add_list, but there's probably a way to make it do
                # less work.

        return result

    def __isub__(self, other):
        if isinstance(other, dmlist_base):
            other._check_integrity()
            for i in range(len(other.keys)):
                val = other.values[i]
                self -= val
                if isinstance(val, iota):
                    val._add_lists.remove(self)
        else:
            if self.values.count(other):
                # Get index of last matching value
                idx = len(self.values) - 1 - self.values[::-1].index(other)
                self.values.pop(idx)
                self.keys.pop(idx)

        return self

    def __ior__(self, other):
        if isinstance(other, dmlist_base):
            for idx, other_key in enumerate(other.keys):
                other_val = other.values[idx]
                # print(f"idx={idx} other_key={other_key} other_val={other_val}")
                # Keyless values
                if other_key is None:
                    if self._has_none_key_value(other_val):
                        continue
                    else:
                        self.append(other_val)
                else:
                    if other_key not in self.keys:
                        self.append(other_val, key=other_key)
        elif isinstance(other, str) or isinstance(other, Number):
            if other not in self.keys:
                self.append(other)
        elif isinstance(other, Iterable):
            for idx, other_val in enumerate(other):
                if self._has_none_key_value(other_val):
                    continue
                else:
                    self.append(other_val)
        else:
            if other not in self.values:
                self.append(other)

        self._check_integrity()
        return self

    def __or__(self, other):
        result = self._safe_duplicate()
        if isinstance(other, dmlist_base):
            for idx, other_key in enumerate(other.keys):
                other_val = other.values[idx]
                # print(f"idx={idx} other_key={other_key} other_val={other_val}")
                # Keyless values
                if other_key is None:
                    if result._has_none_key_value(other_val):
                        continue
                    else:
                        result.append(other_val)
                else:
                    if other_key not in result.keys:
                        result.append(other_val, key=other_key)
        elif isinstance(other, str) or isinstance(other, Number):
            if other not in result.keys:
                result.append(other)
        elif isinstance(other, Iterable):
            for idx, other_val in enumerate(other):
                if result._has_none_key_value(other_val):
                    continue
                else:
                    result.append(other_val)
        else:
            if other not in result.values:
                result.append(other)

        result._check_integrity()
        return result

    def __repr__(self):
        return dmlist_repr(self)

    def __len__(self):
        return len(self.keys)

    def clear(self):
        self.keys.clear()
        self.values.clear()

    def Find(self, Elem, Start=1, End=0):
        # TODO: Support Start and End
        self._check_integrity()
        for i in range(len(self.keys)):
            if self.keys[i] is None and self.values[i] == Elem:
                return i + 1
            elif self.keys[i] == Elem:
                return i + 1
        return 0

    def Cut(self, Start=1, End=0):
        # TODO: Support Start and End
        self._check_integrity()
        self.clear()


class dmlistType(type):
    """
    This implementation is from the odict library, Copyright Anthony Towns
    <aj@erisian.com.au> and made available under the MIT license.

    This piece of the implementation allows us to use a convenient syntax for
    declaring literals.

    The dmlistType provides a way to use a dict-like syntax for DM list
    literals.
    >>> l = dmlist["foo": "bar", "baz": 4]
    >>> l["foo"] == "bar"
    True
    >>> l[2] == "baz"
    True

    This syntax may also be used to create an ordinary array.
    >>> l = dmlist[3, 5, 7, 9]
    >>> l[2] == 5
    True

    The `newlist` method accepts types, and upon being invoked returns a list of
    instances corresponding to each type.
    >>> l = dmlist.newlist(int, str)
    >>> l == [0, ""]
    True

    While integers are not allowed as dmlist keys, a special constructor syntax
    is supported where the values are simply monotonically increasing integers.
    This syntax is called an "integer map" below, and is encountered
    occasionally in SS13 codebases.
    >>> l = dmlist[1: "abc", 2: "def"]
    >>> l[1] == "abc"
    True

    If a single string element is passed to the constructor, do not consider it
    a list of characters, as Python would.
    >>> l = dmlist["test"]
    >>> l[1] == "test"
    True
    >>> "test" in l
    True
    """
    syntax_error = SyntaxError(
        "Allowed syntax: dmlist[<k>: <v>(, <k>: <v>...)]")

    def __getitem__(self, keys):
        od = self()

        if isinstance(keys, slice) or isinstance(keys, type):
            keys = (keys,)
        elif isinstance(keys, str):
            od.append(keys)
            return od

        test_keys = [k.start for k in keys if isinstance(k, slice)]
        is_integer_keys = all([isinstance(k, int) for k in test_keys])
        is_natural_order = test_keys == list(range(1, len(keys) + 1))
        is_integer_map = is_integer_keys and is_natural_order

        for k in keys:
            if is_integer_map:
                od.append(k.stop)
            elif isinstance(k, slice) and k.step is None:
                od[k.start] = k.stop
            else:
                od.append(k)
        return od


@recursive_repr(fillvalue="dmlist[...]")
def dmlist_repr(self):
    if len(self.keys) == 0:
        return "dmlist()"
    else:
        return "dmlist[%s]" % (", ".join("{}{}".format(f"{self.keys[i]}: " if self.keys[i] else "", self.values[i]) for i in range(len(self.keys))),)


dmlist = dmlistType(str('dmlist'), (dmlist_base,), {"__repr__": dmlist_repr})


def _del(obj: iota):
    """_del is the replacement for DM's builtin proc `del()`.

    When called, it uses the object's bookkeeping data to remove the object
    itself from any dmlists or other objects that refer to it.

    >>> i = iota()
    >>> j = iota()
    >>> i.foo = j
    >>> _del(j)
    >>> i.foo == None
    True

    >>> i = iota()
    >>> l = dmlist()
    >>> l.append(i)
    >>> _del(i)
    >>> l[1] == None
    True

    >>> l = dmlist()
    >>> i = iota()
    >>> l["a"] = i
    >>> _del(i)
    >>> l["a"] is None
    True

    """
    for l in obj._add_lists:
        l._check_integrity()
        for i in range(len(l.keys)):
            if l.values[i] == obj:
                l.values[i] = None
            if l.keys[i] == obj:
                l.keys[i] = None
                # In DM, the value of a deleted-object key is no longer
                # accessible by indexing into the list with None
                l.values[i] = None

    obj._add_lists.clear()

    for i, varnames in obj._add_vars.items():
        for varname in varnames:
            i.__setattr__(varname, None)

    obj._add_vars.clear()
