[← Back to README](../README.md)

# The HDR black screen

## Summary

On the test device, Real Racing 3 shows a **black screen after loading** whenever the active graphics preset has
**HDR post-processing switched off**. Switching on `USE_HDR_POST_PROCESS`, `TONEMAP` and `GAMMA_CORRECTION`
(fix level **B**) fixes it, without changing anything else in the preset.

```sh
python tools/rr3gfx.py hdr AndroidHigh.plist --level B -o fixed/AndroidHigh.plist
```

## Test setup

| | |
|---|---|
| Device | Samsung SM-S948B |
| GPU | Qualcomm Adreno 840 |
| OS | Android 16 (API 36) |
| Game | Real Racing 3 14.0.1, ROW build (`com.ea.games.r3_row`) |
| Preset RR3 picks by itself | `AndroidHigh` (HDR **off** in the factory file) |

Method: copy one preset's compiled `.plist` over all seven Android preset names in `.depot/eds`, so the game uses
it whatever tier it detects. Then start the game and watch the screen and logcat.

## Symptom

- Loading completes, and the 3D scene renders briefly.
- Then the picture (menu and scene) goes **black**.
- The process keeps running: there's no crash, no ANR and no tombstone.

## Evidence

**17 presets were tested unmodified.** The result matched the preset's HDR switches every time:

| Result | Presets |
|---|---|
| **works** | `AndroidXtraHigh`, `SimRigTV`, `AppleTV`, `AppleTV5,3`, `iPad` |
| **black** | `AndroidLow`, `AndroidMid`, `AndroidMid2`, `AndroidHigh`, `AndroidUltraWide`, `iPad1,1`, `iPad2,1`, `iPad2,2`, `iPad2,3`, `iPad2,5`, `iPad3,1`, `iPad3,2` |

Comparing all 41 decoded presets, these keys are **on in every working preset and off in every black one**:

- `USE_HDR_POST_PROCESS`, `TONEMAP`, `GAMMA_CORRECTION`, `ENV_MAP_HDR`, `USE_HDR_AUTOMATIC_EXPOSURE`
- and some effects that only the top tier has: `CAR_AMBIENT_OCCLUSION`, `CAR_PLANAR_REFLECTION`,
  `PARTICLE_CAST_SHADOW` and others

Top-tier presets switch on lots of things together, so this comparison alone can't say which switch matters. That
needed the targeted test below.

In RR3 14.0.1, the five HDR switches are always all on or all off. **19 presets have them on:** `AndroidXtraHigh`,
`SimRigTV`, `AppleTV`, `AppleTV5,3`, `iPad`, `iPad4,1`, `iPad5,1`, `iPad6,3`, `iPad6,4`, `iPad6,7`, `iPad6,8`,
`iPhone`, `iPhone6,2`, `iPhone7,1`, `iPhone8,2`, `iPhone9,2`, `iPhone10,3`, `iPod`, `iPod7,1`. See
[PRESETS.md](PRESETS.md).

## Targeted test: fix levels

The factory `AndroidHigh` (black) was patched with only the HDR switches changed. Every other byte stayed
identical:

| Level | Set to `true` | Result |
|---|---|---|
| A | `USE_HDR_POST_PROCESS` | **still black** |
| **B** | A + `TONEMAP` + `GAMMA_CORRECTION` | **works** |
| C | B + `ENV_MAP_HDR` + `USE_HDR_AUTOMATIC_EXPOSURE` | **works** |

So the black screen comes from the HDR / tonemapping path being off. The other top-tier effects aren't needed.
**B is the minimal fix.** C adds HDR reflections and auto exposure, at some extra GPU cost.

## Likely mechanism

This is a hypothesis and hasn't been proven. With HDR on, RR3 renders the scene off-screen and then tonemaps it
to the screen. With HDR off, it takes a direct, older path. On this GPU and driver the older path seems to stop
producing visible output. That fits the evidence: the scene appears for a moment, then goes black, and nothing
crashes.

## Theories that were ruled out

| Theory | Why it was ruled out |
|---|---|
| The `Settings file loaded, but had an invalid ID` log line means the copy is rejected | It's only a warning. RR3 uses the copied settings, and loads the `.feats` named by the content's `PLIST_IDENTIFIER`. |
| Low presets need missing low-detail track files (`R4_TRACK_EXTENSION = low/`) | `AndroidHigh` doesn't use `low/` tracks (its `R4_TRACK_EXTENSION` is empty) and still goes black. The 3D scene also renders fine before the screen goes black. |
| Screen size, GUI layout (`_480x320`) or `HIGH_RES_MENU` | `iPad3,1` has high-res menus and a large screen and still goes black. Fix level B leaves those settings alone and works. |
| Missing assets (`particle_test.pvr`, `hatch.lights`, `menu-carselect_porsche.banim`) | They're missing on clean installs too, where the game works. |

## Applying the fix

- **One preset:** `rr3gfx.py hdr <preset>.plist --level B`, then install it as described in the
  [README](../README.md#installing-an-edited-profile-on-a-device).
- **Every Android tier:** apply B to the preset you want, then copy the result over all seven Android names
  (`AndroidLow`, `AndroidMid`, `AndroidMid2`, `AndroidHigh`, `AndroidXtraHigh`, `AndroidUltraWide`, `SimRigTV`).
- Each preset keeps its own identity and other settings, and only the HDR switches change.

## Help wanted

Results from other GPUs (Mali, Xclipse, PowerVR, older Adreno) would help show whether this is specific to the
Adreno 8xx series or its drivers. Please open an issue with your device, GPU, Android version, the preset
used, and whether level A, B or C was needed.
