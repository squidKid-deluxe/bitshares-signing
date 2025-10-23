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
import secp256k1  # Replaced ecdsa with secp256k1

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
        # Create a secp256k1 PublicKey object for internal operations
        self._secp256k1_pubkey = secp256k1.PublicKey(bytes(self), raw=True)

    def compressed(self):
        """Generate compressed public key"""
        # Use secp256k1 to serialize as compressed key
        return self._secp256k1_pubkey.serialize(compressed=True).hex()

    def un_compressed(self):
        """Generate uncompressed public key"""
        # Use secp256k1 to serialize as uncompressed key
        return self._secp256k1_pubkey.serialize(compressed=False).hex()

    def point(self):
        """Get ECDSA point representation"""
        # Get the uncompressed serialization to extract x and y coordinates
        uncompressed = self._secp256k1_pubkey.serialize(compressed=False)
        # The first byte is 0x04 (uncompressed prefix), then 32 bytes x, then 32 bytes y
        x = int.from_bytes(uncompressed[1:33], 'big')
        y = int.from_bytes(uncompressed[33:65], 'big')
        # Return a tuple representing the point (x, y)
        return (x, y)

    def __repr__(self):
        """Return hex representation"""
        return repr(self._pk)

    def __format__(self, _format):
        """Format the public key"""
        return format(self._pk, _format)

    def __bytes__(self):
        """Return raw bytes (33 bytes for compressed)"""
        return bytes(self._pk)


class PrivateKey:
    """Handles private key operations and public key derivation"""

    def __init__(self, wif=None, prefix=PREFIX):
        self._wif = wif if isinstance(wif, Base58) else Base58(wif)
        
        # Decode the WIF to get raw private key bytes
        wif_bytes = unhexlify(base58_check_decode(wif))
        # Skip the prefix (0x80) and get just the private key (32 bytes)
        privkey_bytes = wif_bytes[1:33]
        
        # Create secp256k1 PrivateKey object
        self._secp256k1_privkey = secp256k1.PrivateKey(privkey_bytes, raw=True)
        # Get the corresponding public key
        self._secp256k1_pubkey = self._secp256k1_privkey.pubkey
        
        # Store compressed and uncompressed public keys
        self._pubkeyhex = self._secp256k1_pubkey.serialize(compressed=True).hex()
        self._pubkeyuncompressedhex = self._secp256k1_pubkey.serialize(compressed=False).hex()
        
        self.pubkey = PublicKey(self._pubkeyhex, prefix=prefix)
        self.uncompressed = PublicKey(self._pubkeyuncompressedhex, prefix=prefix)
        self.uncompressed.address = Address(
            pubkey=self._pubkeyuncompressedhex, prefix=prefix
        )
        self.address = Address(pubkey=self._pubkeyhex, prefix=prefix)

    def compressed_pubkey(self):
        """Derive compressed and uncompressed public keys"""
        # Just return the precomputed values
        return [self._pubkeyhex, self._pubkeyuncompressedhex]

    def __bytes__(self):
        """Return raw private key bytes"""
        return bytes(self._wif)
