## Summary

Describe what this pull request changes and why.

## Checks

Run all three commands from the repository root and confirm the results:

```sh
python tools/rr3gfx.py verify profiles
python -m unittest discover -s tools/tests -v
python tools/gen_docs.py && git diff --exit-code docs
```

- [ ] Profile verification passes (`166 ok, 0 failed`)
- [ ] Unit tests pass
- [ ] Generated documentation is up to date
- [ ] I did not modify anything under `profiles/`
- [ ] I did not weaken or remove `.gitattributes` rules
- [ ] I did not hand-edit `docs/PRESETS.md` or `docs/SETTINGS_REFERENCE.md`

## Notes for reviewers

Include testing details, screenshots, or documentation notes as appropriate.
