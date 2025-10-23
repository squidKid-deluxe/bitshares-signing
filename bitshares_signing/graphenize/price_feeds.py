import itertools

# GRAPHENE SIGNING MODULES
from ..rpc import rpc_lookup_asset_symbols
from ..utilities import fraction

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_publish(publish_edicts, fees, rpc, account_id, tx_operations):
    """
    TRANSLATE PRICE FEED PUBLISH ORDERS TO GRAPHENE
    """
    symbols = list(
        set(
            itertools.chain(
                *[[i["currency_name"], i["asset_name"]] for i in publish_edicts]
            )
        )
    )
    symbol_data = dict(zip(symbols, rpc_lookup_asset_symbols(rpc, symbols)))
    for edict in publish_edicts:
        # make external rpc for id and precision for the asset
        asset_id, asset_precision = (
            symbol_data[edict["asset_name"]]["id"],
            symbol_data[edict["asset_name"]]["precision"],
        )
        # repeat for currency
        currency_id, currency_precision = (
            symbol_data[edict["currency_name"]]["id"],
            symbol_data[edict["currency_name"]]["precision"],
        )
        # adjust settlment price to graphene asset and currency precisions
        adj_settlement = (
            edict["settlement_price"] * 10**asset_precision / 10**currency_precision
        )
        if edict["currency_name"] == "BTS":
            adj_core = adj_settlement
        else:
            adj_core = edict["core_price"] * 10**asset_precision / 10**5
        # FEE ORDERED DICT
        # create publication fee ordered dict
        fee = {"amount": fees["publish"], "asset_id": "1.3.0"}
        # SETTLEMENT ORDERED DICT
        # convert settlement price to a base/quote fraction
        s_base = fraction(adj_settlement)["base"]
        s_quote = fraction(adj_settlement)["quote"]
        # create a settlement-base price ordered dict
        settlement_base = {"amount": s_base, "asset_id": asset_id}
        # create a quote price ordered dict used w/ settlement base
        settlement_quote = {"amount": s_quote, "asset_id": currency_id}
        # combine settlement base and quote price
        settlement_price = {"base": settlement_base, "quote": settlement_quote}
        # CORE ORDERED DICT
        # convert core price to a base/quote fraction and multiply base by CER coeff
        c_base = int(fraction(adj_core)["base"] * edict["CER"])
        c_quote = fraction(adj_core)["quote"]
        # create a core-base price ordered dict
        core_base = {"amount": c_base, "asset_id": asset_id}
        # create a quote price ordered dict used w/ core base
        core_quote = {"amount": c_quote, "asset_id": "1.3.0"}
        # combine core base and quote price
        core_exchange_rate = {"base": core_base, "quote": core_quote}
        # /bitshares/bitshares.py
        feed = {
            "settlement_price": settlement_price,
            "maintenance_collateral_ratio": edict["MCR"],
            "maximum_short_squeeze_ratio": edict["MSSR"],
            "core_exchange_rate": core_exchange_rate,
        }
        operation = [
            19,  # nineteen means "Publish Price Feed"
            {
                "fee": fee,
                "publisher": account_id,
                "asset_id": asset_id,
                "feed": feed,
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_add_producer(producer_edicts, fees, account_id, tx_operations):
    """
    TRANSLATE ADD PRODUCER ORDER TO GRAPHENE
    """
    for edict in producer_edicts:
        fee = {"amount": fees["add_producer"], "asset_id": "1.3.0"}
        operation = [
            13,  # thirteen means "edit the price feed producer list"
            {
                "fee": fee,
                "issuer": account_id,
                "asset_to_update": edict["asset_id"],
                "new_feed_producers": edict["producer_ids"],
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations
