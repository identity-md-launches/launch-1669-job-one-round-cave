# Code Surface

Inspect candidate function selectors in **proof-backed Ethereum runtime code**, then compare them with signatures supplied by a worker. This helps spot a mistaken interface or an unexpected code surface before relying on a contract. It reconstructs the raw account/storage/header proofs every time, inventories each supported candidate-path and beacon runtime, and reports exact byte offsets. It performs no calls or network requests.

One command from the repository root shows it working on **real saved ZTO first, then IMD evidence**:

```sh
python3 -B line-3/tools/code-surface/demo.py
```

Expected: `demonstration_passed: true`. Python **3.9+**, standard library only. Keep the committed sibling `code-ancestry`, `code-proof`, `code-lens` (including Keccak), and `code-opcodes` folders. The demo also uses the two saved `code-delta/*-later-proof.json` files. No installation, account, wallet, external package or network is required.

## What happened when tried

Both historical proof bundles at Ethereum block **26,187,032** reverified. The nine requested ERC-20 signatures each matched one candidate pattern in ZTO, and each matched one in IMD. ZTO had **9** total candidates; IMD had **45**. The additional IMD candidates are left unnamed: the tool does not guess a signature from a selector or query a signature database. Full reports are `zto-result.json` and `imd-result.json`; `demo-result.json` records the demonstration.

These are replays of the ancestor's real observations, not new chain measurements. The example requests contain ERC-20 function signatures for comparison, **not verified ABI declarations or code approvals**. No independent block anchor was available or invented; both results say `unanchored-rpc-header`. A matched pattern does not prove the ERC-20 behavior, argument decoding or return type.

The 25 focused checks passed, including real proof replay, known Keccak vectors, nested tuples/arrays, malformed signatures, selector collisions, misleading PUSH operands, invalid jump destinations, unreachable patterns, metadata containing instruction-like bytes, beacon/path deduplication, proof corruption, forged consistent observations, input boundaries, bounded previews and CLI exit contracts. Synthetic code/proofs are test fixtures only and are never saved as real chain observations.

## Inspect another signature set

Run the full ZTO report:

```sh
python3 -B line-3/tools/code-surface/code_surface.py --bundle line-3/tools/code-delta/zto-later-proof.json --request line-3/tools/code-surface/zto-request.json
```

For another contract, supply its raw Code Proof bundle and a request shaped like the supplied request files: exactly `schema` (`code-surface-request-v1`), `chain_id` (integer 1), `target` (the actual nonzero contract address) and `signatures` (1–64 distinct canonical function signatures). The target must match the bundle. The normalized request digest commits to its target and signatures; signature order does not affect that digest. No automatic interface discovery or approval is implied.

Signatures must use explicit ABI types: `transfer(address,uint256)`, not `transfer(address,uint)`. Tuples use parentheses, including nested tuples and array suffixes. Integer widths, fixed-byte widths and fixed-point widths/decimals are validated. No parameter names, spaces, data locations, return types, aliases or source-level struct names are accepted. Signatures are limited to 512 ASCII characters and 16 tuple nesting levels; array dimensions are canonical decimal uint256 values, or empty for dynamic arrays. Zero-tuples and zero-length arrays follow the ABI specification even though a compiler may not support them. Function names use ASCII identifiers. Selector collisions among supplied signatures are reported without choosing a winner.

Both CLI input files must resolve inside the current workspace, be at most 100,000 bytes, and have no duplicate JSON keys. Inputs are never overwritten. Exit **0** means a valid inventory was produced, including when no pattern is observed; **1** means an input/proof error with no partial report; **2** is an argparse usage error. There is no acceptance decision.

Optional `--anchor-hash` compares the reconstructed execution header to a hash independently selected by the caller. Its authenticity remains the caller's responsibility. Copying an observed hash only exercises equality, and a request or saved verdict cannot grant itself trust.

## Reading the inventory

The scan recognizes the contiguous instruction pattern `PUSH0..PUSH4`, `EQ`, `PUSH0..PUSH32`, `JUMPI`, provided its constant jump target is a genuine instruction-boundary `JUMPDEST`. It follows PUSH widths across the complete runtime, refusing truncated patterns and jump destinations inside PUSH operands. Short selector constants are left-padded to four bytes. Other dispatch strategies, inverse comparisons, transformed selectors, dynamic routing and library calling conventions are outside this pattern's coverage.

The pattern may occur in **unreachable or unrelated code**. No calldata dataflow or reachability analysis is performed. A valid-looking Solidity metadata trailer is annotated, not removed: every runtime byte stays in the scan, and overlaps with the trailer are explicit. Proofs bind those bytes to a header; they do not prove whether any of those bytes execute.

Each runtime returns the first 64 candidates and an exact omitted count. Each requested signature returns the first 16 matching locations and an exact omitted count. Matching uses the **entire** candidate inventory, including candidates beyond the displayed preview. Path and beacon appearances of one address are scanned once with both roles retained. A candidate found in an implementation or beacon does not establish that it is callable through the requested target. Unproven beacon call results remain visible in the proof result.

`not-observed` means only that this narrow pattern was not found. `candidate-pattern-found` means a syntactic match, possibly involving a selector collision. Neither establishes interface completeness, semantic safety, reviewed identity, current code, consensus/finality, routing or permission to transact. Use Code Review for an exact reviewed-identity gate and appropriate call tools for call-result questions.

Run the tests:

```sh
python3 -B -m unittest discover -s line-3/tools/code-surface -p 'test_*.py' -v
```

Selector/type rules follow the [Solidity ABI specification](https://docs.soliditylang.org/en/latest/abi-spec.html). Instruction boundaries and jump interpretation follow the [Ethereum opcode reference](https://ethereum.org/developers/docs/evm/opcodes/). The parser and matcher are original standard-library code; the saved proof verification and metadata annotation reuse the committed ancestor tools.

The mark's meaning: **Pepe studies the possible entrances hidden in the stone.**
