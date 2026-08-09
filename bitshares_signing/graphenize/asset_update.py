from ..rpc import rpc_get_objects, rpc_get_required_fees, rpc_lookup_asset_symbols


def _merge_extensions(current_ext, edict_ext):
    result = dict(current_ext) if current_ext else {}
    for key, value in edict_ext.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = value
    return result


def graphenize_asset_update_bitasset(edicts, fees, rpc, account_id, tx_operations):
    for edict in edicts:
        assets = rpc_lookup_asset_symbols(rpc, [edict["asset_to_update"]])
        asset_id = assets[0]["id"]
        asset = rpc_get_objects(rpc, asset_id)
        bitasset = rpc_get_objects(rpc, asset["bitasset_data_id"])
        current = bitasset["options"]

        current_ext = current.get("extensions")
        edict_ext = edict.get("extensions", {})
        merged_ext = _merge_extensions(current_ext, edict_ext)

        new_opts = {
            "feed_lifetime_sec": current["feed_lifetime_sec"],
            "minimum_feeds": current["minimum_feeds"],
            "force_settlement_delay_sec": current["force_settlement_delay_sec"],
            "force_settlement_offset_percent": current["force_settlement_offset_percent"],
            "maximum_force_settlement_volume": current["maximum_force_settlement_volume"],
            "short_backing_asset": current["short_backing_asset"],
            "extensions": merged_ext,
        }

        operation = [
            12,
            {
                "fee": {"amount": 0, "asset_id": "1.3.0"},
                "issuer": account_id,
                "asset_to_update": asset_id,
                "new_options": new_opts,
            },
        ]
        fee_amount = rpc_get_required_fees(rpc, [operation], "1.3.0")[0]
        operation[1]["fee"]["amount"] = fee_amount
        tx_operations.append(operation)
    return tx_operations


def graphenize_asset_update(edicts, fees, rpc, account_id, tx_operations):
    for edict in edicts:
        assets = rpc_lookup_asset_symbols(rpc, [edict["asset_to_update"]])
        asset_id = assets[0]["id"]
        asset = rpc_get_objects(rpc, asset_id)
        current = asset["options"]

        current_ext = current.get("extensions")
        edict_ext = edict.get("extensions", {})
        merged_ext = _merge_extensions(current_ext, edict_ext)

        new_opts = {
            "max_supply": current["max_supply"],
            "market_fee_percent": edict.get("market_fee_percent", current["market_fee_percent"]),
            "max_market_fee": current["max_market_fee"],
            "issuer_permissions": current["issuer_permissions"],
            "flags": current["flags"],
            "core_exchange_rate": current["core_exchange_rate"],
            "whitelist_authorities": current["whitelist_authorities"],
            "blacklist_authorities": current["blacklist_authorities"],
            "whitelist_markets": current["whitelist_markets"],
            "blacklist_markets": current["blacklist_markets"],
            "description": current["description"],
            "extensions": merged_ext,
        }

        operation = [
            11,
            {
                "fee": {"amount": 0, "asset_id": "1.3.0"},
                "issuer": account_id,
                "asset_to_update": asset_id,
                "new_options": new_opts,
            },
        ]
        fee_amount = rpc_get_required_fees(rpc, [operation], "1.3.0")[0]
        operation[1]["fee"]["amount"] = fee_amount
        tx_operations.append(operation)
    return tx_operations
