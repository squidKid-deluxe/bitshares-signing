"""
graphene_signing.py

Graphene types and signing function required to authenticate operation being
broadcast to BitShares

WTFPL litepresence.com Dec 2021 & squidKid-deluxe Jan 2024
"""

# Standard Python modules
from binascii import hexlify, unhexlify
from hashlib import new as hashlib_new
from hashlib import sha256

# Third party modules
from ecdsa import SECP256k1 as ecdsa_SECP256k1
from ecdsa import SigningKey as ecdsa_SigningKey
from ecdsa import VerifyingKey as ecdsa_VerifyingKey
from ecdsa import numbertheory as ecdsa_numbertheory
from ecdsa import util as ecdsa_util

# Graphene signing modules
from .config import PREFIX

# Global constants
BASE58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
HEXDIGITS = "0123456789abcdefABCDEF"


class Base58:
    """Abstraction layer for base58 encoded strings and their hex/binary representation"""

    def __init__(self, data, prefix=PREFIX):
        self._prefix = prefix
        if all(c in HEXDIGITS for c in data):
            self._hex = data
        elif data[0] in ["5", "6"]:
            self._hex = base58_check_decode(data)
        elif data[0] in ["K", "L"]:
            self._hex = base58_check_decode(data)[:-2]
        elif data[: len(self._prefix)] == self._prefix:
            self._hex = gph_base58_check_decode(data[len(self._prefix) :])
        else:
            raise ValueError("Error loading Base58 object")

    def __format__(self, _format):
        if _format.upper() != PREFIX:
            raise ValueError(f"Format must be {PREFIX}")
        return _format.upper() + str(self)

    def __repr__(self):
        """Return hex string representation"""
        return self._hex

    def __str__(self):
        """Return base58 string representation"""
        return gph_base58_check_encode(self._hex)

    def __bytes__(self):
        """Return raw bytes representation"""
        return unhexlify(self._hex)


def base58_decode(base58_str):
    """Convert base58 string to hexadecimal"""
    base58_text = bytes(base58_str, "ascii")
    num = 0
    leading_zeroes_count = 0

    for byte in base58_text:
        num = num * 58 + BASE58.find(byte)
        if num == 0:
            leading_zeroes_count += 1

    res = bytearray()
    while num >= 256:
        div, mod = divmod(num, 256)
        res.insert(0, mod)
        num = div
    res.insert(0, num)

    return hexlify(bytearray(1) * leading_zeroes_count + res).decode("ascii")


def base58_encode(hexstring):
    """Convert hexadecimal string to base58"""
    byteseq = bytes(unhexlify(bytes(hexstring, "ascii")))
    num = 0
    leading_zeroes_count = 0

    for byte in byteseq:
        num = num * 256 + byte
        if num == 0:
            leading_zeroes_count += 1

    res = bytearray()
    while num >= 58:
        div, mod = divmod(num, 58)
        res.insert(0, BASE58[mod])
        num = div
    res.insert(0, BASE58[num])

    return (BASE58[0:1] * leading_zeroes_count + res).decode("ascii")


def ripemd160(string):
    """Generate 160-bit RIPEMD hash"""
    r160 = hashlib_new("ripemd160")
    r160.update(unhexlify(string))
    return r160.digest()


def double_sha256(string):
    """Generate double SHA-256 hash"""
    return sha256(sha256(unhexlify(string)).digest()).digest()


def base58_check_encode(version, payload):
    """Encode with base58 check"""
    string = f"{version:02x}{payload}"
    checksum = double_sha256(string)[:4]
    return base58_encode(string + hexlify(checksum).decode("ascii"))


def gph_base58_check_encode(string):
    """Graphene-specific base58 check encoding"""
    checksum = ripemd160(string)[:4]
    return base58_encode(string + hexlify(checksum).decode("ascii"))


def base58_check_decode(string):
    """Decode base58 with checksum verification"""
    string = unhexlify(base58_decode(string))
    dec = hexlify(string[:-4]).decode("ascii")
    checksum = double_sha256(dec)[:4]
    if string[-4:] != checksum:
        raise ValueError("Checksum verification failed")
    return dec[2:]


def gph_base58_check_decode(string):
    """Graphene-specific base58 check decoding"""
    string = unhexlify(base58_decode(string))
    dec = hexlify(string[:-4]).decode("ascii")
    checksum = ripemd160(dec)[:4]
    if string[-4:] != checksum:
        raise ValueError("Checksum verification failed")
    return dec


class Address:
    """Represents a blockchain address"""

    def __init__(self, address=None, pubkey=None, prefix=PREFIX):
        self.prefix = prefix
        self.pubkey = Base58(pubkey, prefix=prefix)
        self._address = address


class PublicKey:
    """Handles public key operations"""

    def __init__(self, pk, prefix=PREFIX):
        self.prefix = prefix
        self._pk = Base58(pk, prefix=prefix)
        self.address = Address(pubkey=pk, prefix=prefix)
        self.pubkey = self._pk

    def derive_y_from_x(self, xxx, is_even):
        """Derive y-coordinate from x-coordinate"""
        curve = ecdsa_SECP256k1.curve
        aaa, bbb, ppp = curve.a(), curve.b(), curve.p()
        alpha = (pow(xxx, 3, ppp) + aaa * xxx + bbb) % ppp
        beta = ecdsa_numbertheory.square_root_mod_prime(alpha, ppp)
        if (beta % 2) == is_even:
            beta = ppp - beta
        return beta

    def compressed(self):
        """Generate compressed public key"""
        order = ecdsa_SECP256k1.generator.order()
        point = ecdsa_VerifyingKey.from_string(
            bytes(self), curve=ecdsa_SECP256k1
        ).pubkey.point
        x_str = ecdsa_util.number_to_string(point.x(), order)
        return hexlify(bytes(chr(2 + (point.y() & 1)), "ascii") + x_str).decode("ascii")

    def un_compressed(self):
        """Generate uncompressed public key"""
        public_key = repr(self._pk)
        prefix = public_key[0:2]
        if prefix == "04":
            return public_key
        if prefix not in ["02", "03"]:
            raise ValueError("Invalid public key prefix")

        xxx = int(public_key[2:], 16)
        yyy = self.derive_y_from_x(xxx, prefix == "02")
        return f"04{xxx:064x}{yyy:064x}"

    def point(self):
        """Get ECDSA point representation"""
        string = unhexlify(self.un_compressed())
        return ecdsa_VerifyingKey.from_string(
            string[1:], curve=ecdsa_SECP256k1
        ).pubkey.point

    def __repr__(self):
        """Return hex representation"""
        return repr(self._pk)

    def __format__(self, _format):
        """Format the public key"""
        return format(self._pk, _format)

    def __bytes__(self):
        """Return raw bytes (33 bytes)"""
        return bytes(self._pk)


class PrivateKey:
    """Handles private key operations and public key derivation"""

    def __init__(self, wif=None, prefix=PREFIX):
        self._wif = wif if isinstance(wif, Base58) else Base58(wif)
        self._pubkeyhex, self._pubkeyuncompressedhex = self.compressed_pubkey()
        self.pubkey = PublicKey(self._pubkeyhex, prefix=prefix)
        self.uncompressed = PublicKey(self._pubkeyuncompressedhex, prefix=prefix)
        self.uncompressed.address = Address(
            pubkey=self._pubkeyuncompressedhex, prefix=prefix
        )
        self.address = Address(pubkey=self._pubkeyhex, prefix=prefix)

    def compressed_pubkey(self):
        """Derive compressed and uncompressed public keys"""
        secret = unhexlify(repr(self._wif))
        order = ecdsa_SigningKey.from_string(
            secret, curve=ecdsa_SECP256k1
        ).curve.generator.order()
        point = ecdsa_SigningKey.from_string(
            secret, curve=ecdsa_SECP256k1
        ).verifying_key.pubkey.point
        x_str = ecdsa_util.number_to_string(point.x(), order)
        y_str = ecdsa_util.number_to_string(point.y(), order)

        compressed = hexlify(chr(2 + (point.y() & 1)).encode("ascii") + x_str).decode(
            "ascii"
        )
        uncompressed = hexlify(chr(4).encode("ascii") + x_str + y_str).decode("ascii")
        return [compressed, uncompressed]

    def __bytes__(self):
        """Return raw private key bytes"""
        return bytes(self._wif)
