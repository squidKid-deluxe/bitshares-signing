import itertools

# GRAPHENE SIGNING MODULES
from ..config import AUTOSCALE, CORE_FEES, DUST, KILL_OR_FILL
from ..rpc import rpc_balances, rpc_open_orders
from ..utilities import it, to_iso_date

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_limit_orders(
    create_edicts, fees, asset, currency, account_id, tx_operations
):
    """
    Translate limit orders to graphene
    """
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency
    for idx, edict in enumerate(create_edicts):
        price = edict["price"]
        amount = edict["amount"]
        op_exp = int(edict.get("expiration", 0))
        # convert zero expiration flag to "really far in future"
        if op_exp == 0:
            op_exp = END_OF_TIME
        op_expiration = to_iso_date(op_exp)
        # we'll use ordered dicts and put items in api specific order
        min_to_receive = dict({})
        amount_to_sell = dict({})
        # derive min_to_receive & amount_to_sell from price & amount
        # means SELLING currency RECEIVING assets
        if edict["op"] == "buy":
            min_to_receive["amount"] = int(amount * 10**asset_precision)
            min_to_receive["asset_id"] = asset_id
            amount_to_sell["amount"] = int(amount * price * 10**currency_precision)
            amount_to_sell["asset_id"] = currency_id
        # means SELLING assets RECEIVING currency
        if edict["op"] == "sell":
            min_to_receive["amount"] = int(amount * price * 10**currency_precision)
            min_to_receive["asset_id"] = currency_id
            amount_to_sell["amount"] = int(amount * 10**asset_precision)
            amount_to_sell["asset_id"] = asset_id
        # Limit_order_create fee ordered dictionary
        fee = {"amount": fees["create"], "asset_id": "1.3.0"}
        # create ordered dicitonary from each buy/sell operation
        operation = [
            1,
            {
                "fee": fee,
                "seller": account_id,
                "amount_to_sell": amount_to_sell,
                "min_to_receive": min_to_receive,
                "expiration": op_expiration,
                "fill_or_kill": KILL_OR_FILL,
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations


def scale_limit_orders(
    rpc, order, asset_id, currency_id, account_name, buy_edicts, sell_edicts
):
    """
    Scale order size to funds on hand
    """
    if AUTOSCALE or CORE_FEES:
        balances = rpc_balances(rpc, account_name)
        assets, currency, bitshares = (
            balances[order["header"]["asset_name"]],
            balances[order["header"]["currency_name"]],
            balances["BTS"],
        )
        if AUTOSCALE and buy_edicts + sell_edicts:
            # autoscale buy edicts
            if buy_edicts:
                currency_value = 0
                # calculate total value of each amount in the order
                for idx, _ in enumerate(buy_edicts):
                    currency_value += (
                        buy_edicts[idx]["amount"] * buy_edicts[idx]["price"]
                    )
                # scale the order amounts to means
                scale = SIXSIG * currency / (currency_value + SATOSHI)
                if scale < 1:
                    print(
                        it("yellow", "ALERT: scaling buy edicts to means: %.3f" % scale)
                    )
                    for idx, _ in enumerate(buy_edicts):
                        buy_edicts[idx]["amount"] *= scale
            # autoscale sell edicts
            if sell_edicts:
                asset_total = 0
                # calculate total amount in the order
                for idx, _ in enumerate(sell_edicts):
                    asset_total += sell_edicts[idx]["amount"]
                scale = SIXSIG * assets / (asset_total + SATOSHI)
                # scale the order amounts to means
                if scale < 1:
                    print(
                        it(
                            "yellow",
                            "ALERT: scaling sell edicts to means: %.3f" % scale,
                        )
                    )
                    for idx, _ in enumerate(sell_edicts):
                        sell_edicts[idx]["amount"] *= scale
        save_core_fees(buy_edicts, sell_edicts, bitshares, asset_id, currency_id)

    # after scaling recombine buy and sell
    create_edicts = buy_edicts + sell_edicts

    ###### Remove dust edicts
    if DUST and create_edicts:
        create_edicts2 = []
        dust = DUST * 100000 / 10 ** order["header"]["asset_precision"]
        for idx, edict in enumerate(create_edicts):
            if edict["amount"] > dust:
                create_edicts2.append(edict)
            else:
                print(
                    it("red", "WARN: removing dust threshold %s order" % dust),
                    edict,
                )
        create_edicts = create_edicts2[:]  # copy as new list
        del create_edicts2
    return create_edicts


def save_core_fees(buy_edicts, sell_edicts, bitshares, asset_id, currency_id):
    """
    Always save last two bitshares for fees
    """
    if CORE_FEES and (
        buy_edicts + sell_edicts and ("1.3.0" in [asset_id, currency_id])
    ):
        # when BTS is the currency don't spend the last 2
        if currency_id == "1.3.0" and buy_edicts:
            bts_value = 0
            # calculate total bts value of each amount in the order
            for idx, _ in enumerate(buy_edicts):
                bts_value += buy_edicts[idx]["amount"] * buy_edicts[idx]["price"]
            # scale the order amounts to save last two bitshares
            scale = SIXSIG * max(0, (bitshares - 2)) / (bts_value + SATOSHI)
            if scale < 1:
                print(it("yellow", "ALERT: scaling buy edicts for fees: %.4f" % scale))
                for idx, _ in enumerate(buy_edicts):
                    buy_edicts[idx]["amount"] *= scale
        # when BTS is the asset don't sell the last 2
        if asset_id == "1.3.0" and sell_edicts:
            bts_total = 0
            # calculate total of each bts amount in the order
            for idx, _ in enumerate(sell_edicts):
                bts_total += sell_edicts[idx]["amount"]
            scale = SIXSIG * max(0, (bitshares - 2)) / (bts_total + SATOSHI)
            # scale the order amounts to save last two bitshares
            if scale < 1:
                print(
                    it(
                        "yellow",
                        "ALERT: scaling sell edicts for fees: %.4f" % scale,
                    )
                )
                for idx, _ in enumerate(sell_edicts):
                    sell_edicts[idx]["amount"] *= scale
    return buy_edicts, sell_edicts


def graphenize_cancel(
    rpc, cancel_edicts, fees, order, account_name, account_id, tx_operations
):
    """
    Translate cancel orders to graphene
    """
    for edict in cancel_edicts:
        if "ids" not in edict.keys():
            edict["ids"] = ["1.7.X"]
        if "1.7.X" in edict["ids"]:  # the "cancel all" signal
            # for cancel all op, we collect all open orders in 1 market
            edict["ids"] = rpc_open_orders(rpc, account_name, order["header"])
            print(it("yellow", str(edict)))
        for order_id in edict["ids"]:
            # confirm it is good 1.7.x format:
            order_id = str(order_id)
            aaa, bbb, ccc = order_id.split(".", 2)
            assert int(aaa) == 1
            assert int(bbb) == 7
            assert int(ccc) == float(ccc) > 0
            # create cancel fee ordered dictionary
            fee = {"amount": fees["cancel"], "asset_id": "1.3.0"}
            # create ordered operation dicitonary for this edict
            operation = [
                2,  # two means "Limit_order_cancel"
                {
                    "fee": fee,
                    "fee_paying_account": account_id,
                    "order": order_id,
                    "extensions": [],
                },
            ]
            # append the ordered dict to the trx operations list
            tx_operations.append(operation)
    return tx_operations
