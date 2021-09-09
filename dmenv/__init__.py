from collections.abc import Iterable
from reprlib import recursive_repr
from numbers import Number


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


class dmlist_base(object):
    """A dmlist emulates the behavior of the "list" data structure in Dreammaker.

    It is the worst data structure I have ever encountered in my life.

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

    >>> class A: pass
    >>> l = dmlist()
    >>> a = A()
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

    TODO: Add more specific behavior checks
    """

    def __init__(self, keyvalues=None):
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
                    self.keys[idx]

            if not found_key:
                self.keys.append(key_or_index)
                self.values.append(value)

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

    def __bool__(self) -> bool:
        return len(self.values) > 0

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Iterable):
            return self.values == o
        elif isinstance(o, dmlist_base):
            return self.keys == o.keys and self.values == o.values
        return False

    def __add__(self, other):
        self.__iadd__(other)

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

    def __or__(self, other):
        result = dmlist_base()
        result.keys = list(self.keys)
        result.values = list(self.values)
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
        self._check_integrity()
        return len(self.keys)

    def __contains__(self, item):
        return item in self.keys

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
    """
    syntax_error = SyntaxError(
        "Allowed syntax: dmlist[<k>: <v>(, <k>: <v>...)]")

    def __getitem__(self, keys):
        if isinstance(keys, slice):
            keys = (keys,)
        od = self()
        for k in keys:
            if isinstance(k, slice) and k.step is None:
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