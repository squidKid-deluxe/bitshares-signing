import itertools

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_swaps(swap_edicts, fees, asset, currency, account_id, tx_operations):
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency
    for edict in swap_edicts:
        price = edict["price"]
        amount = edict["amount"]
        pool = edict["pool"]
        fee = {"amount": fees["swap"], "asset_id": "1.3.0"}
        # we'll use ordered dicts and put items in api specific order
        min_to_receive = dict({})
        amount_to_sell = dict({})
        # derive min_to_receive & amount_to_sell from price & amount
        # means SELLING currency RECEIVING assets
        if edict["op"] == "swap":
            amount_to_sell["amount"] = int(amount * 10**currency_precision)
            amount_to_sell["asset_id"] = currency_id

            if price == 0:
                min_to_receive["amount"] = int(1)
                min_to_receive["asset_id"] = asset_id
            else:
                min_to_receive["amount"] = int(amount / price * 10**asset_precision)
                min_to_receive["asset_id"] = asset_id

        operation = [
            63,
            {
                "fee": fee,
                "account": account_id,
                "pool": pool,
                "amount_to_sell": amount_to_sell,
                "min_to_receive": min_to_receive,
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_pool_creation(
    pool_create_edicts,
    fees,
    asset,
    currency,
    account_id,
    tx_operations,
):
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency

    for pool_create_edict in pool_create_edicts:
        # op_exp = int(pool_create_edict["expiration"])
        operation = [
            59,
            {
                "fee": {"amount": 5000000, "asset_id": "1.3.0"},
                "account": account_id,
                "asset_a": asset_id,
                "asset_b": currency_id,
                "share_asset": pool_create_edict["share_asset"],
                "taker_fee_percent": int(pool_create_edict["taker_fee_percent"] * 100),
                "withdrawal_fee_percent": int(
                    pool_create_edict["withdrawal_fee_percent"] * 100
                ),
            },
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_pool_deposit(
    pool_deposit_edicts,
    fees,
    asset,
    currency,
    account_id,
    tx_operations,
):
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency
    for pool_deposit in pool_deposit_edicts:
        # call fee ordered dictionary of graphene amount, asset_id
        fee = {"amount": fees["pool_deposit"], "asset_id": "1.3.0"}
        # call ordered dictionary from each buy/sell operation
        operation = [
            61,
            {
                "fee": fee,
                "account": account_id,
                "pool": pool_deposit["pool"],
                "amount_a": {
                    "amount": int(pool_deposit["amount_a"] * 10**asset_precision),
                    "asset_id": asset_id,
                },
                "amount_b": {
                    "amount": int(pool_deposit["amount_b"] * 10**currency_precision),
                    "asset_id": currency_id,
                },
                "extensions": [],
            },
        ]
        # add this op to our list of ops
        tx_operations.append(operation)
    return tx_operations
