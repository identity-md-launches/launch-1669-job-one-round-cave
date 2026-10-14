# Return Lens

Decode a saved Ethereum call's successful return bytes using an explicitly chosen
flat ABI layout. This helps a worker read a rehearsal that would otherwise show
only hexadecimal, while retaining the exact target, sender presence, calldata,
value, source and historical block. Python 3.9+ standard library only.

One offline command from the repository root:

```sh
python3 -B line-4/tools/return-lens/return_lens.py demo
```

When tried on 2026-10-14, it printed `decoded` and ZTO supply
`1000000000000000000000000000` base units from the ancestor's saved real
`totalSupply()` call. A fresh PublicNode read also decoded that value at finalized
block `0x18f9676`, hash
`0x0a308ec083664a035e236e8d8939b06557e933ae05347da15d48945a6aa2e884`.
Replay that committed evidence without network:

```sh
python3 -B line-4/tools/return-lens/return_lens.py check line-4/tools/return-lens/zto-live-observation.json --types uint256
```

For another saved Call Rehearsal observation, choose its reviewed return layout:

```sh
python3 -B line-4/tools/return-lens/return_lens.py check path/to/observation.json --types address,uint256,string
```

Supported types: `uint8` through `uint256` and `int8` through `int256` in eight-bit
increments, `bool`, `address`, `bytes1` through `bytes32`, `bytes`, and `string`.
Supply 1–32 comma-separated types. Arrays, nested tuples, aliases and fixed-point
types are rejected. Integers are decimal strings to preserve precision in JSON;
addresses and bytes are hexadecimal; strings require strict UTF-8. No token
decimal scaling or inferred ABI is applied. A decoded zero address, if actually
returned, is evidence data rather than an invented input address.

The decoder requires canonical widths, sign extension, booleans, padding, minimal
ordered dynamic offsets and exact consumption of all bytes. It rejects shared
tails, gaps, trailing words, truncated lengths, malformed UTF-8 and oversized
inputs. A return must also pass the ancestor's saved interpretation: malformed
saved `bool`/`uint256` results are not silently reinterpreted as successful raw
bytes. Use `raw` when collecting legitimate multi-field results. Reverts and RPC
failures remain `inconclusive`. Exit 0 means `decoded`; exit 2 means inconclusive
or invalid input. Decoding `false` is still decoding, not a success predicate.

Optional fresh read-only supply call, with ZTO first by default:

```sh
python3 -B line-4/tools/return-lens/return_lens.py live
```

`--token IMD`, `--rpc https://eth.drpc.org` and `--save new/workspace/file.json`
are available. Live mode is restricted to the two assignment-supplied real tokens'
`totalSupply()` calls. It reuses Call Changes' finalized, block-hash-pinned
collector and its four-method read-only RPC allowlist, dedicated User-Agent,
redirect refusal, disabled environment proxy discovery and 90 KB input limit.
No custom sender is invented. Saves are exclusive and confined to the workspace.
Socket timeouts are per request (25 seconds); there is no total deadline.

Focused checks:

```sh
python3 -B -m unittest discover -s line-4/tools/return-lens -p 'test_*.py' -v
```

All 12 tests passed, including saved real ZTO evidence, signed integer boundaries,
static/dynamic tuples, UTF-8 byte lengths, invalid offsets, padding, transport and
revert outcomes. Other ABI cases in the tests are explicitly synthetic parser
fixtures, not live contract observations.

Retain adjacent `call-changes/` with its `rehearse_core.py` when moving this tool.
There are no external runtime dependencies. Types must come from a reviewed ABI:
matching bytes alone cannot authenticate that ABI or prove expected behavior,
state changes, gas, canonicality, safety or future execution. No wallet, key,
secret, environment variable, signature, broadcast, payment, deployment or
application post is accessed or produced. Live HTTP requests carry only read-only
JSON-RPC queries.

Encoding reference: [Solidity ABI specification](https://docs.soliditylang.org/en/latest/abi-spec.html).
