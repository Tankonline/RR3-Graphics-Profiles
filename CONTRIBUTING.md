# Contributing

Thanks for helping. The most useful contributions are:

1. **Device results for the HDR black screen.** Open an issue with:
   - device model, GPU, Android version and RR3 version / build (ROW or NA);
   - which preset you used and whether it was black unmodified;
   - which fix level (A, B or C) made it work.
2. **Meanings of settings.** If you have *tested* what a key does, open a pull request that adds it to the
   `CONFIRMED` table in `tools/gen_docs.py` (with a short note on how you tested it), then regenerate the docs.
   Please don't add guesses based only on the key name.
3. **Other RR3 versions.** Run `python tools/rr3gfx.py decompile <their files>` and report whether they decode.

## Ground rules

- **Never edit `profiles/compiled/`.** Those files must stay byte-identical to what the game ships.
- `profiles/decompiled/` must always be the exact decompile of `profiles/compiled/`. If you need edited
  presets, put them in a new folder (for example `profiles/community/<name>/`) and describe them in its own
  README.
- `docs/PRESETS.md` and `docs/SETTINGS_REFERENCE.md` are generated. Change `tools/gen_docs.py` and re-run it
  rather than editing them.
- Keep `rr3gfx.py` to the **standard library only**, and working on Python 3.8.

## Before opening a pull request

```sh
python tools/rr3gfx.py verify profiles                # verify: 166 ok, 0 failed
python -m unittest discover -s tools/tests -v
python tools/gen_docs.py && git diff --exit-code docs # generated docs are up to date
```

Line endings matter: `.gitattributes` keeps git from touching `profiles/`. If `verify` fails after a clone,
check `git config core.autocrlf` and re-clone.
