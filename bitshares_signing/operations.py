from .base58 import PublicKey
from .config import PREFIX
from .types import (Array, Bytes, Extension, Int64, ObjectId, Optional,
                    PointInTime, String, Uint8, Uint16, Uint32, Uint64)


def is_args_this_class(self, args):
    """
    graphenebase/objects.py
    True if there is only one argument
    and its type name is the same as the type name of self
    """
    return len(args) == 1 and type(args[0]).__name__ == type(self).__name__


# SERIALIZATION OBJECTS
class GrapheneObject:
    def __init__(self, *args, **kwargs):
        if is_args_this_class(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            self.data = self._prepare_data(kwargs)

    def _prepare_data(self, kwargs):
        """To be implemented by subclasses. Preprocess kwargs and return the data dict."""
        raise NotImplementedError("Subclasses must implement _prepare_data")

    def __bytes__(self):
        # encodes data into wire format
        if self.data is None:
            return bytes()
        b = b""
        # data is a dictionary for human readable reasons
        # but is treated as an ordered list of values
        for value in self.data.values():
            b += bytes(value, "utf-8") if isinstance(value, str) else bytes(value)
        return b


class Price(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {"base": Asset(kwargs["base"]), "quote": Asset(kwargs["quote"])}


class Asset(GrapheneObject):  # bitsharesbase/objects.py
    def _prepare_data(self, kwargs):
        return {
            "amount": Int64(kwargs["amount"]),
            "asset_id": ObjectId(kwargs["asset_id"], "asset"),
        }

class Memo(GrapheneObject):
    """Memo object for transactions"""

    def _prepare_data(self, kwargs):
        prefix = kwargs.pop("prefix", PREFIX)
        if "message" in kwargs and kwargs["message"]:
            return {
                "from": PublicKey(kwargs["from"], prefix=prefix),
                "to": PublicKey(kwargs["to"], prefix=prefix),
                "nonce": Uint64(int(kwargs["nonce"])),
                "message": Bytes(kwargs["message"]),
            }
        return None


class Transfer(GrapheneObject):
    """Transfer operation object"""

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
    """Asset issuance operation object"""

    def _prepare_data(self, kwargs):
        prefix = kwargs.get("prefix", PREFIX)
        if "memo" in kwargs and kwargs["memo"]:
            memo = Optional(Memo(prefix=prefix, **kwargs["memo"]))
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


class PriceFeed(GrapheneObject):
    """
    bitsharesbase/objects.py
    """

    def _prepare_data(self, kwargs):
        return {
            "settlement_price": Price(kwargs["settlement_price"]),
            "maintenance_collateral_ratio": Uint16(
                kwargs["maintenance_collateral_ratio"]
            ),
            "maximum_short_squeeze_ratio": Uint16(
                kwargs["maximum_short_squeeze_ratio"]
            ),
            "core_exchange_rate": Price(kwargs["core_exchange_rate"]),
        }


class Asset_create(GrapheneObject):
    def _prepare_data(self, kwargs):
        if kwargs.get("bitasset_opts"):
            bitasset_opts = Optional(BitAssetOptions(kwargs["bitasset_opts"]))
        else:
            bitasset_opts = Optional(None)
        return {
            "fee": Asset(kwargs["fee"]),
            "issuer": ObjectId(kwargs["issuer"], "account"),
            "symbol": String(kwargs["symbol"]),
            "precision": Uint8(kwargs["precision"]),
            "common_options": AssetOptions(kwargs["common_options"]),
            "bitasset_opts": bitasset_opts,
            "is_prediction_market": Uint8(bool(kwargs["is_prediction_market"])),
            "extensions": Array([]),
        }


class AssetOptions(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {
            "max_supply": Int64(kwargs["max_supply"]),
            "market_fee_percent": Uint16(kwargs["market_fee_percent"]),
            "max_market_fee": Int64(kwargs["max_market_fee"]),
            "issuer_permissions": Uint16(kwargs["issuer_permissions"]),
            "flags": Uint16(kwargs["flags"]),
            "core_exchange_rate": Price(kwargs["core_exchange_rate"]),
            "whitelist_authorities": Array(
                [ObjectId(x, "account") for x in kwargs["whitelist_authorities"]]
            ),
            "blacklist_authorities": Array(
                [ObjectId(x, "account") for x in kwargs["blacklist_authorities"]]
            ),
            "whitelist_markets": Array(
                [ObjectId(x, "asset") for x in kwargs["whitelist_markets"]]
            ),
            "blacklist_markets": Array(
                [ObjectId(x, "asset") for x in kwargs["blacklist_markets"]]
            ),
            "description": String(kwargs["description"]),
            "extensions": Array([]),
        }


class Asset_reserve(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "payer": ObjectId(kwargs["payer"], "account"),
            "amount_to_reserve": Asset(kwargs["amount_to_reserve"]),
            "extensions": Array([]),
        }


class BitAssetOptions(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {
            "feed_lifetime_sec": Uint32(kwargs["feed_lifetime_sec"]),
            "minimum_feeds": Uint8(kwargs["minimum_feeds"]),
            "force_settlement_delay_sec": Uint32(kwargs["force_settlement_delay_sec"]),
            "force_settlement_offset_percent": Uint16(
                kwargs["force_settlement_offset_percent"]
            ),
            "maximum_force_settlement_volume": Uint16(
                kwargs["maximum_force_settlement_volume"]
            ),
            "short_backing_asset": ObjectId(kwargs["short_backing_asset"], "asset"),
            "extensions": Array([]),
        }


class Asset_claim_pool(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "issuer": ObjectId(kwargs["issuer"], "account"),
            "asset_id": ObjectId(kwargs["asset_id"], "asset"),
            "amount_to_claim": Asset(kwargs["amount_to_claim"]),
            "extensions": Array([]),
        }


class Call_order_update(GrapheneObject):
    """
    /bitsharesbase/operations.py
    """

    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "funding_account": ObjectId(kwargs["funding_account"], "account"),
            "delta_collateral": Asset(kwargs["delta_collateral"]),
            "delta_debt": Asset(kwargs["delta_debt"]),
            "extensions": CallOrderExtension(kwargs["extensions"]),
        }


class Limit_order_create(GrapheneObject):  # bitsharesbase/operations.py
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "seller": ObjectId(kwargs["seller"], "account"),
            "amount_to_sell": Asset(kwargs["amount_to_sell"]),
            "min_to_receive": Asset(kwargs["min_to_receive"]),
            "expiration": PointInTime(kwargs["expiration"]),
            "fill_or_kill": Uint8(kwargs["fill_or_kill"]),
            "extensions": Array([]),
        }


class Limit_order_cancel(GrapheneObject):  # bitsharesbase/operations.py
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "fee_paying_account": ObjectId(kwargs["fee_paying_account"], "account"),
            "order": ObjectId(kwargs["order"], "limit_order"),
            "extensions": Array([]),
        }


class CallOrderExtension(Extension):
    """
    /bitsharesbase/objects.py
    """

    # FIXME this "should" have self as first arg but pybitshares does it like this
    def tcr(value):
        if value:
            return Uint16(value)
        else:
            return Optional(None)

    sorted_options = [("target_collateral_ratio", tcr)]


class Asset_publish_feed(GrapheneObject):
    """
    bitsharesbase/operations.py
    """

    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "publisher": ObjectId(kwargs["publisher"], "account"),
            "asset_id": ObjectId(kwargs["asset_id"], "asset"),
            "feed": PriceFeed(kwargs["feed"]),
            "extensions": Array([]),
        }


class Liquidity_pool_create(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "account": ObjectId(kwargs["account"], "account"),
            "asset_a": ObjectId(kwargs["asset_a"], "asset"),
            "asset_b": ObjectId(kwargs["asset_b"], "asset"),
            "share_asset": ObjectId(kwargs["share_asset"], "asset"),
            "taker_fee_percent": Uint16(kwargs["taker_fee_percent"]),
            "withdrawal_fee_percent": Uint16(kwargs["withdrawal_fee_percent"]),
            "extensions": Array([]),
        }


class Liquidity_pool_deposit(GrapheneObject):
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "account": ObjectId(kwargs["account"], "account"),
            "pool": ObjectId(kwargs["pool"], "liquidity_pool"),
            "amount_a": Asset(kwargs["amount_a"]),
            "amount_b": Asset(kwargs["amount_b"]),
            "extensions": Array([]),
        }


class Liquidity_pool_exchange(GrapheneObject):  # bitsharesbase/operations.py
    def _prepare_data(self, kwargs):
        return {
            "fee": Asset(kwargs["fee"]),
            "account": ObjectId(kwargs["account"], "account"),
            "pool": ObjectId(kwargs["pool"], "liquidity_pool"),
            "amount_to_sell": Asset(kwargs["amount_to_sell"]),
            "min_to_receive": Asset(kwargs["min_to_receive"]),
            "extensions": Array([]),
        }


class Asset_update_feed_producers(GrapheneObject):
    """
    bitsharesbase/operations.py
    """

    def _prepare_data(self, kwargs):
        kwargs["new_feed_producers"] = sorted(
            kwargs["new_feed_producers"], key=lambda x: float(x.split(".")[2])
        )
        return {
            "fee": Asset(kwargs["fee"]),
            "issuer": ObjectId(kwargs["issuer"], "account"),
            "asset_to_update": ObjectId(kwargs["asset_to_update"], "asset"),
            "new_feed_producers": Array(
                [ObjectId(o, "account") for o in kwargs["new_feed_producers"]]
            ),
            "extensions": Array([]),
        }
