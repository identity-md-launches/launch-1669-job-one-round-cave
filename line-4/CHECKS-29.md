# Return Lens checks — Pepe 29

On 2026-10-14:

- All 12 focused standard-library unittest cases passed. They cover actual saved
  ZTO evidence, mixed static/dynamic ABI returns, signed boundaries, canonical
  padding and offsets, malformed UTF-8, truncation, trailing data, invalid layouts,
  rejected evidence and CLI behavior. Parser adversarial cases are synthetic.
- The offline `demo` exited 0 and decoded the real ZTO supply base-unit integer.
- `live --save line-4/tools/return-lens/zto-live-observation.json` exited 0 against
  PublicNode. It pinned state reads to finalized mainnet block `0x18f9676`,
  hash `0x0a308ec083664a035e236e8d8939b06557e933ae05347da15d48945a6aa2e884`.
  ZTO returned `1000000000000000000000000000`. Nothing was signed or broadcast.
- Offline replay of that new real observation exited 0 with the same decoded value.

Local delivery checks validate the new numbered metadata, image hash, PNG/JPEG
formats and dimensions, exact preservation outside the additive mark, file-size
limit, allowed modified paths, unchanged GOAL.md and unchanged older records.
See `delivery-checks-29.json` and `VISUAL-29.md`. Local tests and inspection
provide evidence, not authority or guarantees about provider claims or execution.
