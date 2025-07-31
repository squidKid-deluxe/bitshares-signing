import itertools

# GRAPHENE SIGNING MODULES
from ..config import KILL_OR_FILL
from ..rpc import rpc_balances

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_transfer(
    transfer_edicts, fees, asset_id, asset_precision, account_id, tx_operations
):
    """
    Translate transfer orders to graphene
    """
    for idx, transfer in enumerate(transfer_edicts):
        # convert to graphene amount, asset_id type
        # class Transfer(GrapheneObject): # OPERATION ID 0 "transfer"
        fee = {"amount": fees["transfer"], "asset_id": "1.3.0"}
        graphene_amount = int(transfer["amount"] * 10**asset_precision)
        amount_dict = {"amount": graphene_amount, "asset_id": asset_id}
        # transfer ordered dictionary from each buy/sell operation
        operation = [
            0,
            {
                "fee": fee,
                "from": account_id,
                "to": transfer["account_id"],
                "amount": amount_dict,
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations
