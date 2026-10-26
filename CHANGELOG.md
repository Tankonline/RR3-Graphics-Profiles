# Changelog

## 1.0.0 (2026-10-26)

First public release.

- All 41 render presets (`eds/*.plist`) and 42 shader feature files (`feats/*.feats`) from Real Racing 3
  14.0.1 (Android ROW build), in compiled (original) and decompiled (XML) form.
- `tools/rr3gfx.py` 1.0.0: `decompile`, `compile`, `info`, `verify`, `hdr`, `diff`, `keystream`.
  - Embedded 10,420-byte keystream, which covers every shipped file.
  - XML validation, entity / DTD refusal, line-ending checks, and a round-trip check on every write.
- `tools/gen_docs.py`: generates `docs/PRESETS.md` and `docs/SETTINGS_REFERENCE.md`.
- `tools/tests/`: byte-exact round trip of every profile, line endings, identifiers, the shared feats key list,
  safety checks and the CLI.
- Documentation: format, reverse engineering, the HDR black-screen fix, presets, settings reference, tool
  reference.
