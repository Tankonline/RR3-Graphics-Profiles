[← Back to README](../README.md)

# How the encryption was reverse engineered

This is a record of how the keystream in `tools/rr3gfx.py` was recovered, so the work can be checked or repeated
for another RR3 version. The method below needs only the game's data files and its own log output.

## 1. First observations

- The `.plist` and `.feats` files looked random, with no readable text and no known compression header.
- The same 16 bytes started every `.plist` (`e6 ea 60 c5 …`), and a different 16 bytes started every `.feats`
  (`e6 86 70 c9 …`). Real compression or a proper cipher with a random IV wouldn't do that. It pointed to
  **the same keystream applied from byte 0** to plaintexts that begin with the same text.
- **XOR of two files of the same type** gave bytes that were almost all small values. Wherever the plaintexts
  match, the result is `0x00`, and elsewhere it's the XOR of two ASCII characters (< `0x80`). That is what a
  shared XOR keystream produces: the keystream cancels out.
- A `.plist` XORed with a `.feats` also gave only 7-bit values, so **both types share one keystream**.
- No short repeat period showed up, so it's a long keystream, not a short repeating key.

So: `stored = text XOR K`, with one long `K`. Recovering `K` means knowing (or deducing) the plaintext of at least
one file, byte for byte.

## 2. Known plaintext from the game's own log (bytes 0 to 6,792)

When RR3 starts it writes its active settings to logcat:

```
3DSceneScale = 0.800000 nScreenSize = 2340x1080
Current settings:
  "3D_SCENE_SCALE" -
0.800000 : FLOAT
  "AA_LEVEL" -
0 : INT
  "ALLOW_RETINA" -
true : BOOL
…
```

That's every key, value and type of the active preset (`AndroidLow` at the time). It was turned back into
an Apple XML plist. The writing style wasn't known, so formatting variants were tried until one fitted exactly:

| Choice | Fits |
|---|---|
| line endings | **CRLF** |
| indent | **one tab** |
| floats | **short form**, always with at least one decimal (`1.0`, `0.005`), not the log's `0.800000` |
| key order | **ASCII sorted** (same as the dump) |
| multi-line strings | **CRLF** inside the string |

The right variant is exactly **6,793 bytes, the size of `AndroidLow.plist`**. XORing it with the file gives
`K[0..6792]`. Applying that `K` to all the other files gives clean, plausible XML everywhere, which confirms it.

One value was later found to be wrong: the dump shows `3D_SCENE_SCALE` as `0.800000`, but the file stores `1.0`.
RR3 computes the scene scale at runtime from the screen size (the `3DSceneScale = … nScreenSize = …` line), so
the dump shows the computed value, not the stored one. That put two keystream bytes (210 and 212) wrong. See
section 5.

## 3. Extending to 6,990 bytes (every `.plist`)

Several presets are longer than `AndroidLow`, up to 6,990 bytes (`iPhone`). Beyond byte 6,792 their plaintext was
unknown, but heavily constrained:

- Every plist has the same 113 keys in the same sorted order, so the last few keys and the closing
  `</dict>␍␊</plist>␍␊` are known.
- Working backwards from each file's end gives the exact text, apart from values. Most of the values at the end
  are booleans (`<true/>`/`<false/>`).
- Each candidate combination of values has to fit the file's exact length. It must also decode the *other*
  files (shorter or longer at that byte) to valid text.

Enumerating these length-constrained combinations, and scoring each candidate keystream byte against all 42
`.feats` files at the same position (which must stay valid `<Key>`/`<Value>` text), gave a unique answer up to
6,990 bytes. **All 41 plists then decoded to well-formed XML.**

## 4. Extending to 10,420 bytes (every `.feats`)

`.feats` files run to 10,420 bytes. Their structure is rigid:

```
␠␠␠␠<Key>NAME</Key>␊␠␠␠␠<Value>true|false</Value>␊   (repeated)
```

Only the key names and the true/false values are unknown, and **every file has the same keys in the same
order**.

The useful insight is the **shift between files**. Files differ in device-name length and in how many `false`
values they have, so the same key sits at a slightly different byte offset in each file. By byte ~6,900 the 42
files fall into 14 groups spread over 24 bytes. At any byte position:

- the file furthest ahead may be spelling a new, unknown character;
- the files behind it are at text the leader has **already revealed**, so their plaintext is known and they
  determine `K[i]`;
- then `K[i]` reveals the leader's new character.

A search walks forward one byte at a time:

1. For each file, list the characters its grammar allows next. These are fixed text, a known key name, or
   `true`/`false`. While a name is being spelled, a file that's behind follows the name the leading file has
   *partly* spelled so far.
2. Keep only the keystream values that every file allows.
3. If more than one is left, take the best-supported one and remember the others. A later contradiction (no
   value allowed, or two spellings of the same key) rewinds to the last choice.

The first version only followed key names that were *complete* in some file. It stalled at byte 9,854, at
`LENS_DISTORTION_CHROMATIC_ABERRATION` (36 characters): once every file was inside that name at the same time,
it was guessing blind. After adding partial-name following, and making every ambiguous step reversible, the
search reached **10,420 bytes with no guesses at all**.

`mac.feats` was left out of the search. It's the only file in the furthest-ahead group, so nothing could check
it, and it showed an apparent `<Vamum>` typo. It was decoded afterwards with the finished keystream.

## 5. Correcting bytes 210 and 212

With the full keystream, 29 of the 42 `.feats` failed XML parsing, all around line 9 or 10, in the part
recovered from the plist. The damage sat at different text positions in different files, which pointed to bad
keystream bytes rather than bad files. The `mac.feats` "typo" `<Vamum>` was the same error.

The fix used the rigid structure: each `.feats` plaintext was rebuilt exactly from its own list of keys and
values. That's `header + pairs + footer`, and it has to come out at the file's exact length. XORing each rebuilt
file with the stored file gives the keystream directly.

- 40 of the 42 files rebuilt cleanly (in the other two the damage hit a key name).
- Those 40 files **agree on every byte**. They differ from the old keystream at exactly two positions: 210
  (`0x83` → `0x82`) and 212 (`0x9a` → `0x92`).
- In the plists those two bytes are the value of `3D_SCENE_SCALE`: `0.8` becomes `1.0`, which is consistent with
  section 2.

## 6. Verification

With the final keystream (10,420 bytes, SHA-256 `b8700d28…d3d9`):

- all 41 `.plist` files parse as XML, and `PLIST_IDENTIFIER` matches the file name in every one;
- all 42 `.feats` files parse as XML, `Device name` matches the file name, and all have the same 190 keys;
- `compile(decompile(x)) == x` for all 83 files (`rr3gfx.py verify`, and the unit tests);
- edited files (HDR levels A, B and C) load in RR3 14.0.1 on a real device, so the format and the plaintext
  style RR3 accepts are confirmed.

## 7. Repeating this for another version

1. Check whether the keystream is the same: `rr3gfx.py decompile` the new files. If they come out as valid XML,
   you're done.
2. If not, check that the same-type XOR still gives 7-bit output (same scheme, new key).
3. Get known plaintext. RR3's `Current settings:` log is the best source, but don't trust values RR3 computes
   at runtime (`3D_SCENE_SCALE`).
4. Use the shared key order and the shifts between files to extend the keystream, as in sections 3-4. Then
   cross-check every byte with the rebuild method in section 5.
