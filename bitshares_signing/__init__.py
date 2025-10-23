r"""
```
+-------------------------------------------------+
|   ____  _ _   ____  _                           |
|  | __ )(_) |_/ ___|| |__   __ _ _ __ ___  ___   |
|  |  _ \| | __\___ \| '_ \ / _` | '__/ _ \/ __|  |
|  | |_) | | |_ ___) | | | | (_| | | |  __/\__ \  |
|  |____/|_|\__|____/|_| |_|\__,_|_|  \___||___/  |
|        ____  _             _                    |
|       / ___|(_) __ _ _ __ (_)_ __   __ _        |
|       \___ \| |/ _` | '_ \| | '_ \ / _` |       |
|        ___) | | (_| | | | | | | | | (_| |       |
|       |____/|_|\__, |_| |_|_|_| |_|\__, |       |
|                |___/               |___/        |
+-------------------------------------------------+
```

WTFPL litepresence.com Dec 2021 & squidKid-deluxe Jan 2024

** ManualSigning re-imagined **

---------------------------------------------------

## Authenticated BUY/SELL/CANCEL without Pybitshares (MIT) Architecture

```
def WTFPL_v0_March_1765():
    if any([stamps, licenses, taxation, regulation, fiat, etat]):
        try:
            print("No thank you!")
        except:
            return [tar, feathers]
```

### ALPHA RELEASE - PUBLIC DOMAIN, NO WARRANTY

Joe, a CEX algorithmic trader, discovers Bitshares DEX and asks:

"How do I get reliable public API data that never goes stale?"
 - metaNODE.py

"How do I authenticate to the DEX?"
 - manualSIGNING.py

Seven small scripts, totaling a mere 105kb, and DEX algo trading barriers to entry are defeated.

You’re instantly connected and authenticated.

Buy, sell, and cancel orders with seamless connectivity and simple authentication — CEX-style data at your fingertips.

Want more?

For full buy/sell/cancel + order book UI:
 - microDEX.py

For advanced algorithmic trading and backtesting:
 - extinctionEVENT.py

For tracking historical returns on investment:
 - accountBALANCES.py

For the ultimate public API full universe search utility:
 - latencyTEST.py

> NOTE: the above scripts are outdated and may require modification for reliable usage

Whitepapers for deep dives:
 - metaNODEwhitepaper.md
 - manualSIGNINGwhitepaper.md

## FEATURES

- `prototype_order()` generates an order header template.
- Edicts can include any combination of operations.
- Automatically scales buy/sell orders to prevent exceeding account budget.
- Ensure you always have enough funds to cover transaction fees with the last two Bitshares.
- Uses multiprocessing to handle websockets and manage faulty order timeouts.
- New edict `{'op': login}` matches a WIF (Wallet Import Format) to an account name and returns `True`/`False`.
- No dependencies on Pybitshares!

## HOW DO I USE THIS TOOL?

An order is structured as a dictionary of:

`['edicts', 'header', 'nodes']`

See `help(bitshares_signing.quickstart)` for detailed examples.

## OBJECTIVES

- Use only standard Python objects. ✅
- Collect necessary Pybitshares objects (copy, paste, cite). ✅
- Strip unnecessary methods from Pybitshares objects. ✅
- Reorganize classes and definitions in a logical, chronological order. ✅
- Enable users to create orders using simple, human-readable terms. ✅
- Build transactions using Graphene-style terms. ✅
- Serialize transactions. ✅
- Validate serialization using `get_transaction_hex_without_sig()`. ✅
- Sign transactions with ECDSA. ✅
- Validate signed transactions. ✅
- Broadcast transactions to an RPC node. ✅
- Make the script importable as a module and callable with `broker(order)`. ✅
- Allow for a list of buy/sell/cancel actions (edicts). ✅
- Implement `cancel-all` functionality. ✅
- Provide extensive line-by-line commentary for clarity. ✅

## ONGOING:
- Make prototype_order take token- and user- names, rather than ids
- Add Liquidity pool swap/stake/unstake
- Simplify and condense Pybitshares methods. (Still in progress)
- Expand and finalize the `manualSIGNINGwhitepaper.md`. (5200-word rough draft available)
- Transition from object-oriented (class-based) to procedural (function-based) style. (Planned)

## DEPENDENCIES
- Python 3
- Linux recommended, other OSes have not been tested
- ecdsa, secp256k1, and websocket-client. (`pip3 install -r requirements.txt` to get the right versions)

> Note: bitshares_signing has not been tested on python3.10+; for reliable use, use
>       python3.6.9 to python3.9

## LICENSE:
Citations to Pybitshares (MIT) & @xeroc as needed.
Special thanks to @vvk123, @sschiessl, and @harukaff_bot.
All remaining rights under WTFPL March 1765.
"""

from .graphene_auth import broker, prototype_order

__all__ = ["broker", "prototype_order", "SUPPORTED_OPS", "quickstart"]
SUPPORTED_OPS = [
    "login",
    "buy",
    "sell",
    "cancel",
    "swap",
    "deposit_pool",
    "transfer",
    "issue",
    "reserve",
    "call",
    "fee_pool",
    "create_pool",
    "create_asset",
    "update_pool",
]


def quickstart():
    """
    from bitshares_signing import broker, prototype_order

    # define order headers
    order = prototype_order(
        {
            "asset_id": "1.3.x",
            "asset_precision": int(),
            "currency_id": "1.3.x",
            "currency_precision": int(),
            "account_id": "1.2.x",
            "account_name": str(),
            "wif": str(),
        }
    )
    test_order1 = order.copy()
    test_order2 = order.copy()

    # test your wif with login
    test_order1["edicts"] = [
        {
            "op": "login",
        }
    ]
    logged_in = broker(order)

    # add edicts
    order["edicts"] = [
        # buy - buying `asset`, selling `currency`
        {
            "op": "buy",
            "amount": float(),
            "price": float(),
        },
        # sell - selling `asset`, buying `currency`
        {
            "op": "sell",
            "amount": float(),
            "price": float(),
        },
        # cancel - cancel all `ids` or all open orders if `ids` is ["1.7.X"]
        {
            "op": "cancel",
            "ids": ["1.7.X"],
        },
        # swap - selling `amount` of `currency` for `assets` at `price` on `pool`
        {
            "op": "swap",
            "amount": float(),
            "price": float(),
            "pool": "1.19.x",
        },
        # deposit_pool - deposit `amount_a` of `asset` and `amount_b` of `currency` into `pool`
        {
            "op": "deposit_pool",
            "amount_a": float(),  # asset
            "amount_b": float(),  # currency
            "pool": "1.19.x",
        },
        # transfer - move `amount` of `asset` to `account_id`
        {
            "op": "transfer",
            "amount": float(),
            "account_id": "1.2.x",
        },
        # issue - issue `amount` of `asset` to `account_id`
        {
            "op": "issue",
            "amount": float(),
            "account_id": "1.2.x",
        },
        # reserve - reserve `amount` of `asset`
        {
            "op": "reserve",
            "amount": float(),
        },
        # call - update a call order with a change in debt (`debt_delta`), change in
        #        collateral (`collateral_delta`), and target collateral ratio (`tcr`)
        {
            "op": "call",
            "debt_delta": float(),
            "collateral_delta": float(),
            "tcr": float(),
        },
        # fee_pool - claim `amount_to_claim` from the fee pool of `asset_id`, issued by
        #            `issuer`
        {
            "op": "fee_pool",
            "amount_to_claim": float(),
            "asset_id": "1.3.x",
            "issuer": "1.2.x",
        },
        # create_pool - create a liquidity pool, where asset a and b are the asset and
        #               currency in the header.  The pool token is given by `share_asset`,
        #               and withdrawal and taker fees are given by their respective keys.
        {
            "op": "create_pool",
            "share_asset": "1.3.x",
            "taker_fee_percent": float(),  # these two are in percent, so 0.1 would be amt*0.001
            "withdrawal_fee_percent": float(),
        },
        # create_asset - create a new asset, inline comments given because there are
        #                a lot of values.
        {
            "op": "create_asset",
            "issuer": "1.2.x",  # who is allowed to issue this asset?
            "symbol": str(),  # what is it called?
            "precision": int(),  # how many decimal points can amounts of it be referenced with?
            "common_options": {
                # how much of it can exist?
                "max_supply": int(),
                # the fee paid by the buyer to the issuer during limit orders
                "market_fee_percent": int(),
                # non-changeable number that limits the above value
                "max_market_fee": int(),
                # series of flags which limits the ability of the issuer to continue to edit particular flags
                "issuer_permissions": int(),
                # the ability of the issuer to change capabilities of the UIA such as the ability to transfer
                "flags": int(),
                # the user may pay their market fees using core token at the core exchange rate
                # periodically updated by the issuer from the fee pool maintained by the issuer
                "core_exchange_rate": {
                    "base": {"amount": int(), "asset_id": "1.3.1"},
                    "quote": {"amount": int(), "asset_id": "1.3.0"},
                },
                # the issuer may create a list of only those who have permission to trade this asset
                "whitelist_authorities": list("1.2.x"),
                # as well as those who do not
                "blacklist_authorities": list("1.2.x"),
                # the issuer may create a list of only those other assets this one may be traded against
                "whitelist_markets": list("1.3.x"),
                # as well as those it cannot be
                "blacklist_markets": list("1.3.x"),
                "description": str(),
            },
            "is_prediction_market": bool(),
        },
    ]

    broker(order)
    """
    pass
