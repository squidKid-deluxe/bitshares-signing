import json
from binascii import unhexlify
from struct import pack  # convert to string representation of C struct

from .utilities import from_iso_date

# bitsharesbase/objecttypes.py used by ObjectId() to confirm a.b.c
TYPES = {
    "account": 2,
    "asset": 3,
    "limit_order": 7,
    "liquidity_pool": 19,
}


class ObjectId:
    """
    encodes a.b.c object ids - serializes the *instance* only!
    """

    def __init__(self, object_str, type_verify=None):
        # if after splitting a.b.c there are 3 pieces:
        if len(object_str.split(".")) == 3:
            # assign those three pieces to a, b, and c
            aaa, bbb, ccc = object_str.split(".")
            # assure they are integers
            self.aaa = int(aaa)
            self.bbb = int(bbb)
            self.ccc = int(ccc)
            # serialize the c element; the "instance"
            self.instance = Id(self.ccc)
            self.abc = object_str
            # 1.2.x:account, 1.3.x:asset, 1.7.x:limit, etc as defined in TYPES
            if type_verify:
                assert TYPES[type_verify] == int(bbb), (
                    # except raise error showing mismatch
                    "Object id does not match object type! "
                    + "Excpected %d, got %d" % (TYPES[type_verify], int(bbb))
                )
        else:
            raise Exception("Object id is invalid")

    def __bytes__(self):
        """
        bytes of serialized c element; the "instance"
        """
        return bytes(self.instance)


class Id:
    """
    serializes the c element of "a.b.c" types
    merged with Varint32()
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return bytes(varint(self.data))


class Array:
    """
    serializes lists as byte strings
    merged with Set() and Varint32()
    """

    def __init__(self, data):
        self.data = data or []
        self.length = int(len(self.data))

    def __bytes__(self):
        return bytes(varint(self.length)) + b"".join([bytes(a) for a in self.data])


class Uint8:
    """
    byte string of 8 bit unsigned integers
    merged with Bool()
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<B", self.data)


class Uint16:
    """
    byte string of 16 bit unsigned integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<H", self.data)


class Uint32:
    """
    byte string of 32 bit unsigned integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<I", self.data)


class Uint64:
    """
    byte string of 64 bit unsigned integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<Q", self.data)


class Int64:
    """
    byte string of 64 bit signed integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<q", self.data)


def unicodify(data):
    r = []
    for s in data:
        o = ord(s)
        if (o <= 7) or (o == 11) or (o > 13 and o < 32):
            r.append("u%04x" % o)
        elif o == 8:
            r.append("b")
        elif o == 9:
            r.append("\t")
        elif o == 10:
            r.append("\n")
        elif o == 12:
            r.append("f")
        elif o == 13:
            r.append("\r")
        else:
            r.append(s)
    return bytes("".join(r), "utf-8")


class String:
    def __init__(self, d):
        self.data = d

    def __bytes__(self):
        if self.data:
            d = unicodify(self.data)
        else:
            d = b""
        return varint(len(d)) + d

    def __str__(self):
        return "%s" % str(self.data)


class Optional:
    """
    #
    """

    def __init__(self, data):
        self.data = data

    def __bytes__(self):
        if not bool(self.data):
            return bytes(Uint8(0))
        return (
            bytes(Uint8(1)) + bytes(self.data) if bytes(self.data) else bytes(Uint8(0))
        )

    def __str__(self):
        return str(self.data)

    def isempty(self):
        """
        is there no data
        """
        if self.data is None:
            return True
        if not bool(str(self.data)):  # pragma: no cover
            return True
        return not bool(bytes(self.data))


class Signature:
    """
    used to disable bytes() method on Signatures in OrderedDicts
    """

    def __init__(self, data):
        self.data = data

    def __bytes__(self):
        return self.data  # note does NOT return bytes(self.data)


class PointInTime:
    """
    used to pack ISO8601 time as 4 byte unix epoch integer as bytes
    """

    def __init__(self, data):
        self.data = data

    def __bytes__(self):
        return pack("<I", from_iso_date(self.data))


class StaticVariant:
    """
    #
    """

    def __init__(self, data, type_id):
        self.data = data
        self.type_id = type_id

    def __bytes__(self):
        return varint(self.type_id) + bytes(self.data)

    def __str__(self):
        return json.dumps([self.type_id, self.data.json()])


class Bytes:
    """Bytes

    Initializes from and stores internally as a string of hex digits.
    Byte-serializes as a length-prefixed series of bytes represented
    by those hex digits.

    Ex: len(str(Bytes("deadbeef")) == 8   # Eight hex chars
        len(bytes(Bytes("deadbeef")) == 5 # Four data bytes plus varint length

    Implements __json__() method to disambiguate between string and numeric in
    event where hex digits include only numeric digits and no alpha digits.

    """

    def __init__(self, d):
        self.data = d

    def __bytes__(self):
        d = unhexlify(bytes(self.data, "utf-8"))
        return varint(len(d)) + d

    def __json__(self):
        return str(self.data)

    def __str__(self):
        return str(self.data)


class Extension(Array):
    sorted_options = []

    def __init__(self, *args, **kwargs):
        self.json = {}
        a = []
        for key, value in kwargs.items():
            self.json.update({key: value})
        for arg in args:
            if isinstance(arg, dict):
                self.json.update(arg)

        for index, extension in enumerate(self.sorted_options):
            name = extension[0]
            klass = extension[1]
            for key, value in self.json.items():
                if key.lower() == name.lower():
                    a.append(StaticVariant(klass(value), index))
        super().__init__(a)

    def __str__(self):
        """We overload the __str__ function because the json representation is different
        for extensions."""
        return json.dumps(self.json)


# VARINT
def varint(num):
    """
    varint encoding normally saves memory on smaller numbers
    yet retains ability to represent numbers of any magnitude
    specifically, this does the following:
     - take a number, see if it fits in a 7 bit int:
     - - if not, use the 8th as a continuation bit
     - - - continue (see if the number fits in the next 7)
     - - if so, add the last 7 bit chunk
    """
    data = b""
    while num >= 0x80:
        data += bytes([(num & 0x7F) | 0x80])
        num >>= 7
    data += bytes([num])
    return data
