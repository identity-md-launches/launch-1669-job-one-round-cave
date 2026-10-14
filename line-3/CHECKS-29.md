# Code Surface checks

Executed locally on 2026-10-14 from the repository root:

```sh
python3 -B line-3/tools/code-surface/demo.py
python3 -B -m unittest discover -s line-3/tools/code-surface -p 'test_*.py' -v
```

The demo returned `demonstration_passed: true`. It reconstructed real saved ZTO and IMD proofs at block 26,187,032, finding all nine requested selectors in each; total candidate counts were 9 and 45. Both anchors remain `unanchored-rpc-header`, and no reachability, complete interface or safety claim is granted.

All **25 tests passed** in the final focused suite (0 failures, 0 errors). The checks cover canonical signature vectors/types, malformed inputs and bounds, known selector collisions, PUSH operand exclusion, valid instruction-boundary jump targets, truncated code, short selector constants, unreachable patterns, metadata annotation without suppression, beacon/path deduplication, corrupt proofs, a forged self-consistent observation, separate anchor equality, complete counts behind bounded previews, workspace boundaries, duplicate JSON keys and CLI success/error output. A synthetic reconstructed proof tests large candidate inventories without presenting that fixture as a chain observation.

No predecessor implementation was modified. Runtime dependencies are already committed standard-library Python files. The new demo works offline; no network service or installed package is needed during verification. Test reports are the contributor's own local evidence, not independent certification.

Delivery and visual checks are recorded separately in `delivery-checks-29.json` and `visual-checks-29.json` after inspecting the final PNG and JPEG.
