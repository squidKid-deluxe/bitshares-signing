```
+-------------------------------------------------+
|   ____  _ _   ____  _                           |
|  | __ )(_) |_/ ___|| |__   __ _ _ __ ___  ___   |
|  |  _ \| | __\___ \| '_ \ / _` | '__/ _ \/ __|  |
|  | |_) | | |_ ___) | | | | (_| | | |  __/\__ \  |
|  |____/|_|\__|____/|_| |_|\__,_|_|  \___||___/  |
|        ____  _             _                    |
|       / ___|(_) __ _ _ __ (_)_ __   __ _        |
|       \___ \| |/ _` | '_ \| | '_ \ / _` |       |
|        ___) | | (_| | | | | | | | | (_| |       |
|       |____/|_|\__, |_| |_|_|_| |_|\__, |       |
|                |___/               |___/        |
+-------------------------------------------------+
```

WTFPL litepresence.com Dec 2021 & squidKid-deluxe Mar 2025

** ManualSigning re-imagined **

---------------------------------------------------

## Authenticated BUY/SELL/CANCEL without Pybitshares (MIT) Architecture

```
def WTFPL_v0_March_1765():
    if any([stamps, licenses, taxation, regulation, fiat, etat]):
        try:
            print("No thank you!")
        except:
            return [tar, feathers]
```

### ALPHA RELEASE - PUBLIC DOMAIN, NO WARRANTY

Joe, a CEX algorithmic trader, discovers Bitshares DEX and asks:

"How do I get reliable public API data that never goes stale?"
 - metaNODE.py

"How do I authenticate to the DEX?"
 - manualSIGNING.py

Seven small scripts, totaling a mere 105kb, and DEX algo trading barriers to entry are defeated.

You’re instantly connected and authenticated.

Buy, sell, and cancel orders with seamless connectivity and simple authentication — CEX-style data at your fingertips.

## FEATURES

- `prototype_order()` generates an order header template.
- Edicts can include any combination of operations.
- Automatically scales buy/sell orders to prevent exceeding account budget.
- Ensure you always have enough funds to cover transaction fees with the last two Bitshares.
- Uses multiprocessing to handle websockets and manage faulty order timeouts.
- New edict `{'op': login}` matches a WIF (Wallet Import Format) to an account name and returns `True`/`False`.
- No dependencies on Pybitshares!

## HOW DO I USE THIS TOOL?

An order is structured as a dictionary of:

`['edicts', 'header', 'nodes']`

See `help(bitshares_signing.quickstart)` for detailed examples.

## OBJECTIVES

- Use only standard Python objects. ✅
- Collect necessary Pybitshares objects (copy, paste, cite). ✅
- Strip unnecessary methods from Pybitshares objects. ✅
- Reorganize classes and definitions in a logical, chronological order. ✅
- Enable users to create orders using simple, human-readable terms. ✅
- Build transactions using Graphene-style terms. ✅
- Serialize transactions. ✅
- Validate serialization using `get_transaction_hex_without_sig()`. ✅
- Sign transactions with ECDSA. ✅
- Validate signed transactions. ✅
- Broadcast transactions to an RPC node. ✅
- Make the script importable as a module and callable with `broker(order)`. ✅
- Allow for a list of buy/sell/cancel actions (edicts). ✅
- Implement `cancel-all` functionality. ✅
- Provide extensive line-by-line commentary for clarity. ✅

## ONGOING:
- Make prototype_order take token- and user- names, rather than ids
- Add Liquidity pool swap/stake/unstake
- Simplify and condense Pybitshares methods. (Still in progress)
- Expand and finalize the `manualSIGNINGwhitepaper.md`. (5200-word rough draft available)
- Transition from object-oriented (class-based) to procedural (function-based) style. (Planned)

## DEPENDENCIES
- Python 3
- Linux recommended, other OSes have not been tested
- ecdsa, secp256k1, and websocket-client. (`pip3 install -r requirements.txt` to get the right versions)

> Note: bitshares_signing has not been tested on python3.10+; for reliable use, use
>       python3.6.9 to python3.9

## LICENSE:
Citations to Pybitshares (MIT) & @xeroc as needed.
Special thanks to @vvk123, @sschiessl, and @harukaff_bot.
All remaining rights under WTFPL March 1765.