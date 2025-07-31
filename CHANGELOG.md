
> commit e55ab80ccb88c3ddb3dbc9de315465d0cd08115a

---

March 23 2025

 - ran `pylint --errors-only` on entire package and fixed everything

## rpc.py

 - add `rpc_ticker`
 - `rpc_balances` now returns full account balances as a dictionary keyed by asset name
 - - modified `build_transaction.py` internals to allow for this
 - added cached "common lookups":
 - - `precision`
 - - `id_from_name`
 - - `name_from_id`
 - - `is_mpa`
 - renamed `asset_reserve` key to `reserve` in `rpc_tx_fees`

## utilities.py

 - add `read_file` and `write_file`


## graphene_auth.py

 - `prototype_order`
 - - the asset now defaults to 1.3.0 (BTS)
 - - `account_id` is auto-generated if not given
 - - optionally takes an `rpc` connection for generating the account_id
 - in `broker`, `client_order_id` now defaults to millisecond time

## graphene_signing.py

 - All `OrderedDict` objects were replaced with regular dictionaries, as python3.7 make regular dictionaries ordered.
 - Moved operations and types to new files `operations.py` and `types.py` respectively.

## unit_test.py

 - actually does something; originally intented to provide basic examples, which are now in `__init__.py:quickstart()`.  Now simply asks for username and wif and signs one of every supported op without broadcasting.

## config.py

 - increase TIMEOUT to 60 seconds instead of 20

## build_transaction.py

 - minor bugfixes in `scale_limit_orders` and `save_core_fees`
 - replace `OrderedDict` with regular dictionaries

---

