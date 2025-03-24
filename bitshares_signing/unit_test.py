from getpass import getpass

import bitshares_signing as bts

print("\033c")

user = input("Username: ")
wif = getpass("WIF: ")

order = bts.prototype_order(
    {
        "wif": wif,
        "account_name": user,
        "asset_name": "BTS",
        "currency_name": "HONEST.MONEY",
    },
)


order1 = order.copy()
order1["edicts"] = [{"op": "login"}]


order2 = order.copy()
order2["edicts"] = [
    {"op": "buy", "amount": 1, "price": 1},
    {"op": "sell", "amount": 1, "price": 1},
]


order3 = order.copy()
# add edicts
order3["edicts"] = [
    # cancel - cancel all `ids` or all open orders if `ids` is ["1.7.X"]
    {
        "op": "cancel",
        "ids": ["1.7.X"],
    },
]

order4 = order.copy()
order4["edicts"] = [
    # swap - selling `amount` of `currency` for `assets` at `price` on `pool`
    {
        "op": "swap",
        "amount": 1,
        "price": 1,
        "pool": "1.19.305",
    },
    # deposit_pool - deposit `amount_a` of `asset` and `amount_b` of `currency` into `pool`
    {
        "op": "deposit_pool",
        "amount_a": 1,  # asset
        "amount_b": 1,  # currency
        "pool": "1.19.305",
    },
    # transfer - move `amount` of `asset` to `account_id`
    {
        "op": "transfer",
        "amount": 1,
        "account_id": "1.2.581357",
    },
    # issue - issue `amount` of `asset` to `account_id`
    {
        "op": "issue",
        "amount": 1,
        "account_id": "1.2.581357",
    },
    # reserve - reserve `amount` of `asset`
    {
        "op": "reserve",
        "amount": 1,
    },
    # call - update a call order with a change in debt (`debt_delta`), change in
    #        collateral (`collateral_delta`), and target collateral ratio (`tcr`)
    {
        "op": "call",
        "debt_delta": 1,
        "collateral_delta": 1,
        "tcr": 0,
    },
    # fee_pool - claim `amount_to_claim` from the fee pool of `asset_id`, issued by
    #            `issuer`
    {
        "op": "fee_pool",
        "amount_to_claim": 1,
        "asset_id": "1.3.305",
        "issuer": "1.2.581357",
    },
    # create_pool - create a liquidity pool, where asset a and b are the asset and
    #               currency in the header.  The pool token is given by `share_asset`,
    #               and withdrawal and taker fees are given by their respective keys.
    {
        "op": "create_pool",
        "share_asset": "1.3.9999",
        "taker_fee_percent": 0.1,  # these two are in percent, so 0.1 would be amt*0.001
        "withdrawal_fee_percent": 0.1,
    },
    # create_asset - create a new asset, inline comments given because there are
    #                a lot of values.
]


order5 = order.copy()
order5["edicts"] = [
    {
        "op": "create_asset",
        "issuer": "1.2.581357",  # who is allowed to issue this asset?
        "symbol": "TEST",  # what is it called?
        "precision": 8,  # how many decimal points can amounts of it be referenced with?
        "common_options": {
            # how much of it can exist?
            "max_supply": 1000000,
            # the fee paid by the buyer to the issuer during limit orders
            "market_fee_percent": 1,
            # non-changeable number that limits the above value
            "max_market_fee": 2,
            # series of flags which limits the ability of the issuer to continue to edit particular flags
            "issuer_permissions": 0,
            # the ability of the issuer to change capabilities of the UIA such as the ability to transfer
            "flags": 0,
            # the user may pay their market fees using core token at the core exchange rate
            # periodically updated by the issuer from the fee pool maintained by the issuer
            "core_exchange_rate": {
                "base": {"amount": 1, "asset_id": "1.3.1"},
                "quote": {"amount": 1, "asset_id": "1.3.0"},
            },
            # the issuer may create a list of only those who have permission to trade this asset
            "whitelist_authorities": [],
            # as well as those who do not
            "blacklist_authorities": [],
            # the issuer may create a list of only those other assets this one may be traded against
            "whitelist_markets": [],
            # as well as those it cannot be
            "blacklist_markets": [],
            "description": "Asset for testing bitshares_signing",
        },
        "is_prediction_market": False,
    },
]

bts.broker(order1, broadcast=False)
bts.broker(order2, broadcast=False)
bts.broker(order3, broadcast=False)
bts.broker(order4, broadcast=False)
bts.broker(order5, broadcast=False)
