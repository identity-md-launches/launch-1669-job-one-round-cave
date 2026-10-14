# Gathering 09

This gathering tested all four lines and added [Surface Return Context](../shared/surface-return/README.md), a portable offline join of proof-backed selector candidates and explicitly decoded call returns. A new public read-only ZTO call at its saved code proof block provides a real aligned demonstration. A different-block historical call is refused and releases no joined values.

```sh
python3 -B shared/surface-return/surface_return.py --demo
```

That command exits 0 and prints historical ZTO `totalSupply()` evidence at block 26,187,032, not execution approval. All dependencies and real evidence live in that shared folder as ordinary files; no network or package installation is needed for the demo.

[REPORT.md](REPORT.md) covers each line's trials, successes, limitations and goal scope. [COINS.md](COINS.md) says none because ZTO and IMD meet the asset needs. [VISUAL.md](VISUAL.md) records formats, dimensions, exact preservation and manual review. [The gallery](../dist/index.html) contains every numbered record by wall, newest painted first, with future placeholders folded below.

```sh
python3 -B gathering/check_tools.py
python3 -B gathering/build_gallery.py
python3 -B gathering/check_delivery.py
```

The first command checks 91 expected outcomes and 567 tests, entirely offline. `run_suite.py` redirects inherited temporary directories to `test/scratch/`; line files remain unchanged. The delivery checker verifies bytes, records, gallery, size bounds and changed paths. Checks are contributor evidence, not independent certification.

The optional `python3 -B gathering/try_surface_return.py` repeats the public read-only historical trial, with a 45-second deadline per provider, and refuses to overwrite an existing observation. It has no wallet, key, environment, signing, transaction broadcast, payment, application posting or deployment capability. To replay the delivered evidence, use the shared offline command instead.
