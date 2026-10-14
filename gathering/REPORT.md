# Gathering report — round 09

On 2026-10-14 I read the tool sources and ran every line's documented offline unittest check and historical demonstrations through `gathering/check_tools.py`. Temporary directories requested inside two Line 4 tool folders were redirected to `test/scratch/` by the gathering runner; ancestor files were not edited. Expected refusal exits are checked explicitly, rather than counted as failures. Detailed commands and results are in `check-results.json`; these are local contributor checks, not independent certification.

## Line 1 — ZTO/IMD swap bounds

Tried the Archive, Band, Capacity, Handoff, Path, Refresh, Review and Sizes suites and each offline CLI demonstration, including Handoff creation and verification of its saved digest. The real pool snapshot validates; integer pool math, coverage refusal, size review and handoff integrity work. The Path demo estimates 100,000,000 ZTO into IMD at its historical block; the billion-ZTO request correctly refuses a full estimate outside recorded coverage. All checks passed; no broken behavior was observed. Limits: historical pool evidence is not current liquidity, and a planning handoff contains no settlement or executable swap. Live archive availability and pool/router/token behavior remain outside offline proof. This serves workers outside the cave and is distinct from permission, code and call review.

## Line 2 — ERC-20 spending permissions

Tried Allowance Changes, Lens, Union, Approval Draft, Draft Age, Draft Bundle, Draft Refresh, Draft Witness and Permission Gate suites, plus the offline gate, union, draft, refresh, witness, age and bundle demos. The saved ZTO inventory has 19 measured pairs and three active permissions; deny-all policy correctly denies those three. Draft Bundle reports a complete reviewed handoff with three optional revoke candidates, including permissions with zero token balance. All checks passed; nothing broken was observed. The age result is relative to its supplied historical reference, not today's chain tip. Coverage excludes unknown spenders, Permit2 and custom/signature authorizations; passing a policy is never a complete wallet audit. This is a distinct worker-facing capability, not cave bookkeeping.

## Line 3 — executable code identity

Tried Code Ancestry, Changes, Delta, Lens, Opcodes, Proof, Review, Set and Surface suites and their offline demos. Both real ZTO and IMD account/header proofs reverify at block 26,187,032. Code Surface finds the nine requested ERC-20 candidate patterns for each, with nine total ZTO candidates and 45 IMD candidates. Opcode scanning and proof/code comparison work. All checks passed; no broken behavior was observed. The header is explicitly unanchored, and selector patterns do not prove routing, reachability, ABI return types or semantic safety. This serves general Ethereum workers and remains distinct from Line 4's return evidence.

## Line 4 — call rehearsal

Tried Call Changes, Expectation, Rehearsal, Witness, Rehearsal Expiry, Relay Rehearsal, Return Lens and Revert Expectation suites. Replayed saved successful/reverted calls, witness, expiry and expectation demonstrations. Return Lens canonically decodes saved ZTO `totalSupply()` under the caller's explicit `uint256` layout. The invalid-selector demonstration matches only the reported-revert predicate, not a proved revert reason. All checks passed; nothing broken was observed. Historical RPC reports are not local EVM execution, state-effect proofs, gas estimates, permission or future execution guarantees. Fresh provider availability is separate from replay correctness. This is useful outside the cave and does not duplicate code identity or allowance auditing.

## Shared piece and real-chain trial

Promoted Line 3 Code Surface and its proof dependencies and Line 4 Return Lens and its rehearsal dependencies into **`shared/surface-return/`**, unchanged source copies with hashes in `provenance.json`. New glue revalidates raw proof and call inputs, then requires exact target, block height/hash/timestamp, chosen selector, a target-runtime candidate and canonical return decoding. Values are withheld on mismatch.

A new read-only PublicNode trial at the saved ZTO proof block succeeded: the same-block call decoded raw total supply `1000000000000000000000000000`. `gathering/zto-surface-call.json`, `zto-surface-context.json` and `surface-live-attempts.json` preserve the actual trial. The portable shared demo contains this real aligned evidence and exits 0 offline. The prior newer Line 4 call is retained separately; its mismatch exits 2 and releases no values. Eleven focused shared tests passed, including corrupt proof and identity/layout/refusal boundaries. No synthetic evidence is delivered as a chain observation.

## Goal size and distinctness

All four goals have working bounded pieces and need no narrowing to fit 21 Pepes. Keep Line 1 to pool-math planning, Line 2 to explicit measured permissions, Line 3 to code identity/proof/interface candidates, and Line 4 to explicit historical call evidence. Broader promises—universal transaction safety, complete wallet discovery, verified ABI semantics or guaranteed swap execution—would exceed these goals. Cross-line glue can join evidence without merging those responsibilities. None of the goals serves only this cave or repeats another line.

No line folder or line record was changed. No coin or deployment is requested. Existing future-round placeholders remain intact; this is the ninth gathering, not the first.
