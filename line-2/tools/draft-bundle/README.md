# Draft Bundle

Check that a handoff contains **every optional unsigned ERC-20 revoke candidate exactly once**, with no altered or extra candidate. It binds the bundle to the reviewed chain, token, block number and hash. Candidate order does not matter. This is Python 3.10+ using only the standard library and the adjacent Approval Draft / Permission Gate validators already shipped in this line.

One command from the repository root shows it working:

```sh
python3 -B line-2/tools/draft-bundle/draft_bundle.py
```

When tried, the saved real Ethereum ZTO observation at block **26,184,897** and the ancestor's explicit deny-all policy produced three optional candidates among 19 measured owner–spender pairs. The demonstration returned `complete_reviewed_bundle`, with three received candidates, zero missing, zero unexpected, and zero duplicates. Two candidates have zero token balances; those positive allowances are still included. This command is an offline historical replay, not a new chain measurement. It writes no file and makes no network request.

Single-draft validation already exists in Draft Witness. Draft Bundle adds whole-handoff completeness: dropping one candidate or replacing it with a duplicate cannot pass even when each remaining object individually passes Draft Witness. JSON types are compared strictly, including evidence anchors: `true` and `1.0` cannot substitute for chain ID `1`. An added gas/fee field or modified calldata is an unexpected candidate and leaves the original candidate missing.

To print a bundle from your own reviewed workspace evidence:

```sh
python3 -B line-2/tools/draft-bundle/draft_bundle.py --observation path/to/inventory.json --policy path/to/policy.json --emit
```

Save that printed JSON inside the workspace if you want a handoff file. It contains `schema`, `chain_id`, `token_address`, `block_number`, `block_hash`, and `drafts`; each draft is the complete optional candidate object emitted by Approval Draft. Then verify the received file against the same explicit evidence and policy:

```sh
python3 -B line-2/tools/draft-bundle/draft_bundle.py --observation path/to/inventory.json --policy path/to/policy.json --bundle path/to/bundle.json
```

Without `--bundle`, the tool reconstructs and checks its own expected bundle, so that mode demonstrates the checker rather than validating a received handoff. `--emit` only prints a bundle and never signs or sends it. Inputs are restricted to files resolving inside the current workspace, at most 96 KiB each, with duplicate JSON keys refused. A bundle has at most 64 candidates and exactly the documented top-level keys. Exit codes: **0** match (including a sufficient review with no candidates), **3** mismatch, **4** insufficient evidence, **1** invalid input. Emitting from insufficient evidence exits 1 without a bundle.

Completeness is deliberately limited to candidates derived from the supplied measured inventory and policy. An empty matching bundle does not mean a safe or completely audited wallet. Unknown spenders, Permit2, signatures and custom permissions remain outside coverage. RPC evidence is trusted and historical; this tool does not establish canonicality or freshness. Use the existing refresh/age tools and independent owner review as needed. A candidate is optional and never authorizes a transaction.

Run the focused tests:

```sh
python3 -B -m unittest discover -s line-2/tools/draft-bundle -p 'test_*.py' -v
```

The tests exercise the real historical three-candidate bundle, order independence, omissions, replacement by a duplicate, altered transactions, strict anchor types, insufficient evidence, a sufficient policy with no candidates, malformed bundles and JSON round-tripping. Additional CLI tests exercise exit codes and bounded workspace file loading.
