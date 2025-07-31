import itertools

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_call(
    call_edicts,
    fees,
    asset,
    currency,
    account_id,
    tx_operations,
):
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency
    # TRANSLATE CALL ORDERS TO GRAPHENE
    for call in call_edicts:
        # convert to graphene amount, asset_id type
        delta_debt = {
            "amount": int(call["debt_delta"] * 10**asset_precision),
            "asset_id": asset_id,
        }
        delta_collateral = {
            "amount": int(call["collateral_delta"] * 10**currency_precision),
            "asset_id": currency_id,
        }
        # call fee ordered dictionary of graphene amount, asset_id
        fee = {"amount": fees["call"], "asset_id": "1.3.0"}
        # call ordered dictionary from each buy/sell operation
        operation = [
            3,
            {
                "fee": fee,
                "funding_account": account_id,
                "delta_collateral": delta_collateral,
                "delta_debt": delta_debt,
                "extensions": {"target_collateral_ratio": int(1000 * call["tcr"])},
            },
        ]
        # add this op to our list of ops
        tx_operations.append(operation)
    return tx_operations
