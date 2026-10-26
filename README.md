# RR3 Graphics Profiles

Every graphics profile shipped with **Real Racing 3 14.0.1**, in both the game's encrypted form and as readable
XML, plus **`rr3gfx`**: a small, dependency-free tool that decompiles and compiles them byte for byte.

It also documents a fix for a **black screen after loading** that some newer GPUs hit (confirmed on an Adreno 840):
RR3 needs its HDR render path switched on.

> **Disclaimer.** Real Racing 3 and its game files are the property of Electronic Arts Inc. This is an unofficial
> fan project. It is not affiliated with, endorsed by or supported by EA or Firemonkeys. The profile files are
> included for interoperability, preservation and modding research after the game's online services closed.
> If you are a rights holder and want them removed, open an issue and they will be taken down. The tool and the
> documentation are released under the MIT licence; the game data is **not** covered by that licence.
> Editing game files is at your own risk: back up first.

---

## Contents

- [What is in this repository](#what-is-in-this-repository)
- [Quick start](#quick-start)
- [The black-screen fix (HDR)](#the-black-screen-fix-hdr)
- [How RR3 picks a profile](#how-rr3-picks-a-profile)
- [Installing an edited profile on a device](#installing-an-edited-profile-on-a-device)
- [The file format in one minute](#the-file-format-in-one-minute)
- [Tool overview](#tool-overview)
- [Verifying the repository](#verifying-the-repository)
- [FAQ](#faq)
- [Further documentation](#further-documentation)
- [Credits and licence](#credits-and-licence)

---

## What is in this repository

```
profiles/
  compiled/          The original files, exactly as RR3 ships them (encrypted).
    eds/             41 render presets        <Device>.plist
    feats/           42 shader feature files  <Device>.feats
  decompiled/        The same files as readable XML (byte-exact inverse of compiled/).
    eds/
    feats/
tools/
  rr3gfx.py          Decompiler / compiler / inspector (Python 3.8+, standard library only).
  gen_docs.py        Regenerates docs/PRESETS.md and docs/SETTINGS_REFERENCE.md.
  tests/             Unit tests (round trip of every profile, safety checks, CLI).
docs/
  FORMAT.md              Exact byte-level description of both file types.
  REVERSE_ENGINEERING.md How the encryption was worked out, step by step.
  HDR_BLACK_SCREEN.md    The black-screen investigation, evidence and fix levels.
  PRESETS.md             Table of all 41 presets (generated).
  SETTINGS_REFERENCE.md  Every render setting and shader feature with its values (generated).
  TOOL.md                Full rr3gfx command reference.
```

Source: `files/apk/res/eds` and `files/apk/res/feats` from the Android ROW build (`com.ea.games.r3_row`)
of RR3 14.0.1. `compiled/` is a byte-for-byte copy of them.

## Quick start

You need Python 3.8 or newer. Nothing to install.

```sh
# Readable copy of one profile (writes AndroidHigh.decompiled.plist next to it)
python tools/rr3gfx.py decompile profiles/compiled/eds/AndroidHigh.plist

# ...or just open the ready-made one:
#   profiles/decompiled/eds/AndroidHigh.plist

# Edit it in any text editor, then compile it back into a file RR3 loads
python tools/rr3gfx.py compile my_edits/AndroidHigh.plist -o AndroidHigh.plist

# Summary of a profile (works on compiled and decompiled files)
python tools/rr3gfx.py info profiles/compiled/eds/AndroidHigh.plist

# What differs between two presets?
python tools/rr3gfx.py diff profiles/compiled/eds/AndroidHigh.plist profiles/compiled/eds/AndroidXtraHigh.plist

# Apply the black-screen fix to a preset (output stays in the same format as the input)
python tools/rr3gfx.py hdr profiles/compiled/eds/AndroidHigh.plist --level B -o AndroidHigh.plist
```

On Windows use `py -3` instead of `python` if `python` is not on your PATH.

**Editing tips**

- Keep the line endings: `.plist` files use **CRLF**, `.feats` files use **LF**. `compile` warns when they
  differ, and `compile --eol` fixes them.
- Keep the XML valid. `compile` refuses files that don't parse, so you can't produce a file RR3 would choke on.
- Files can't be longer than **10,420 bytes**, the length of the recovered keystream.
  - `.plist` files (6,773-6,990 bytes) have over 3 KB of room.
  - `.feats` files (10,386-10,420 bytes) have **0-34 bytes** of room. Each `true` → `false` adds one byte, so on
    the longest files (`iPhone2,1`, `iPhone3,1`, `iPhone3,3`) you can only switch features *on*, unless you
    switch others on to make room. `compile` tells you if a file is too long.

## The black-screen fix (HDR)

**Symptom:** RR3 loads, the 3D scene appears for a moment, then the screen goes black. The game doesn't crash.

**Cause (device-tested):** on the tested GPU, every preset with **HDR post-processing off** goes black, and every
preset with it on works. That held for all 17 presets tried. Most Android presets ship with HDR off, including
the one RR3 picks automatically on that phone (`AndroidHigh`).

**Fix:** switch the HDR path on. Three levels were tested by patching `AndroidHigh`:

| Level | Switches set to `true` | Result |
|---|---|---|
| A | `USE_HDR_POST_PROCESS` | still black |
| **B** | A + `TONEMAP` + `GAMMA_CORRECTION` | **works** (recommended) |
| C | B + `ENV_MAP_HDR` + `USE_HDR_AUTOMATIC_EXPOSURE` | works (more effects, more GPU load) |

```sh
python tools/rr3gfx.py hdr profiles/compiled/eds/AndroidHigh.plist --level B -o out/AndroidHigh.plist
```

Only those switches change; every other byte stays identical. Full details:
[docs/HDR_BLACK_SCREEN.md](docs/HDR_BLACK_SCREEN.md).

Tested on: Samsung SM-S948B (Adreno 840), Android 16, RR3 14.0.1 ROW. Other GPUs may not need the fix.

## How RR3 picks a profile

- RR3 chooses a **preset name** for the device (on Android: `AndroidLow`, `AndroidMid`, `AndroidMid2`,
  `AndroidHigh`, `AndroidXtraHigh`, `AndroidUltraWide`; `SimRigTV` also exists).
- It loads `eds/<name>.plist` (render settings), then the `.feats` file named after that plist's
  `PLIST_IDENTIFIER` value (shader features).
- Files in the game's writable `.depot` folder override the factory copies in `apk/res`.

A useful trick is the **universal override**: copy one preset's bytes over all seven Android names, so the game
uses it whatever tier it detects. RR3 logs `Settings file loaded, but had an invalid ID` for the renamed copies,
but it still uses them, and it then loads the `.feats` that matches the identifier inside the file.

See [docs/PRESETS.md](docs/PRESETS.md) for every preset's screen size, renderer, HDR state and more.

## Installing an edited profile on a device

Paths for the ROW build (replace the package name for other builds):

```
/storage/emulated/0/Android/data/com.ea.games.r3_row/files/apk/res/eds/    factory presets (leave alone)
/storage/emulated/0/Android/data/com.ea.games.r3_row/files/apk/res/feats/  factory features (leave alone)
/storage/emulated/0/Android/data/com.ea.games.r3_row/files/.depot/eds/     overrides RR3 actually loads
/storage/emulated/0/Android/data/com.ea.games.r3_row/files/.depot/feats/
```

1. **Close RR3 completely** (force stop).
2. **Back up** `.depot/eds` and `.depot/feats` first.
3. Copy your **compiled** file over the preset your device uses, e.g. with adb:
   ```sh
   adb push AndroidHigh.plist /storage/emulated/0/Android/data/com.ea.games.r3_row/files/.depot/eds/AndroidHigh.plist
   ```
   On Android 11+ the `Android/data` folder isn't reachable from normal file managers. adb, or a tool that uses
   Shizuku or root, can usually write there.
4. Start RR3. To undo, put your backup back (or copy the factory file from `apk/res`).

Only ever copy **compiled** files to the device. A decompiled (plain XML) file is not what RR3 expects.

## The file format in one minute

- Both file types are **plain-text XML XORed with one fixed keystream**. It's the same keystream for every file of
  both types, applied from byte 0. There is no compression, header, checksum or signature.
- Because XOR is its own inverse, the same operation encrypts and decrypts, and edited files load fine.
- `.plist`: an Apple XML property list, CRLF line endings, tab indentation, 113 keys in alphabetical order.
- `.feats`: `<ShaderFeatures><Device name="…">` followed by 190 `<Key>`/`<Value>` pairs, LF line endings, with
  the same keys in the same order in every file.

Exact details: [docs/FORMAT.md](docs/FORMAT.md). How it was worked out:
[docs/REVERSE_ENGINEERING.md](docs/REVERSE_ENGINEERING.md).

## Tool overview

| Command | What it does |
|---|---|
| `decompile <file-or-folder> [-o OUT]` | encrypted → readable XML (validated) |
| `compile <file-or-folder> [-o OUT] [--eol]` | readable XML → encrypted (validated, round-trip checked) |
| `info <file>…` | identifier, screen, renderer, HDR switches, key counts |
| `verify <file-or-folder>` | check that every file round-trips byte for byte |
| `hdr <plist> --level A\|B\|C` | switch on the HDR black-screen fix |
| `diff <a> <b>` | list settings that differ (any mix of compiled/decompiled) |
| `keystream [--export FILE]` | show the keystream's size and hash, or save it |

Folders are processed recursively, and the folder structure is mirrored in the output. Safety features:

- XML is parsed and checked before anything is written.
- Entity / internal-DTD declarations are refused (protects against "billion laughs" style files).
- An input is never overwritten unless you pass `--in-place`.
- The embedded keystream is SHA-256 checked at start-up.

Full reference: [docs/TOOL.md](docs/TOOL.md).

## Verifying the repository

```sh
python tools/rr3gfx.py verify profiles                 # expect: verify: 166 ok, 0 failed
python -m unittest discover -s tools/tests -v          # round trips, line endings, safety, CLI
python tools/gen_docs.py                               # regenerates the two tables; git diff should be empty
```

`.gitattributes` marks `profiles/compiled` as binary and `profiles/decompiled` as `-text`, so git never rewrites
their line endings. If a clone fails `verify`, check `git config core.autocrlf` and re-clone.

## FAQ

**Does this work for other RR3 versions?** The keystream was recovered from 14.0.1 files. Every 14.0.1 file
decodes. For other versions, try `rr3gfx.py decompile` on their files: if the keystream is the same, you get
valid XML; if not, the tool reports an XML error and writes nothing.

**Does it work for iOS?** The presets for Apple devices are in the same files, so they decode. Installing them on
iOS is outside this project's scope.

**Why is `3D_SCENE_SCALE` 1.0 in every preset when the game logs 0.8?** RR3 computes the scene scale at runtime
from the screen size (it logs `3DSceneScale = 0.800000 nScreenSize = 2340x1080`). The stored value really is
1.0. That value was also the one place an earlier keystream guess was wrong; see the reverse-engineering notes.

**What is `mac.feats`?** A shader feature file with no matching preset. It isn't used on Android. It's included
for completeness.

**Can I add settings that aren't in the file?** The tool will compile any valid XML that fits in 10,420 bytes,
but whether RR3 reads a key it doesn't ship with is untested.

## Further documentation

- [docs/FORMAT.md](docs/FORMAT.md): byte-level format of both file types
- [docs/REVERSE_ENGINEERING.md](docs/REVERSE_ENGINEERING.md): how the keystream was recovered
- [docs/HDR_BLACK_SCREEN.md](docs/HDR_BLACK_SCREEN.md): the black-screen investigation
- [docs/PRESETS.md](docs/PRESETS.md): all presets at a glance
- [docs/SETTINGS_REFERENCE.md](docs/SETTINGS_REFERENCE.md): every key and its values
- [docs/TOOL.md](docs/TOOL.md): rr3gfx reference
- [CONTRIBUTING.md](CONTRIBUTING.md) · [CHANGELOG.md](CHANGELOG.md)

## Credits and licence

Research, testing and tooling by the Project RETR0 team. Tool code and documentation: [MIT](LICENSE).
Real Racing 3 game data (everything under `profiles/`) © Electronic Arts Inc., not covered by the MIT licence;
see the disclaimer at the top.
