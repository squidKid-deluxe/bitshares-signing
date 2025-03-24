r"""
graphene_signing.py

  ____  _ _   ____  _                         
 | __ )(_) |_/ ___|| |__   __ _ _ __ ___  ___ 
 |  _ \| | __\___ \| '_ \ / _` | '__/ _ \/ __|
 | |_) | | |_ ___) | | | | (_| | | |  __/\__ \
 |____/|_|\__|____/|_| |_|\__,_|_|  \___||___/
       ____  _             _                  
      / ___|(_) __ _ _ __ (_)_ __   __ _      
      \___ \| |/ _` | '_ \| | '_ \ / _` |     
       ___) | | (_| | | | | | | | | (_| |     
      |____/|_|\__, |_| |_|_|_| |_|\__, |     
               |___/               |___/   


WTFPL litepresence.com Dec 2021 & squidKid-deluxe Jan 2024

Graphene types and signing function required to authenticate operation being broadcast to BitShares

"""
# DISABLE SELECT PYLINT TESTS

# STANDARD PYTHON MODULES
from binascii import hexlify  # binary text to hexidecimal
from binascii import unhexlify  # hexidecimal to binary text
from hashlib import new as hashlib_new  # access algorithm library
from hashlib import sha256  # message digest algorithm
from json import dumps as json_dumps  # serialize object to string
from json import loads as json_loads  # deserialize string to object
from struct import pack  # convert to string representation of C struct

# GRAPHENE SIGNING MODULES
from bitshares_signing.config import ID, PREFIX
# if there was ever a use for "import *"...
from bitshares_signing.operations import (Asset, Asset_claim_pool,
                                          Asset_create, Asset_publish_feed,
                                          Asset_reserve,
                                          Asset_update_feed_producers,
                                          AssetOptions, BitAssetOptions,
                                          Call_order_update,
                                          CallOrderExtension, GrapheneObject,
                                          Limit_order_cancel,
                                          Limit_order_create,
                                          Liquidity_pool_create,
                                          Liquidity_pool_deposit,
                                          Liquidity_pool_exchange, Price,
                                          PriceFeed)
from bitshares_signing.rpc import rpc_get_transaction_hex
from bitshares_signing.types import (Array, Bytes, Id, ObjectId, Optional,
                                     PointInTime, Signature, Uint16, Uint32,
                                     Uint64, varint)
from bitshares_signing.utilities import from_iso_date, it
# THIRD PARTY MODULES
from ecdsa import SECP256k1 as ecdsa_SECP256k1  # curve
from ecdsa import SigningKey as ecdsa_SigningKey  # class
from ecdsa import VerifyingKey as ecdsa_VerifyingKey  # class
from ecdsa import numbertheory as ecdsa_numbertheory  # largest import
from ecdsa import util as ecdsa_util  # module
from secp256k1 import PrivateKey as secp256k1_PrivateKey  # class
from secp256k1 import PublicKey as secp256k1_PublicKey  # class
from secp256k1 import ffi as secp256k1_ffi  # compiled ffi object
from secp256k1 import lib as secp256k1_lib  # library

# GLOBAL CONSTANTS
# base58 encoding and decoding
# this is alphabet defined minus similar characters like 0 and O:
BASE58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
# hex encoding and decoding
HEXDIGITS = "0123456789abcdefABCDEF"
ALL_FLAGS = (
    secp256k1_lib.SECP256K1_CONTEXT_VERIFY | secp256k1_lib.SECP256K1_CONTEXT_SIGN
)


# BASE 58 ENCODE, DECODE, AND CHECK "  # graphenebase/base58.py
class Base58:
    """
    This class serves as an abstraction layer
    to deal with base58 encoded strings
    and their corresponding hex and binary representation
    """

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
        assert _format.upper() == PREFIX
        return _format.upper() + str(self)

    def __repr__(self):  # hex string of data
        return self._hex

    def __str__(self):  # base58 string of data
        return gph_base58_check_encode(self._hex)

    def __bytes__(self):  # raw bytes of data
        return unhexlify(self._hex)


def base58_decode(base58_str):
    """
    #
    """
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
    """
    #
    """
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
    """
    160-bit cryptographic hash function
    """
    r160 = hashlib_new("ripemd160")  # import the library
    r160.update(unhexlify(string))
    return r160.digest()


def double_sha256(string):
    """
    double sha256 cryptographic hash function
    """
    return sha256(sha256(unhexlify(string)).digest()).digest()


def base58_check_encode(version, payload):
    """
    #
    """
    string = ("%.2x" % version) + payload
    checksum = double_sha256(string)[:4]
    return base58_encode(string + hexlify(checksum).decode("ascii"))


def gph_base58_check_encode(string):
    """
    #
    """
    checksum = ripemd160(string)[:4]
    return base58_encode(string + hexlify(checksum).decode("ascii"))


def base58_check_decode(string):
    """
    #
    """
    string = unhexlify(base58_decode(string))
    dec = hexlify(string[:-4]).decode("ascii")
    checksum = double_sha256(dec)[:4]
    assert string[-4:] == checksum
    return dec[2:]


def gph_base58_check_decode(string):
    """
    #
    """
    string = unhexlify(base58_decode(string))
    dec = hexlify(string[:-4]).decode("ascii")
    checksum = ripemd160(dec)[:4]
    assert string[-4:] == checksum
    return dec


# ADDRESS AND KEYS
class Address:
    """
    # cropped litepresence2019
    Example :: Address("BTSFN9r6VYzBK8EKtMewfNbfiGCr56pHDBFi")
    # graphenebase/account.py
    """

    def __init__(self, address=None, pubkey=None, prefix=PREFIX):
        self.prefix = prefix
        self.pubkey = Base58(pubkey, prefix=prefix)
        self._address = address


class PublicKey:
    """
    # graphenebase/account.py
    This class deals with Public Keys and inherits ``Address``.
    :param str pk: Base58 encoded public key
    :param str prefix: Network prefix (defaults to ``BTS``)
    """

    def __init__(self, pk, prefix=PREFIX):
        self.prefix = prefix
        self._pk = Base58(pk, prefix=prefix)
        self.address = Address(pubkey=pk, prefix=prefix)
        self.pubkey = self._pk

    def derive_y_from_x(self, xxx, is_even):
        """
        Derive yyy point from xxx point:
        e: yyy^2 = xxx^3 + ax + bbb mod ppp
        """
        curve = ecdsa_SECP256k1.curve
        aaa, bbb, ppp = curve.a(), curve.b(), curve.p()
        alpha = (pow(xxx, 3, ppp) + aaa * xxx + bbb) % ppp
        beta = ecdsa_numbertheory.square_root_mod_prime(alpha, ppp)
        if (beta % 2) == is_even:
            beta = ppp - beta
        return beta

    def compressed(self):
        """
        Derive compressed public key
        """
        order = ecdsa_SECP256k1.generator.order()
        point = ecdsa_VerifyingKey.from_string(
            bytes(self), curve=ecdsa_SECP256k1
        ).pubkey.point
        x_str = ecdsa_util.number_to_string(point.x(), order)
        # y_str = ecdsa_util.number_to_string(point.y(), order)
        compressed = hexlify(bytes(chr(2 + (point.y() & 1)), "ascii") + x_str).decode(
            "ascii"
        )
        return compressed

    def un_compressed(self):
        """
        Derive uncompressed key
        """
        public_key = repr(self._pk)
        prefix = public_key[0:2]
        if prefix == "04":
            return public_key
        assert prefix in ["02", "03"]
        xxx = int(public_key[2:], 16)
        yyy = self.derive_y_from_x(xxx, (prefix == "02"))
        return "04" + "%064x" % xxx + "%064x" % yyy

    def point(self):
        """
        Return the point for the public key
        """
        string = unhexlify(self.un_compressed())
        return ecdsa_VerifyingKey.from_string(
            string[1:], curve=ecdsa_SECP256k1
        ).pubkey.point

    def __repr__(self):
        """
        Gives the hex representation of the Graphene public key.
        """
        return repr(self._pk)

    def __format__(self, _format):
        """
        Formats the instance of:doc:`Base58 <base58>
        ` according to ``_format``
        """
        return format(self._pk, _format)

    def __bytes__(self):
        """
        Returns the raw public key (has length 33)
        """
        return bytes(self._pk)


class PrivateKey:
    """
    Derives the compressed and uncompressed public keys and
    constructs two instances of ``PublicKey``:
    # Bitshares(MIT) graphenebase/account.py
    # Bitshares(MIT) bitsharesbase/account.py
    # merged litepresence2019
    """

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
        """
        Derive uncompressed public key
        """
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
        """
        Returns the raw private key
        """
        return bytes(self._wif)


class Memo(GrapheneObject):
    def _prepare_data(self, kwargs):
        prefix = kwargs.pop("prefix", PREFIX)
        if "message" in kwargs and kwargs["message"]:
            return {
                "from": PublicKey(kwargs["from"], prefix=prefix),
                "to": PublicKey(kwargs["to"], prefix=prefix),
                "nonce": Uint64(int(kwargs["nonce"])),
                "message": Bytes(kwargs["message"]),
            }
        else:
            return None


class Transfer(GrapheneObject):
    def _prepare_data(self, kwargs):
        prefix = kwargs.get("prefix", PREFIX)
        if "memo" in kwargs and kwargs["memo"]:
            if isinstance(kwargs["memo"], dict):
                kwargs["memo"]["prefix"] = prefix
                memo = Optional(Memo(**kwargs["memo"]))
            else:
                memo = Optional(Memo(kwargs["memo"]))
        else:
            memo = Optional(None)
        return {
            "fee": Asset(kwargs["fee"]),
            "from": ObjectId(kwargs["from"], "account"),
            "to": ObjectId(kwargs["to"], "account"),
            "amount": Asset(kwargs["amount"]),
            "memo": memo,
            "extensions": Array([]),
        }


class Asset_issue(GrapheneObject):
    def _prepare_data(self, kwargs):
        prefix = kwargs.get("prefix", PREFIX)
        if "memo" in kwargs and kwargs["memo"]:
            memo = Optional(Memo(prefix=prefix, **kwargs["memo"]))  # FIXME
        else:
            memo = Optional(None)
        return {
            "fee": Asset(kwargs["fee"]),
            "issuer": ObjectId(kwargs["issuer"], "account"),
            "asset_to_issue": Asset(kwargs["asset_to_issue"]),
            "issue_to_account": ObjectId(kwargs["issue_to_account"], "account"),
            "memo": memo,
            "extensions": Array([]),
        }


class Operation:  # refactored  litepresence2019
    "class GPHOperation():"
    # Bitshares(MIT) graphenebase/objects.py
    "class Operation(GPHOperation):"
    # Bitshares(MIT) bitsharesbase/objects.py

    def __init__(self, op):
        if not isinstance(op, list):
            raise ValueError("expecting op to be a list")
        if len(op) != 2:
            raise ValueError("expecting op to be two items")
        if not isinstance(op[0], int):
            raise ValueError("expecting op[0] to be integer")

        self.opId = op[0]

        # Define a mapping of operation codes to their corresponding classes
        operation_map = {
            0: Transfer,
            1: Limit_order_create,
            2: Limit_order_cancel,
            3: Call_order_update,
            10: Asset_create,
            13: Asset_update_feed_producers,
            14: Asset_issue,
            15: Asset_reserve,
            19: Asset_publish_feed,
            47: Asset_claim_pool,
            59: Liquidity_pool_create,
            61: Liquidity_pool_deposit,
            63: Liquidity_pool_exchange,
        }

        # Use the mapping to set self.op
        if op[0] in operation_map:
            self.op = operation_map[op[0]](op[1])
        else:
            raise ValueError(f"Invalid operation code: {op[0]}")

    def __bytes__(self):
        print(it("yellow", "GPHOperation.__bytes__"))
        return bytes(Id(self.opId)) + bytes(self.op)


class SignedTransaction(GrapheneObject):  # merged litepresence2019
    # Bitshares(MIT) graphenebase/signedtransactions.py
    # Bitshares(MIT) bitsharesbase/signedtransactions.py

    def _prepare_data(self, kwargs):
        print(it("red", "SignedTransaction"))
        print(
            """ Create a signed transaction and
                    offer method to create the signature

                (see ``getBlockParams``)
                :param num refNum: parameter ref_block_num
                :param num refPrefix: parameter ref_block_prefix
                :param str expiration: expiration date
                :param Array operations:  array of operations
            """
        )
        print("kwargs", kwargs)
        if (
            "extensions" not in kwargs
            or "extensions" in kwargs
            and not kwargs.get("extensions")
        ):
            kwargs["extensions"] = Array([])
        if "signatures" not in kwargs:
            kwargs["signatures"] = Array([])
        else:
            kwargs["signatures"] = Array(
                [Signature(unhexlify(a)) for a in kwargs["signatures"]]
            )

        if "operations" in kwargs:
            opklass = self.getOperationKlass()
            if all(not isinstance(a, opklass) for a in kwargs["operations"]):
                kwargs["operations"] = Array([opklass(a) for a in kwargs["operations"]])
            else:
                kwargs["operations"] = Array(kwargs["operations"])

        return {
                "ref_block_num": Uint16(kwargs["ref_block_num"]),
                "ref_block_prefix": Uint32(kwargs["ref_block_prefix"]),
                "expiration": PointInTime(kwargs["expiration"]),
                "operations": kwargs["operations"],
                "extensions": kwargs["extensions"],
                "signatures": kwargs["signatures"],
            }

    @property
    def id(self):
        print("SignedTransaction.id")
        """
        The transaction id of this transaction
        """
        # Store signatures temporarily
        sigs = self.data["signatures"]
        self.data.pop("signatures", None)
        # Generage Hash of the seriliazed version
        h = sha256(bytes(self)).digest()
        # Recover signatures
        self.data["signatures"] = sigs
        # Return properly truncated tx hash
        return hexlify(h[:20]).decode("ascii")

    def getOperationKlass(self):
        print("SignedTransaction.get_operationKlass")
        return Operation

    # FIXME ded code?
    # def derSigToHexSig(self, s):
    #     print("SignedTransaction.derSigToHexSig")
    #     s, junk = ecdsa_der.remove_sequence(unhexlify(s))
    #     if junk:
    #         print("JUNK: %s", hexlify(junk).decode("ascii"))
    #     assert junk == b""
    #     x, s = ecdsa_der.remove_integer(s)
    #     y, s = ecdsa_der.remove_integer(s)
    #     return "%064x%064x" % (x, y)

    def derive_digest(self, chain):
        print("SignedTransaction.derive_digest")
        print(self, chain)
        # Do not serialize signatures
        sigs = self.data["signatures"]
        self.data["signatures"] = []
        # Get message to sign
        #   bytes(self) will give the wire formated data according to
        #   GrapheneObject and the data given in __init__()
        self.message = unhexlify(ID) + bytes(self)
        self.digest = sha256(self.message).digest()
        # restore signatures
        self.data["signatures"] = sigs

    def verify(self, pubkeys=[], chain=PREFIX):
        print(it("green", "###############################################"))
        print("SignedTransaction.verify")
        print(it("green", "self, pubkeys, chain"), self, pubkeys, chain)

        self.derive_digest(chain)
        print(it("green", "self"))
        print(self)
        signatures = self.data["signatures"].data
        print(it("green", "signatures"))
        print(signatures)
        pubKeysFound = []

        for signature in signatures:
            p = verify_message(self.message, bytes(signature))
            phex = hexlify(p).decode("ascii")
            print("")
            print("")
            print(it("green", "phex"))
            print(it("green", phex))
            print(it("cyan", "len(phex)"), len(str(phex)))
            print("")
            print("")
            pubKeysFound.append(phex)

        for pubkey in pubkeys:
            print(it("green", "for pubkey in pubkeys:"))
            print(it("green", "************ pubkey ************"))
            print(it("blue", "repr(pubkey)"))
            print(repr(pubkey))

            print(it("cyan", "len(pubkey)"), len(str(pubkey)))
            print("")
            if not isinstance(pubkey, PublicKey):
                raise Exception("Pubkeys must be array of 'PublicKey'")

            k = pubkey.un_compressed()[2:]

            print(it("green", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"))
            print(it("yellow", "k"))
            print(k)
            print(it("cyan", "len(k)"), len(str(k)))
            print(it("yellow", "pubKeysFound"))
            print(pubKeysFound)
            print(it("cyan", "len(pubKeysFound[0])"), len(pubKeysFound[0]))
            print("")
            print(it("green", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"))

            # if k not in pubKeysFound and repr(pubkey) not in pubKeysFound:
            #     print(
            #         it(
            #             "blue",
            #             "if k not in pubKeysFound and repr(pubkey) "
            #             + "not in pubKeysFound:",
            #         )
            #     )
            #     k = PublicKey(PublicKey(k).compressed())
            #     f = format(k, PREFIX)  # chain_params["prefix"]) # 'BTS'
            #     print("")
            #     print(it("red", "FIXME"))
            #     raise Exception("Signature for %s missing!" % f)

        return pubKeysFound

    # FIXME: ded code?
    # def sign(self, wifkeys, chain=PREFIX):
    #     print("SignedTransaction.sign")
    #     """
    #     Sign the transaction with the provided private keys.
    #     """
    #     # FIXME is this even used????
    #     self.derive_digest(chain)

    #     # Get Unique private keys
    #     self.privkeys = []
    #     [self.privkeys.append(item) for item in wifkeys if item not in self.privkeys]

    #     # Sign the message with every private key given!
    #     sigs = []
    #     for wif in self.privkeys:
    #         signature = sign_message(self.message, wif)
    #         sigs.append(Signature(signature))

    #     self.data["signatures"] = Array(sigs)
    #     return self


# SERIALIZATION


def serialize_transaction(rpc, trx):
    """
    {"method":"call","params":[
        2,
        "get_required_signatures",
            [{"ref_block_num":0,
            "ref_block_prefix":0,
            "expiration":"1970-01-01T00:00:00",
            "operations":
                [[3,{
                "fee":{"amount":"48260","asset_id":"1.3.0"},
                "funding_account":"1.2.11111111",
                "delta_collateral":{"amount":"1","asset_id":"1.3.5650"},
                "delta_debt":{"amount":"0","asset_id":"1.3.5662"},
                "extensions":{"target_collateral_ratio":2000}}]],
                "extensions":[],"signatures":[]},
                ["BTS6upQe7upQe7upQe7upQe7upQe7upQe7upQe7upQe7upQe7upQe7"]]],
            "id":371}
    """
    if trx["operations"] == []:
        return trx, b""
    # gist.github.com/xeroc/9bda11add796b603d83eb4b41d38532b
    # RPC call for ordered dicts which are dumped by the query
    tx_ops = trx["operations"]
    for idx, _ in enumerate(tx_ops):
        if "memo" in tx_ops[idx][1].keys() and tx_ops[idx][1]["memo"] == "":
            tx_ops[idx][1] = {k: v for k, v in tx_ops[idx][1].items() if k != "memo"}
    rpc_tx = dict(trx)
    rpc_tx["operations"] = tx_ops
    # find out how the backend suggests to serialize the trx
    rpc_tx_hex = rpc_get_transaction_hex(rpc, json_loads(json_dumps(rpc_tx)))
    buf = b""  # create an empty byte string buffer
    # add block number, prefix, and trx expiration to the buffer
    buf += pack("<H", trx["ref_block_num"])  # 2 byte int
    buf += pack("<I", trx["ref_block_prefix"])  # 4 byte int
    buf += pack("<I", from_iso_date(trx["expiration"]))  # 4 byte int
    # add length of operations list to buffer
    buf += bytes(varint(len(trx["operations"])))
    # add the operations list to the buffer in graphene type fashion
    for op in trx["operations"]:
        # print(ops[0])  # Int (1=create, 2=cancel, etc.)
        # print(ops[1])  # OrderedDict of operations
        buf += varint(op[0])
        if op[0] == 0:
            buf += bytes(Transfer(op[1]))
        elif op[0] == 1:
            buf += bytes(Limit_order_create(op[1]))
        elif op[0] == 2:
            buf += bytes(Limit_order_cancel(op[1]))
        elif op[0] == 3:
            buf += bytes(Call_order_update(op[1]))
            buf += bytes(varint(0))
        elif op[0] == 10:
            buf += bytes(Asset_create(op[1]))
        elif op[0] == 13:
            buf += bytes(Asset_update_feed_producers(op[1]))
        elif op[0] == 14:
            buf += bytes(Asset_issue(op[1]))
        elif op[0] == 15:
            buf += bytes(Asset_reserve(op[1]))
        elif op[0] == 19:
            buf += bytes(Asset_publish_feed(op[1]))
        elif op[0] == 47:
            buf += bytes(Asset_claim_pool(op[1]))
        elif op[0] == 59:
            buf += bytes(Liquidity_pool_create(op[1]))
        elif op[0] == 61:
            buf += bytes(Liquidity_pool_deposit(op[1]))
        elif op[0] == 63:
            buf += bytes(Liquidity_pool_exchange(op[1]))
    # add legth of (empty) extensions list to buffer
    buf += bytes(varint(len(trx["extensions"])))  # usually, effectively varint(0)
    # this the final manual transaction hex, which should match rpc
    manual_tx_hex = hexlify(buf)
    # prepend the chain ID to the buffer to create final serialized msg
    message = unhexlify(ID) + buf
    # if serialization is correct: rpc_tx_hex = manual_tx_hex plus an empty signature
    assert rpc_tx_hex == manual_tx_hex + b"00", "Serialization Failed"
    return trx, message


def sign_transaction(trx, message, wif):
    """
    # graphenebase/ecdsa.py
    # tools.ietf.org/html/rfc6979
    # @xeroc/steem-transaction-signing-in-a-nutshell
    # @dantheman/steem-and-bitshares-cryptographic-security-update
    # deterministic signatures retain the cryptographic
    # security features associated with digital signatures
    # but can be more easily implemented
    # since they do not need high-quality randomness
    """

    def canonical(sig):
        """
        1 in 4 signatures are randomly canonical; "normal form"
        using the other three causes vulnerability to maleability attacks
        as a metaphor; "require reduced fractions in simplest terms"
        note: 0x80 hex = 10000000 binary = 128 integer
        :return bool():
        """
        sig = bytearray(sig)
        return not any(
            [
                int(sig[0]) & 0x80,
                int(sig[32]) & 0x80,
                sig[0] == 0 and not int(sig[1]) & 0x80,
                sig[32] == 0 and not int(sig[33]) & 0x80,
            ]
        )

    # create fixed length representation of arbitrary length data
    # this will thoroughly obfuscate and compress the transaction
    # signing large data is computationally expensive and time consuming
    # the hash of the data is a relatively small
    # signing hash is more efficient than signing serialization
    digest = sha256(message).digest()
    # ECDSA
    # eliptical curve digital signature algorithm
    # this is where the real hocus pocus lies
    # all of the ordering, typing, serializing, and digesting
    # culminates with the message meeting the wif
    # begin with the 8 bit string representation of private key
    try:
        private_key = bytes(PrivateKey(wif))
    except:
        return
    # create some arbitrary data used by the nonce generation
    ndata = secp256k1_ffi.new("const int *ndata")
    ndata[0] = 0  # it adds "\0x00", then "\0x00\0x00", etc..
    while True:  # repeat process until deterministic and cannonical
        ndata[0] += 1  # increment the arbitrary nonce
        # obtain compiled/binary private key from the wif
        privkey = secp256k1_PrivateKey(private_key, raw=True)
        # create a new recoverable 65 byte ECDSA signature
        sig = secp256k1_ffi.new("secp256k1_ecdsa_recoverable_signature *")
        # parse a compact ECDSA signature (64 bytes + recovery id)
        # returns: 1 = deterministic; 0 = not deterministic
        deterministic = secp256k1_lib.secp256k1_ecdsa_sign_recoverable(
            privkey.ctx,  # initialized context object
            sig,  # array where signature is held
            digest,  # 32-byte message hash being signed
            privkey.private_key,  # 32-byte secret key
            secp256k1_ffi.NULL,  # default nonce function
            ndata,  # incrementing nonce data
        )
        if not deterministic:
            continue
        # we derive the recovery parameter
        # which simplifies the verification of the signature
        # it links the signature to a single unique public key
        # without this parameter, the back-end would need to test
        # for multiple public keys instead of just one
        signature, i = privkey.ecdsa_recoverable_serialize(sig)
        # we ensure that the signature is canonical; simplest/reduced form
        if canonical(signature):
            # add 4 and 27 to stay compatible with other protocols
            i += 4  # compressed
            i += 27  # compact
            # and have now obtained our signature
            break
    # having derived a valid canonical signature
    # we format it in its hexadecimal representation
    # and add it our transactions signatures
    # note that we do not only add the signature
    # but also the recover parameter
    # this kind of signature is then called "compact signature"
    signature = hexlify(pack("<B", i) + signature).decode("ascii")
    trx["signatures"].append(signature)
    return trx


def verify_transaction(trx, wif):
    """
    # gist.github.com/xeroc/9bda11add796b603d83eb4b41d38532b
    # once you have derived your new trx including the signatures
    # verify your transaction and it's signature
    """
    tx2 = SignedTransaction(**trx)
    tx2.derive_digest(PREFIX)
    pubkeys = [PrivateKey(wif).pubkey]
    tx2.verify(pubkeys, PREFIX)
    return trx


def verify_message(message, signature):
    """
    graphenebase/ecdsa.py stripped of non-secp256k1 methods
    returns bytes
    """
    # require message and signature to be bytes
    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")
    if not isinstance(signature, bytes):
        signature = bytes(signature, "utf-8")
    # recover parameter only
    recover_parameter = bytearray(signature)[0] - 4 - 27
    # "bitwise or"; each bit of the output is 0
    # if the corresponding bit of x AND of y is 0, otherwise it's 1

    # ecdsa.PublicKey with additional functions to serialize
    # in uncompressed and compressed formats
    pub = secp256k1_PublicKey(flags=ALL_FLAGS)
    # recover raw signature
    sig = pub.ecdsa_recoverable_deserialize(signature[1:], recover_parameter)
    # recover public key
    verify_pub = secp256k1_PublicKey(pub.ecdsa_recover(message, sig))
    # convert recoverable sig to normal sig
    normal_sig = verify_pub.ecdsa_recoverable_convert(sig)
    # verify
    verify_pub.ecdsa_verify(message, normal_sig)
    ret = verify_pub.serialize(compressed=True)
    return ret
