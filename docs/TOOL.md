[← Back to README](../README.md)

# rr3gfx reference

`tools/rr3gfx.py` is a single-file tool for Python 3.8+ that uses only the standard library. Copy it anywhere and
run it:

```sh
python rr3gfx.py <command> [options]        # Windows: py -3 rr3gfx.py ...
python rr3gfx.py --version
python rr3gfx.py <command> --help
```

Exit code: `0` on success, `1` if any file failed (the others are still processed).

Terms used below:

- **compiled**: the encrypted file as RR3 stores it.
- **decompiled**: the readable XML.

The tool tells them apart by content. A decompiled file starts with `<?xml` (plist) or `<ShaderFeatures>`
(feats). The type comes from the extension (`.plist` or `.feats`).

---

## decompile

Encrypted game file(s) → readable XML.

```sh
python rr3gfx.py decompile <file-or-folder> [-o OUTPUT] [--in-place] [-q]
```

| Input | Default output |
|---|---|
| a file `X.plist` | `X.decompiled.plist` next to it |
| a folder `dir/` | `dir_decompiled/`, with the same sub-folders |
| `-o out/` | `out/<relative path>` |
| a file with `-o name.plist` | exactly `name.plist` |

- Files that are already decompiled are skipped (`skip`).
- Each result is checked as XML before it's written. A file that doesn't decode (wrong game version, damaged
  file) is reported and nothing is written for it.
- The input is never overwritten unless you pass `--in-place`.

```sh
python rr3gfx.py decompile profiles/compiled -o my_profiles -q
# decompile: 83 written, 0 skipped, 0 failed
```

## compile

Readable XML → encrypted game file(s) that RR3 loads.

```sh
python rr3gfx.py compile <file-or-folder> [-o OUTPUT] [--in-place] [-q] [--eol]
```

Output naming is the same as `decompile`, with `.compiled` / `_compiled`. Before writing, `compile`:

1. checks the XML parses, has the right root (`<plist><dict>` or `<ShaderFeatures><Device>`), and contains no
   `<!ENTITY>` or internal DTD;
2. checks line endings. RR3 uses CRLF in `.plist` and LF in `.feats`. Any other style gives a warning, and
   `--eol` converts it for you;
3. checks the file fits in the keystream (10,420 bytes);
4. encrypts it, then decrypts the result again and compares, to be sure the round trip is exact.

```sh
python rr3gfx.py compile edited/AndroidHigh.plist -o AndroidHigh.plist --eol
```

## info

A short summary of one or more profiles, compiled or decompiled.

```
$ python rr3gfx.py info profiles/compiled/eds/AndroidHigh.plist profiles/decompiled/feats/AndroidHigh.feats
AndroidHigh.plist
  type       : plist (compiled), 6808 bytes, sha256 2fc793914a2417f7...
  identifier : AndroidHigh
  notes      : High-end Android devices
  screen     : 480x320  gui layout _480x320  high-res menu false
  renderer   : GL_ES_2  scene scale 1.0  AA 0
  hdr        : USE_HDR_POST_PROCESS=false  TONEMAP=false  GAMMA_CORRECTION=false  ENV_MAP_HDR=false  USE_HDR_AUTOMATIC_EXPOSURE=false
  keys       : 113
AndroidHigh.feats
  type       : feats (decompiled), 10409 bytes, sha256 00d8f831208ab94c...
  device     : AndroidHigh
  features   : 190 (171 on, 19 off)
```

## verify

Checks that every file round-trips byte for byte. For a compiled file that means
`compile(decompile(x)) == x`, and for a decompiled one `decompile(compile(x)) == x`.

```sh
python rr3gfx.py verify profiles
# verify: 166 ok, 0 failed
```

Use it after cloning (to catch line-ending damage) or after editing a folder.

## hdr

Switches on the HDR black-screen fix in a `.plist`. See [HDR_BLACK_SCREEN.md](HDR_BLACK_SCREEN.md).

```sh
python rr3gfx.py hdr <plist> [--level A|B|C] [--format same|compiled|decompiled] [-o OUTPUT]
```

| Level | Sets to `<true/>` |
|---|---|
| A | `USE_HDR_POST_PROCESS` |
| **B** (default) | A + `TONEMAP`, `GAMMA_CORRECTION` |
| C | B + `ENV_MAP_HDR`, `USE_HDR_AUTOMATIC_EXPOSURE` |

- Accepts compiled or decompiled input. By default the output has the same format as the input.
- Only those `<false/>` values change, to `<true/>` (each one makes the file 1 byte shorter). Every other byte is
  untouched.
- Each key must appear exactly once, or the command stops without writing anything.
- Default output: `<name>.hdr<LEVEL>.plist` next to the input.

```
$ python rr3gfx.py hdr profiles/compiled/eds/AndroidHigh.plist --level B -o out/AndroidHigh.plist
HDR level B: changed USE_HDR_POST_PROCESS, TONEMAP, GAMMA_CORRECTION
wrote out/AndroidHigh.plist (compiled, 6805 bytes)
```

## diff

Lists the settings that differ between two profiles of the same type. Either one can be compiled or decompiled.

```
$ python rr3gfx.py diff profiles/compiled/eds/AndroidHigh.plist profiles/compiled/eds/AndroidMid.plist
key                                  AndroidHigh.plist  |  AndroidMid.plist
CAR_SHADOW_MAPS                      true  |  false
CUBE_MAP_DIMENSIONS                  512  |  384
...
32 of 113 keys differ
```

Line breaks inside strings are shown as `\n`.

## keystream

```sh
python rr3gfx.py keystream                    # keystream: 10420 bytes, sha256 b8700d28...
python rr3gfx.py keystream --export ks.bin    # raw bytes, e.g. for other tools
```

The keystream is embedded in the script as base64 and checked against its SHA-256 on every start.

## Using it as a library

```python
import sys; sys.path.insert(0, "tools")
import rr3gfx

text = rr3gfx.decompile_bytes(open("AndroidHigh.plist", "rb").read(), "plist")
text, changed = rr3gfx.apply_hdr(text, "B")
data, warnings = rr3gfx.compile_bytes(text, "plist")
settings = rr3gfx.plist_settings(text)          # {key: value-as-text}
name, features = rr3gfx.feats_settings(feats_text)
```

Problems with input files raise `rr3gfx.Rr3GfxError`.

## Security notes

- The tool only reads the files you name and writes where you tell it. It never overwrites its input unless you
  pass `--in-place`.
- XML is parsed with Python's built-in parser. Documents that declare entities or an internal DTD are refused
  before parsing, which blocks entity-expansion ("billion laughs") files. External entities aren't resolved by
  Python's parser.
- No network access, and no code execution from input files.
