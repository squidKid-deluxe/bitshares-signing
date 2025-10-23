r"""
rpc.py

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

Collection of functions that interact with BitShares nodes using a WebSocket connection.

"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except

# STANDARD PYTHON MODULES
import json
import os
import time
from random import shuffle

# THIRD PARTY MODULES
from websocket import create_connection as wss  # handshake to node
from websocket._exceptions import WebSocketConnectionClosedException

# GRAPHENE SIGNING MODULES
from .config import HANDSHAKE_TIMEOUT, NODES, PATH
from .utilities import read_file, trace, write_file


def wss_handshake(rpc=None):
    """
    create a wss handshake in less than X seconds, else try again
    """
    shuffle(NODES)
    handshake = HANDSHAKE_TIMEOUT + 1
    while handshake > HANDSHAKE_TIMEOUT:
        try:
            try:
                if rpc is not None:
                    rpc.close()  # attempt to close open stale connection
            except Exception:
                pass
            start = time.time()
            NODES.append(NODES.pop(0))  # rotate list
            node = NODES[0]
            rpc = wss(node, timeout=HANDSHAKE_TIMEOUT)
            handshake = time.time() - start
        except Exception:
            continue
    return rpc


def wss_query(rpc, params, client_order_id=1):
    """
    this definition will place all remote procedure calls (RPC)
    """

    for _ in range(10):
        try:
            # print(it('purple','RPC ' + params[0])('cyan',params[1]))
            # this is the 4 part format of EVERY rpc request
            # params format is ["location", "object", []]
            query = json.dumps(
                {
                    "method": "call",
                    "params": params,
                    "jsonrpc": "2.0",
                    "id": client_order_id,
                }
            )
            # print(query)
            # rpc is the rpc connection created by wss_handshake()
            # we will use this connection to send query and receive json
            rpc.send(query)
            ret = json.loads(rpc.recv())
            try:
                ret = ret["result"]  # if there is result key take it
            except Exception:
                pass
            # print(ret)
            # print('elapsed %.3f sec' % (time.time() - start))
            return ret
        except WebSocketConnectionClosedException:
            raise RuntimeError("Websocket Closed")
        except Exception as error:
            try:  # attempt to terminate the connection
                rpc.close()
            except Exception:
                pass
            print("RPC failed, switching nodes...")
            # switch NODES
            rpc = wss_handshake(rpc)
            continue


def rpc_block_number(rpc):
    """
    block number and block prefix
    """
    return wss_query(rpc, ["database", "get_dynamic_global_properties", []])


def rpc_account_id(rpc, account_name):
    """
    given an account name return an account id
    """
    ret = wss_query(rpc, ["database", "lookup_accounts", [account_name, 1]])
    return ret[0][1]


def rpc_get_account(rpc, account_name):
    """
    given an account name return an account id
    """
    ret = wss_query(rpc, ["database", "get_account_by_name", [account_name, 1]])
    return ret


def rpc_tx_fees(rpc, account_id):
    # returns fee for limit order create and cancel without 10^precision

    query = [
        "database",
        "get_required_fees",
        [
            [
                [str(op_id), {"from": str(account_id)}]
                for op_id in [
                    0,  # transfer funds
                    1,  # create a limit order
                    2,  # cancel a limit order
                    3,  # update a call order
                    10,  # create an asset
                    13,  # add a feed producer
                    14,  # issue a UIA
                    15,  # reserve a UIA
                    19,  # publish a price feed
                    47,
                    59,  # create liquidity pool
                    60,  # delete liquidity pool
                    61,  # deposit to liquidity pool
                    63,  # exchange via liquidity pool
                    75,  # update liquidity pool
                ]
            ],
            "1.3.0",
        ],
    ]
    ret = wss_query(rpc, query)
    keys = [
        "transfer",
        "create",
        "cancel",
        "call",
        "asset_create",
        "add_producer",
        "issue",
        "reserve",
        "publish",
        "fee_pool",
        "pool_create",
        "pool_delete",
        "pool_deposit",
        "swap",
        "pool_update",
    ]

    final_ret = {key: ret[i]["amount"] for i, key in enumerate(keys)}
    return final_ret


def rpc_ticker(rpc, asset, currency):
    ticker = wss_query(rpc, ["database", "get_ticker", [asset, currency]])
    ret = {}
    ret["base"] = ticker["base"]
    ret["quote"] = ticker["quote"]
    ret["last"] = float(ticker["latest"])
    ret["bid"] = float(ticker["highest_bid"])
    ret["ask"] = float(ticker["lowest_ask"])
    ret["raw"] = ticker
    return ret


def rpc_orderbook(rpc, asset, currency, depth=3):
    """
    Remote procedure call orderbook bids and asks
    ~
    :RPC param str(base): symbol name or ID of the base asset
    :RPC param str(quote): symbol name or ID of the quote asset
    :RPC param int(limit): depth of the order book to retrieve (max limit 50)
    :RPC returns: Order book of the market
    """
    asset_precision = precision(rpc, id_from_name(rpc, asset))
    order_book = wss_query(
        rpc,
        [
            "database",
            "get_order_book",
            [currency, asset, depth],
        ],
    )
    asks = []
    bids = []
    try:
        for i, _ in enumerate(order_book["asks"]):
            price = float(order_book["asks"][i]["price"])
            if float(price) == 0:
                raise ValueError("zero price in asks")
            volume = float(
                float(order_book["asks"][i]["quote"]) / 10 ** int(asset_precision)
            )
            asks.append((price, volume))
        for i, _ in enumerate(order_book["bids"]):
            price = float(order_book["bids"][i]["price"])
            if float(price) == 0:
                raise ValueError("zero price in bids")
            volume = float(
                float(order_book["bids"][i]["quote"]) / 10 ** int(asset_precision)
            )
            bids.append((price, volume))
    except:
        print(order_book)
        raise
    return {"asks": asks, "bids": bids}


def rpc_pool_book(rpc, pool_id=None, pool_data=None, depth=100, maxvolume=None):
    # async def gather_orderbook(self, pool_data, rpc, pair, req_params, ws):
    """
    Gather orderbook information either from the pool data or via RPC request
    Parameters:
        pool_data (dict): The data of the pool
        rpc (object): The rpc instance to be used to make the request
        pair (str): The asset pair being queried
        req_params (dict): The request parameters used gather the orderbook

    Returns:
        data (dict): A dictionary containing the bid and ask orderbook information
    """

    def pool(x_start, y_start, delta_x):
        """
        x_start*y_start = k
        x1 = x_start+delta_x
        k / x1 = y1
        y1-y_start = delta_y
        """
        return y_start - (x_start * y_start) / (x_start + delta_x)

    depth += 1
    if pool_id is not None:
        pool_data = rpc_get_objects(rpc, pool_id)
    elif pool_data is None:
        raise ValueError("Must provide at least one of pool_id or pool_data")

    balance_a = int(pool_data["balance_a"]) / 10 ** precision(rpc, pool_data["asset_a"])
    balance_b = int(pool_data["balance_b"]) / 10 ** precision(rpc, pool_data["asset_b"])
    konstant = balance_a * balance_b

    # List to store the order book
    bidp, bidv, askp, askv = [], [], [], []
    step = (balance_a if maxvolume is None else maxvolume) / depth

    for i in range(1, depth):
        delta_a = i * step
        balance_a2 = balance_a + delta_a
        balance_b2 = konstant / balance_a2
        delta_b = abs(balance_b - balance_b2)
        price = delta_a / delta_b
        # gain = step * price
        askp.append(price)
        askv.append(step)

    for i in range(1, depth):
        delta_a = i * step
        balance_a2 = balance_a - delta_a
        balance_b2 = konstant / balance_a2
        delta_b = abs(balance_b - balance_b2)
        price = delta_a / delta_b
        # gain = step * price
        bidp.append(price)
        bidv.append(step)

    # Sort the order book by price
    asks = list(map(list, sorted(zip(askp, askv), reverse=False)))
    bids = list(map(list, sorted(zip(bidp, bidv), reverse=True)))

    return {"asks": asks, "bids": bids}


def rpc_fill_order_history(rpc, account_id, asset, currency):
    """
    we get a list of "fill order history" dicts for one trading_pair from core:
    {
        "id": "0.0.69",
        "key": {
            "base": "1.3.0",
            "quote": "1.3.8",
            "sequence": -5
        },
        "time.time": "2021-12-22T23:09:42",
        "op": {
            "fee": {
                "amount": 0,
                "asset_id": "1.3.8"
            },
            "order_id": "1.7.181",
            "account_id": "1.2.207",
            "pays": {
                "amount": 100000,
                "asset_id": "1.3.0"
            },
            "receives": {
                "amount": 60000000,
                "asset_id": "1.3.8"
            }
        }
    }
    we need to refine this into dicts
    for our account for each trading_pair in this format:
    {
        "exchange_order_id": str(),
        "trade_type": str(),
        "price": Decimal(),
        "amount": Decimal(),
    }
    """
    iteration = 0
    rpc_fills = []
    while rpc_fills == []:
        iteration += 1
        if iteration > 10:
            break
        ret = wss_query(
            rpc,
            [
                "history",
                "get_fill_order_history",
                [id_from_name(rpc, asset), id_from_name(rpc, currency), 100],
            ],
        )
        # sort by user
        fills = [i for i in ret if i["op"]["account_id"] == account_id]
        for fill in fills:
            print(fill)
            # base
            base_id = fill["op"]["pays"]["asset_id"]
            base_name = name_from_id(rpc, base_id)
            base_precision = precision(rpc, base_id)
            pays = float(fill["op"]["pays"]["amount"]) / 10**base_precision
            # quote
            quote_id = fill["op"]["receives"]["asset_id"]
            quote_name = name_from_id(rpc, quote_id)
            quote_precision = precision(rpc, quote_id)
            receives = float(fill["op"]["receives"]["amount"]) / 10**quote_precision
            # fee
            fee = {"asset": quote_name, "amount": 0}
            try:
                fee_id = fill["op"]["fee"]["asset_id"]
                fee_name = name_from_id(rpc, fee_id)
                if fee_name not in [base_name, quote_name]:
                    raise ValueError("fee outside of trading pair")
                fee_precision = precision(rpc, fee_id)
                fee_amount = float(fill["op"]["fee"]["amount"]) / 10**fee_precision
                fee = {"asset": fee_name, "amount": fee_amount}
            except Exception:
                pass
            # pair and order id
            fill_trading_pair = base_name + "-" + quote_name
            exchange_order_id = fill["op"]["order_id"]

            # Basic data; doesn't change with pair order
            rpc_fills.append(
                {
                    "exchange_order_id": str(exchange_order_id),
                    "unix": from_iso_date(fill["time"]),
                    "sequence": abs(fill["key"]["sequence"]),
                    "fee": fee,
                    "is_maker": fill["op"].get("is_maker", False),
                }
            )

            # eg pays BTC receives USD in BTC-USD market; price = $50,000
            if base_name == asset and quote_name == currency:
                rpc_fills[-1].update(
                    {
                        "price": float(receives / pays),
                        "amount": float(pays),
                        "type": "SELL",
                    }
                )
            # eg pays USD receives BTC in BTC-USD market; price = $50,000
            elif base_name == currency and quote_name == asset:
                rpc_fills[-1].update(
                    {
                        "price": float(pays / receives),
                        "amount": float(receives),
                        "type": "BUY",
                    }
                )
    return rpc_fills


def rpc_balances(rpc, account_name):
    """
    account balances
    """
    balances = wss_query(
        rpc,
        [
            "database",
            "get_named_account_balances",
            [account_name, []],
        ],
    )

    # convert from graphene to human-readable
    balances = {
        name_from_id(rpc, obj["asset_id"]): int(obj["amount"])
        / 10 ** precision(rpc, obj["asset_id"])
        for obj in balances
    }

    return balances


def rpc_open_orders(rpc, account_name, pair):
    """
    return a list of open orders, for one account, in one market
    """
    ret = wss_query(rpc, ["database", "get_full_accounts", [[account_name], "false"]])
    try:
        limit_orders = ret[0][1]["limit_orders"]
    except Exception:
        limit_orders = []
    market = [pair["currency_id"], pair["asset_id"]]
    orders = []
    for order in limit_orders:
        base_id = order["sell_price"]["base"]["asset_id"]
        quote_id = order["sell_price"]["quote"]["asset_id"]
        if (base_id in market) and (quote_id in market):
            orders.append(order["id"])
    return orders


def rpc_key_reference(rpc, public_key):
    """
    given public key return account id
    """
    return wss_query(rpc, ["database", "get_key_references", [[public_key]]])


def rpc_get_transaction_hex_without_sig(rpc, trx):
    """
    use this to verify the manually serialized trx buffer
    """
    ret = wss_query(rpc, ["database", "get_transaction_hex_without_sig", [trx]])
    return bytes(ret, "utf-8")


def rpc_get_transaction_hex(rpc, trx):
    """
    use this to verify the manually serialized trx buffer
    """
    ret = wss_query(rpc, ["database", "get_transaction_hex", [trx]])
    try:
        return bytes(ret, "utf-8")
    except Exception:
        print(trx)
        print(ret)


def rpc_get_objects(rpc, obj_id):
    """
    use this to verify the manually serialized trx buffer
    """
    return wss_query(rpc, ["database", "get_objects", [[obj_id]]])[0]


def rpc_broadcast_transaction(rpc, trx, client_order_id=1):
    """
    upload the signed transaction to the blockchain
    """
    ret = wss_query(
        rpc, ["network_broadcast", "broadcast_transaction", [trx]], client_order_id
    )

    print(json.dumps(ret, indent=4))

    return ret


def rpc_lookup_asset_symbols(rpc, asset):  # DONE
    """
    Given asset names return asset ids and precisions
    """
    if isinstance(asset, str):
        asset = [asset]

    return wss_query(rpc, ["database", "lookup_asset_symbols", [asset]])


def precision(rpc, object_id):
    """
    Retrieve or fetch and store the precision value for a given object ID.

    Args:
        rpc: RPC connection object
        object_id: Unique identifier of the object

    Returns:
        int: Precision value associated with the object
    """
    # Attempt to load existing precision data from file
    try:
        precs = json.loads(read_file("precisions.txt"))
    except (FileNotFoundError, json.JSONDecodeError):
        precs = {}  # Initialize empty dict if file doesn't exist or is invalid

    # Return cached precision if available
    if object_id in precs:
        return precs[object_id]

    # Fetch precision from RPC and convert to integer
    prec = int(rpc_get_objects(rpc, object_id)["precision"])
    precs[object_id] = prec  # Cache the new precision value

    # Save updated precision data to file
    write_file(os.path.join(PATH, "pipe", "precisions.txt"), json.dumps(precs))
    return prec


def id_from_name(rpc, object_name):
    """
    Get or retrieve and store object ID based on its name.

    Args:
        rpc: RPC connection object
        object_name: Name of the object

    Returns:
        str: Object ID corresponding to the name
    """
    # Load existing name-to-ID mappings
    try:
        precs = json.loads(read_file(os.path.join(PATH, "pipe", "ids_to_names.txt")))
    except (FileNotFoundError, json.JSONDecodeError):
        precs = {}

    # Return cached ID if available
    if object_name in precs:
        return precs[object_name]

    # Fetch ID from RPC using the object name
    prec = rpc_lookup_asset_symbols(rpc, object_name)[0]["id"]
    precs[object_name] = prec  # Cache the result

    # Save updated mappings to file
    write_file(os.path.join(PATH, "pipe", "ids_to_names.txt"), json.dumps(precs))
    return prec


def name_from_id(rpc, obj_id, kind="asset"):
    """
    Retrieve or fetch and store object name based on its ID and type.

    Args:
        rpc: RPC connection object
        obj_id: Object identifier
        kind: Type of object ("asset" or other), defaults to "asset"

    Returns:
        str: Name or symbol of the object
    """
    # Load existing ID-to-name mappings
    try:
        precs = json.loads(read_file(os.path.join(PATH, "pipe", "names_to_ids.txt")))
    except (FileNotFoundError, json.JSONDecodeError):
        precs = {}

    # Create a unique key combining ID and kind
    key = str((obj_id, kind))
    if key in precs:
        return precs[key]

    # Fetch appropriate field based on object kind
    if kind == "asset":
        prec = rpc_get_objects(rpc, obj_id)["symbol"]  # Get asset symbol
    else:
        prec = rpc_get_objects(rpc, obj_id)["name"]  # Get object name

    precs[key] = prec  # Cache the result

    # Save updated mappings to file
    write_file(os.path.join(PATH, "pipe", "names_to_ids.txt"), json.dumps(precs))
    return prec


def is_mpa(rpc, object_id):
    """
    Check if an object is a Market Pegged Asset (MPA).

    Args:
        object_id: Unique identifier of the object

    Returns:
        bool: True if object is an MPA, False otherwise
    """
    # Load existing MPA status data
    try:
        precs = json.loads(read_file(os.path.join(PATH, "pipe", "mpas.txt")))
    except (FileNotFoundError, json.JSONDecodeError):
        precs = {}

    # Return cached status if available
    if object_id in precs:
        return precs[object_id]

    # Check if object has bitasset_data_id field to determine MPA status
    prec = "bitasset_data_id" in rpc_get_objects(rpc, object_id)
    precs[object_id] = prec  # Cache the result

    # Save updated MPA status data to file
    write_file(os.path.join(PATH, "pipe", "mpas.txt"), json.dumps(precs))
    return prec


def unit_test():
    """
    test functionality of select definitions
    """
    rpc = wss_handshake()
    rpc_get_account(rpc, "litepresence1")


if __name__ == "__main__":
    unit_test()
