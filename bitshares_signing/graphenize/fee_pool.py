import itertools

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_fee_pool(
    fee_pool_edicts,
    fees,
    asset,
    currency,
    account_id,
    tx_operations,
):
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency

    for fee_pool in fee_pool_edicts:
        # call fee ordered dictionary of graphene amount, asset_id
        fee = {"amount": 0, "asset_id": "1.3.0"}
        # call ordered dictionary from each buy/sell operation
        operation = [
            47,
            {
                "fee": {"amount": fees["fee_pool"], "asset_id": "1.3.0"},
                "issuer": fee_pool["issuer"],
                "asset_id": fee_pool["asset_id"],
                "amount_to_claim": {
                    "amount": fee_pool["amount_to_claim"],
                    "asset_id": "1.3.0",
                },
                "extensions": [],
            },
        ]
        # add this op to our list of ops
        tx_operations.append(operation)
    return tx_operations
