import itertools

# MAX is 4294967295; year 2106 due to 32 bit unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = 0.00000001
# almost 1
SIXSIG = 0.999999


def graphenize_asset_create(
    asset_create_edicts,
    fees,
    asset,
    currency,
    account_id,
    tx_operations,
):
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency
    for asset_create_edict in asset_create_edicts:
        common_options = asset_create_edict["common_options"]
        operation = [
            10,
            {
                "fee": {"amount": 96700000, "asset_id": "1.3.0"},
                "issuer": asset_create_edict["issuer"],
                "symbol": asset_create_edict["symbol"],
                "precision": asset_create_edict["precision"],
                "common_options": {
                    "max_supply": common_options["max_supply"],
                    "market_fee_percent": common_options["market_fee_percent"],
                    "max_market_fee": common_options["max_market_fee"],
                    "issuer_permissions": common_options["issuer_permissions"],
                    "flags": common_options["flags"],
                    "core_exchange_rate": common_options["core_exchange_rate"],
                    "whitelist_authorities": common_options["whitelist_authorities"],
                    "blacklist_authorities": common_options["blacklist_authorities"],
                    "whitelist_markets": common_options["whitelist_markets"],
                    "blacklist_markets": common_options["blacklist_markets"],
                    "description": common_options["description"],
                    "extensions": [],
                },
                "is_prediction_market": asset_create_edict["is_prediction_market"],
                "extensions": [],
            },
        ]
        tx_operations.append(operation)
    return tx_operations
