r"""
build_transaction.py

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

Build graphene transactions from human-readable edicts

"""

import itertools
# STANDARD PYTHON MODULES
import time
from binascii import unhexlify  # hexidecimal to binary text
from struct import unpack_from  # convert back to PY variable

# GRAPHENE SIGNING MODULES
from .config import AUTOSCALE, CORE_FEES, DUST, KILL_OR_FILL, LIMIT
from .graphenize.asset_create import graphenize_asset_create
from .graphenize.call_order_update import graphenize_call
from .graphenize.fee_pool import graphenize_fee_pool
from .graphenize.issue_reserve import graphenize_issue, graphenize_reserve
from .graphenize.limit_orders import (graphenize_cancel,
                                      graphenize_limit_orders,
                                      scale_limit_orders)
from .graphenize.liquidity_pools import (graphenize_pool_creation,
                                         graphenize_pool_deposit,
                                         graphenize_swaps,
                                         graphenize_pool_update)
from .graphenize.price_feeds import graphenize_add_producer, graphenize_publish
from .graphenize.transfer import graphenize_transfer
from .rpc import (rpc_account_id, rpc_balances, rpc_block_number,
                  rpc_lookup_asset_symbols, rpc_open_orders, rpc_tx_fees)
from .types import ObjectId
from .utilities import fraction, it, to_iso_date

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999



def graphenize_login(login_edicts, fees, account_id, tx_operations):
    """
    Translate login to dummy graphene cancel order
    """
    if login_edicts:
        fee = {"amount": 0, "asset_id": "1.3.0"}
        operation = [
            2,
            {
                "fee": fee,
                "fee_paying_account": account_id,
                "order": "1.7.0",
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations


def build_transaction(rpc, order):
    """
    # this performs incoming limit order api conversion
    # from human terms to graphene terms

    # humans speak:
     - account name, asset name, order number
     - decimal amounts, rounded is just fine
     - buy/sell/cancel
     - amount of assets
     - price in currency

    # graphene speaks:
     - 1.2.x, 1.3.x, 1.7.x
     - only in integers
     - create/cancel
     - min_to_receive/10^receiving_precision
     - amount_to_sell/10^selling_precision

    # build_transaction speaks:
     - list of buy/sell/cancel human terms edicts any order in
     - validated data request
     - autoscale amounts if out of budget
     - autoscale amounts if spending last bitshare
     - bundled cancel/buy/sell transactions out; cancel first
     - prevent inadvertent huge number of orders
     - do not place orders for dust amounts
    """
    # VALIDATE INCOMING DATA
    for key, expected_type in [("edicts", list), ("nodes", list), ("header", dict)]:
        if not isinstance(order[key], expected_type):
            raise ValueError(
                f"order parameter '{key}' must be of type {expected_type.__name__}:"
                f" {order[key]}; is {type(order[key]).__name__}"
            )

    # the location of the decimal place must be provided by order
    asset_precision = int(order["header"].get("asset_precision", 5))
    asset_id = str(order["header"].get("asset_id", "1.3.0"))

    account_name = str(order["header"]["account_name"])
    account_id = str(
        order["header"].get("account_id", rpc_account_id(rpc, account_name))
    )

    currency_precision = int(order["header"].get("currency_precision", 0))
    currency_id = str(order["header"].get("currency_id", 0))

    checks = [account_id, asset_id]

    # perform checks on currency for limit orders
    if order["edicts"][0]["op"] in ["buy", "sell"]:
        checks.append(currency_id)
        if not currency_precision or not currency_id:
            return -1
    # validate a.b.c identifiers of account id and asset ids
    for check in checks:
        ObjectId(check)
    # GATHER TRANSACTION HEADER DATA
    # fetch block data via websocket request
    block = rpc_block_number(rpc)
    ref_block_num = block["head_block_number"] & 0xFFFF
    ref_block_prefix = unpack_from("<I", unhexlify(block["head_block_id"]), 4)[0]
    # fetch limit order create and cancel fee via websocket request
    fees = rpc_tx_fees(rpc, account_id)
    # establish transaction expiration
    tx_expiration = to_iso_date(int(time.time() + 120))
    # initialize tx_operations list
    tx_operations = []

    # Sort incoming edicts by type
    edict_types = {
        "buy": [],
        "sell": [],
        "cancel": [],
        "swap": [],
        "create_pool": [],
        "create_asset": [],
        "transfer": [],
        "reserve": [],
        "issue": [],
        "login": [],
        "call": [],
        "pool_deposit": [],
        "pool_update": [],
        "fee_pool": [],
        "publish": [],
        "add_producer": [],
        # TODO
        # add those from `shorting attack avenger`
    }

    for edict in order["edicts"]:
        if edict["op"] in edict_types:
            print(it("yellow", str({k: str(v) for k, v in edict.items()})))
            edict_types[edict["op"]].append(edict)

    # convert to decimal type

    for op_type in ("buy", "sell"):
        for idx, item in enumerate(edict_types[op_type]):
            edict_types[op_type][idx]["amount"] = item["amount"]
            edict_types[op_type][idx]["price"] = item["price"]

    graphenize_cancel(
        rpc, edict_types["cancel"], fees, order, account_name, account_id, tx_operations
    )
    if any([edict_types["sell"], edict_types["buy"]]):
        scaled_limit_orders = scale_limit_orders(
            rpc,
            order,
            asset_id,
            currency_id,
            account_name,
            edict_types["buy"],
            edict_types["sell"],
        )
        tx_operations = graphenize_limit_orders(
            scaled_limit_orders,
            fees,
            [asset_id, asset_precision],
            [currency_id, currency_precision],
            account_id,
            tx_operations,
        )

    # fmt: off
    # Define a list of operations with their corresponding function and parameters
    operations = [
        ("swap", graphenize_swaps, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("create_pool", graphenize_pool_creation, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("create_asset", graphenize_asset_create, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("call", graphenize_call, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("pool_update", graphenize_pool_update, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("pool_deposit", graphenize_pool_deposit, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("fee_pool", graphenize_fee_pool, [[asset_id, asset_precision], [currency_id, currency_precision]]),
        ("transfer", graphenize_transfer, [asset_id, asset_precision]),
        ("issue", graphenize_issue, [asset_id, asset_precision]),
        ("reserve", graphenize_reserve, [asset_id, asset_precision]),
        ("publish", graphenize_publish, [rpc]),
        ("add_producer", graphenize_add_producer, []),
        ("login", graphenize_login, []),
    ]
    # fmt: on

    # Iterate over the operations and apply them to tx_operations
    for name, func, params in operations:
        tx_operations = func(
            edict_types[name], fees, *params, account_id, tx_operations
        )

    # prevent inadvertent huge number of orders
    tx_operations = tx_operations[:LIMIT]
    # the trx is just a regular dictionary we will convert to json later
    # the operations themselves must still be an OrderedDict
    trx = {
        "ref_block_num": ref_block_num,
        "ref_block_prefix": ref_block_prefix,
        "expiration": tx_expiration,
        "operations": tx_operations,
        "signatures": [],
        "extensions": [],
    }
    return trx
