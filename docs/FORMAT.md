# File format

This describes the exact bytes of RR3 14.0.1's graphics profiles. Everything here was checked against all 83
shipped files (41 `.plist` + 42 `.feats`).

## 1. Encryption layer (both file types)

```
stored[i] = plain[i] XOR K[i]        for i = 0 .. len(file) - 1
```

- `K` is **one fixed keystream**. It's the same for every file and for both types, it's indexed from the first
  byte of the file, and it doesn't depend on the file name, length or content.
- There is no header, length field, compression, checksum, MAC or signature. The stored file is exactly as long
  as the plaintext.
- Decryption and encryption are the same operation. An edited file is accepted as long as the plaintext is valid.
- The recovered `K` is **10,420 bytes** long (SHA-256
  `b8700d285217c1631d824c9521f3bf392d7f0d9bde79dd4ecb435af4347329c1`). That's exactly the length of the longest
  shipped file. Bytes beyond that are unknown, because no shipped file reaches them.
- `K` has no short period, so it's not a repeating key. It looks like output from a fixed-seed generator, but its
  generator wasn't needed and hasn't been identified.

Recognising files: every compiled `.plist` starts with `e6 ea 60 c5 40 26 f3 88 …` (`<?xml ve…`) and every
compiled `.feats` starts with `e6 86 70 c9 48 63 f7 ab …` (`<ShaderFe…`). The first byte is the same for both
because both start with `<`.

## 2. `.plist` (render settings, `eds/`)

An Apple XML property list, written in one exact style:

```
<?xml version="1.0" encoding="UTF-8"?>␍␊
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">␍␊
<plist version="1.0">␍␊
<dict>␍␊
⇥<key>3D_SCENE_SCALE</key>␍␊
⇥<real>1.0</real>␍␊
⇥<key>AA_LEVEL</key>␍␊
⇥<integer>0</integer>␍␊
⇥<key>ALLOW_RETINA</key>␍␊
⇥<true/>␍␊
…
⇥<key>USE_REALTIME_CAR_SHADOW_MAPS</key>␍␊
⇥<false/>␍␊
</dict>␍␊
</plist>␍␊
```

| Property | Value |
|---|---|
| Encoding | ASCII (declared UTF-8) |
| Line endings | **CRLF** everywhere, including inside multi-line strings |
| Indentation | one **tab** before every `<key>` and value |
| Keys | **113**, the same set in every preset, in plain ASCII (byte) order: `3D_SCENE_SCALE` first, `Notes:` between `MOBILE_INTERNET_4G_NAME_LIST` and `OUTPUT_FOLDER` |
| Value types | `<real>`, `<integer>`, `<string>`, `<true/>`, `<false/>` |
| Reals | shortest form with at least one decimal: `1.0`, `8.0`, `-2.0`, `0.005` |
| Empty strings | `<string></string>` |
| Multi-line strings | lines separated by CRLF inside `<string>`, e.g. `Driver high␍␊A, 4000␍␊B, 2500␍␊C, 60` |
| Ends with | `</plist>␍␊` |
| Sizes | 6,773 bytes (`AppleTV`) to 6,990 bytes (`iPhone`) |

Notable keys:

- `PLIST_IDENTIFIER`: the preset's name. RR3 loads `feats/<PLIST_IDENTIFIER>.feats`.
- `ALL_PLISTS`: a `|`-separated list of all 41 presets, identical in every file.
- `Notes:` and `DEVICE_DESCRIPTION`: human-readable descriptions.
- The HDR switches: `USE_HDR_POST_PROCESS`, `TONEMAP`, `GAMMA_CORRECTION`, `ENV_MAP_HDR`,
  `USE_HDR_AUTOMATIC_EXPOSURE` (see [HDR_BLACK_SCREEN.md](HDR_BLACK_SCREEN.md)).

All keys and their values: [SETTINGS_REFERENCE.md](SETTINGS_REFERENCE.md).

## 3. `.feats` (shader features, `feats/`)

A small custom XML document:

```
<ShaderFeatures>␊
␠␠<Device name="AndroidHigh">␊
␠␠␠␠<Key>FOG</Key>␊
␠␠␠␠<Value>true</Value>␊
␠␠␠␠<Key>ADD_FOG</Key>␊
␠␠␠␠<Value>true</Value>␊
…
␠␠␠␠<Key>MOTION_BLUR_CAMERA_WRITE_ALPHA</Key>␊
␠␠␠␠<Value>false</Value>␊
␠␠</Device>␊
</ShaderFeatures>␊
```

| Property | Value |
|---|---|
| Line endings | **LF** |
| Indentation | 2 spaces for `<Device>`, 4 spaces for `<Key>`/`<Value>` |
| No XML declaration | the file starts directly with `<ShaderFeatures>` |
| `Device name` | always equals the file name without `.feats` |
| Keys | **190**, the **same keys in the same order** in all 42 files (not alphabetical) |
| Values | `true` or `false` only |
| Ends with | `</ShaderFeatures>␊` |
| Sizes | 10,386 bytes (`iPad`) to 10,420 bytes (`iPhone2,1`, `iPhone3,1`, `iPhone3,3`) |

Since every file has the same keys, the size of a file is fixed by its device name length plus its number
of `false` values (`false` is one byte longer than `true`).

`mac.feats` has no matching `.plist` and isn't loaded on Android.

## 4. Size limit when editing

The tool can only encrypt bytes it has a keystream for, so a compiled file can be at most **10,420 bytes**.

- `.plist`: more than 3 KB of room in every preset.
- `.feats`: 0-34 bytes of room. Changing a value from `true` to `false` costs one byte.

Whether RR3 itself would accept a longer file (with keystream bytes nobody knows yet) is untested.

## 5. What RR3 checks when loading

These observations come from logcat while testing on Android:

- A plist copied under a different name (for example `AndroidXtraHigh` content saved as `AndroidHigh.plist`) is
  **accepted**. RR3 logs `Settings file loaded, but had an invalid ID: AndroidHigh.plist`, keeps the settings,
  and loads the `.feats` named after the content's `PLIST_IDENTIFIER`.
- No integrity check was seen: edited files load as long as they are valid.
