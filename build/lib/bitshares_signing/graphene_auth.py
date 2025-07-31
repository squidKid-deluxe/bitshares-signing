r"""
graphene_auth.py

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

BitShares ECDSA for Login, Buy, Sell, Cancel, Transfer, Issue, Reserve

"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except, too-many-locals, too-many-statements
# pylint: disable=too-many-branches
#
# STANDARD PYTHON MODULES
import time  # hexidecimal to binary text
from multiprocessing import Process, Value  # convert back to PY variable

from .build_transaction import build_transaction
# GRAPHENE SIGNING MODULES
from .config import ATTEMPTS, JOIN, NODES, PROCESS_TIMEOUT
from .graphene_signing import (PrivateKey, serialize_transaction,
                               sign_transaction, verify_transaction)
from .rpc import (id_from_name, name_from_id, precision,
                  rpc_broadcast_transaction, rpc_get_account,
                  rpc_key_reference, rpc_open_orders, wss_handshake)
from .utilities import it, trace

# ISO8601 timeformat; 'graphene time'
ISO8601 = "%Y-%m-%dT%H:%M:%S%Z"


# Order creation helpers


def prototype_order(info, nodes=None, rpc=None):
    """
    Generates a prototype order, including a header with account and asset
    metadata. It requires a list of cached nodes and asset details to build
    the order structure. If no nodes are provided, it defaults to using the
    `NODES` listed in `config.py`.

    Parameters:
    info (dict): A dictionary containing order-specific information, notably:
                - `asset_id`: The ID of the asset being traded.
                - `asset_precision`: Precision for the asset.
                - `currency_id`: The ID of the associated currency (default is 0).
                - `currency_precision`: Precision for the currency (default is 0).
                - `account_id`: The ID of the issuer's account.
                - `account_name`: The issuer's public account name.
                - `wif`: The issuer's private key in Wallet Import Format (WIF).

    nodes (list, optional): A list of nodes to associate with the order. If
                            not provided, defaults to `NODES`.

    Returns:
    dict: A dictionary representing a prototype order, containing the
          `header` and `nodes`.  To make it not a prototype, simply add an "edicts" key
          with your order information.

    """
    if rpc is None:
        rpc = wss_handshake()
    if nodes is None:
        nodes = NODES
    header = {
        "asset_id": info.get(
            "asset_id", id_from_name(rpc, info.get("asset_name", "BTS"))
        ),
        "currency_id": info.get(
            "currency_id", id_from_name(rpc, info.get("currency_name", "HONEST.USD"))
        ),
    }
    header.update(
        {
            "asset_name": info.get("asset_name", name_from_id(rpc, header["asset_id"])),
            "currency_name": info.get(
                "currency_name", name_from_id(rpc, header["currency_id"])
            ),
        }
    )
    header.update(
        {
            "asset_precision": precision(rpc, header["asset_id"]),
            "currency_precision": precision(rpc, header["currency_id"]),
            "account_id": info.get(
                "account_id", rpc_get_account(rpc, info["account_name"])["id"]
            ),
            "account_name": info["account_name"],
            "wif": info["wif"],
        }
    )
    order = {
        "header": header,
        "edicts": [],
        "nodes": nodes,
    }
    return order


def issue(info, amount, account_id):
    """
    Put UIA.XYZ in user's BitShares wallet.
    """
    order = prototype_order(info)
    order["edicts"] = [{"op": "issue", "amount": amount, "account_id": account_id}]
    print(order["header"]["account_name"], order["header"]["asset_id"], order["edicts"])
    broker(order)


def reserve(info, amount):
    """
    Put UIA.XYZ into the reserve pool.
    """
    order = prototype_order(info)
    order["edicts"] = [{"op": "reserve", "amount": amount}]
    print(order["header"]["account_name"], order["header"]["asset_id"], order["edicts"])
    broker(order)


# Main process
def broker(order, broadcast=True):
    """
    Executes an authenticated operation (one of SUPPORTED_OPS) with robust error handling.

    This function acts as a timed, multiprocess wrapper for authorized operations.
    It ensures that buy, sell, or cancel commands are executed promptly by enforcing a
    timeout for each operation. If the operation does not complete within the
    specified timeout, the process is terminated and restarted. This also helps
    disconnect any hung websockets.

    Parameters:
    order (dict): A dictionary containing the details of the order to execute.
                  See prototype_order for more documentation.

    Returns:
    None

    Behavior:
    - The operation will attempt execution up to a defined number of times (`ATTEMPTS`).
    - Each attempt has a timeout duration of `PROCESS_TIMEOUT`.
    - If the operation still fails to execute within the timeout, it will be aborted.
    - After successful execution, the signal is set to 0 to indicate the process is complete.
    """
    if "client_order_id" not in order["header"]:
        order["header"]["client_order_id"] = int(time.time() * 1e3)
    signal = Value("i", 0)
    auth = Value("i", 0)
    iteration = 0
    while (iteration < ATTEMPTS) and not signal.value:
        iteration += 1
        print("\nmanualSIGNING authentication attempt:", iteration, time.ctime(), "\n")
        child = Process(target=execute, args=(signal, auth, order, broadcast))
        child.daemon = False
        child.start()
        if JOIN:  # means main script will not continue till child done
            child.join(PROCESS_TIMEOUT)
            child.terminate()

    return bool(auth.value)


def execute(signal, auth, order, broadcast):
    """
    #
    """

    def transact(rpc, order, auth):
        trx = build_transaction(rpc, order)
        # if there are any orders, perform ecdsa on serialized transaction
        if trx == -1:
            msg = it("red", "CURRENCY NOT PROVIDED")
        elif trx["operations"]:
            trx, message = serialize_transaction(rpc, trx)
            signed_tx = sign_transaction(trx, message, wif)
            if signed_tx is None:
                msg = it("red", "FAILED TO AUTHENTICATE ORDER")
                return msg
            signed_tx = verify_transaction(signed_tx, wif)
            # don't actaully broadcast login op, signing it is enough
            if order["edicts"][0]["op"] != "login" and broadcast:
                print(
                    rpc_broadcast_transaction(
                        rpc, signed_tx, order["header"]["client_order_id"]
                    )
                )
            auth.value = 1
            msg = it(
                "green",
                ("EXECUTED ORDER" if broadcast else "SIGNED AND VERIFIED ORDER"),
            )
        else:
            msg = it("red", "REJECTED ORDER")
        return msg

    rpc = wss_handshake()

    wif = order["header"]["wif"]
    start = time.time()
    # if this is just an authentication test, then there is no serialization / signing
    # just check that the private key references to the account id in question
    if order["edicts"][0]["op"] == "login":
        msg = it("red", "LOGIN FAILED")
        try:
            # instantitate a PrivateKey object
            private_key = PrivateKey(wif)
            # which contains an Address object
            address = private_key.address
            # which contains str(PREFIX) and a Base58(pubkey)
            # from these two, build a human terms "public key"
            public_key = address.prefix + str(address.pubkey)
            # get a key reference from that public key to 1.2.x account id
            key_reference_id = rpc_key_reference(rpc, public_key)[0][0]
            # extract the account id in the metanode
            account_id = order["header"]["account_id"]
            print("wif account id", key_reference_id)
            print("order account id", account_id)
            # if they match we're authenticated
            if account_id == key_reference_id:
                auth.value = 1
                msg = it("green", "AUTHENTICATED")
        except Exception:
            pass
    else:
        try:
            if (  # cancel all
                order["edicts"][0]["op"] == "cancel"
                and "1.7.X" in order["edicts"][0]["ids"]
            ):
                msg = it("red", "NO OPEN ORDERS")
                open_orders = True
                while open_orders:
                    open_orders = rpc_open_orders(
                        rpc, order["header"]["account_name"], order["header"]
                    )
                    ids = order["edicts"][0]["ids"] = open_orders
                    if ids:
                        msg = transact(rpc, order, auth)
                    time.sleep(5)  # a block and a half
            elif (  # cancel some
                order["edicts"][0]["op"] == "cancel"
                and "1.7.X" not in order["edicts"][0]["ids"]
            ):
                msg = it("red", "NO OPEN ORDERS")
                open_orders = True
                while open_orders:
                    open_orders = rpc_open_orders(
                        rpc, order["header"]["account_name"], order["header"]
                    )
                    ids = order["edicts"][0]["ids"] = [
                        i for i in open_orders if i in order["edicts"][0]["ids"]
                    ]
                    if ids:
                        msg = transact(rpc, order, auth)
                    time.sleep(5)  # a block and a half

            else:  # all other order types
                msg = transact(rpc, order, auth)

        except Exception as error:
            trace(error)
    stars = it("yellow", "*" * (len(msg) + 17))
    msg = "manualSIGNING " + msg
    print("\n")
    print(stars + "\n    " + msg + "\n" + stars)
    print("\n")
    print("process elapsed: %.3f sec" % (time.time() - start), "\n\n")
    signal.value = 1
