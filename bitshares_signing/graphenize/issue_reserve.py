import itertools

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_issue(
    issue_edicts, fees, asset_id, asset_precision, account_id, tx_operations
):
    """
    Translate issue orders to graphene
    """
    for idx, issue in enumerate(issue_edicts):
        # convert to graphene amount, asset_id type
        # class Asset_issue(GrapheneObject): # OPERATION ID 14 "asset_issue"
        fee = {"amount": fees["issue"], "asset_id": "1.3.0"}
        graphene_amount = issue["amount"] * 10**asset_precision
        amount_dict = {"amount": graphene_amount, "asset_id": asset_id}
        # issue ordered dictionary from each buy/sell operation
        operation = [
            14,
            {
                "fee": fee,
                "issuer": account_id,
                "asset_to_issue": amount_dict,
                "issue_to_account": issue["account_id"],
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_reserve(
    reserve_edicts, fees, asset_id, asset_precision, account_id, tx_operations
):
    """
    Translate reserve orders to graphene
    """
    for idx, reserve in enumerate(reserve_edicts):
        # convert to graphene amount, asset_id type
        # class Asset_reserve(GrapheneObject): # OPERATION ID 15 "asset_reserve"
        fee = {"amount": fees["reserve"], "asset_id": "1.3.0"}
        graphene_amount = reserve["amount"] * 10**asset_precision
        amount_dict = {"amount": graphene_amount, "asset_id": asset_id}
        # reserve ordered dictionary from each buy/sell operation
        operation = [
            15,
            {
                "fee": fee,
                "payer": account_id,
                "amount_to_reserve": amount_dict,
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations
