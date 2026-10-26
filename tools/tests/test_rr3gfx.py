"""Tests for rr3gfx. Run from the repo root:  python -m unittest discover -s tools/tests -v

Uses only the standard library. The profile tests check every shipped file, so a broken
keystream, a bad commit (for example git rewriting line endings) or a corrupted profile fails here.
"""
import hashlib
import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import rr3gfx  # noqa: E402

COMPILED = ROOT / "profiles" / "compiled"
DECOMPILED = ROOT / "profiles" / "decompiled"


def pairs():
    """(compiled file, matching decompiled file) for every profile."""
    for sub, ext in (("eds", ".plist"), ("feats", ".feats")):
        for c in sorted((COMPILED / sub).glob("*" + ext)):
            yield c, DECOMPILED / sub / c.name


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = rr3gfx.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


class KeystreamTests(unittest.TestCase):
    def test_keystream_integrity(self):
        self.assertEqual(hashlib.sha256(rr3gfx.KEYSTREAM).hexdigest(), rr3gfx.KEYSTREAM_SHA256)
        self.assertEqual(len(rr3gfx.KEYSTREAM), 10420)

    def test_keystream_covers_every_profile(self):
        longest = max(p.stat().st_size for c, _ in pairs() for p in (c,))
        self.assertLessEqual(longest, len(rr3gfx.KEYSTREAM))

    def test_too_long_input_is_refused(self):
        with self.assertRaises(rr3gfx.Rr3GfxError):
            rr3gfx.xor(bytes(len(rr3gfx.KEYSTREAM) + 1))


class ProfileTests(unittest.TestCase):
    def test_profile_counts(self):
        self.assertEqual(len(list((COMPILED / "eds").glob("*.plist"))), 41)
        self.assertEqual(len(list((COMPILED / "feats").glob("*.feats"))), 42)
        self.assertEqual(len(list((DECOMPILED / "eds").glob("*.plist"))), 41)
        self.assertEqual(len(list((DECOMPILED / "feats").glob("*.feats"))), 42)

    def test_every_profile_round_trips_byte_for_byte(self):
        for comp, dec in pairs():
            with self.subTest(file=comp.name):
                raw, text = comp.read_bytes(), dec.read_bytes()
                kind = rr3gfx.kind_of(comp)
                self.assertEqual(rr3gfx.decompile_bytes(raw, kind, comp.name), text)
                self.assertEqual(rr3gfx.compile_bytes(text, kind, dec.name)[0], raw)

    def test_line_endings_match_rr3(self):
        # .plist uses CRLF and .feats uses LF. If git rewrote them, round trips break.
        for _, dec in pairs():
            with self.subTest(file=dec.name):
                self.assertIsNone(rr3gfx.eol_report(dec.read_bytes(), rr3gfx.kind_of(dec)))

    def test_plist_identifier_matches_file_name(self):
        for _, dec in pairs():
            if dec.suffix == ".plist":
                with self.subTest(file=dec.name):
                    self.assertEqual(rr3gfx.plist_settings(dec.read_bytes())["PLIST_IDENTIFIER"], dec.stem)

    def test_feats_device_name_and_shared_key_list(self):
        key_lists = set()
        for _, dec in pairs():
            if dec.suffix == ".feats":
                with self.subTest(file=dec.name):
                    name, settings = rr3gfx.feats_settings(dec.read_bytes())
                    self.assertEqual(name, dec.stem)
                    self.assertTrue(all(v in ("true", "false") for v in settings.values()))
                    key_lists.add(tuple(settings))
        self.assertEqual(len(key_lists), 1, "every .feats file has the same 190 keys in the same order")
        self.assertEqual(len(next(iter(key_lists))), 190)


class SafetyTests(unittest.TestCase):
    def test_entity_declarations_are_refused(self):
        evil = b'<?xml version="1.0"?><!DOCTYPE plist [<!ENTITY a "x">]><plist><dict/></plist>'
        with self.assertRaises(rr3gfx.Rr3GfxError):
            rr3gfx.check_text(evil, "plist", "evil.plist")

    def test_invalid_xml_is_not_compiled(self):
        with self.assertRaises(rr3gfx.Rr3GfxError):
            rr3gfx.compile_bytes(b"<ShaderFeatures><Device name='x'>", "feats", "bad.feats")

    def test_double_decompile_and_compile_are_refused(self):
        comp, dec = next(pairs())
        with self.assertRaises(rr3gfx.Rr3GfxError):
            rr3gfx.decompile_bytes(dec.read_bytes(), "plist", dec.name)
        with self.assertRaises(rr3gfx.Rr3GfxError):
            rr3gfx.compile_bytes(comp.read_bytes(), "plist", comp.name)


class HdrTests(unittest.TestCase):
    def test_hdr_levels_change_only_their_switches(self):
        text = (DECOMPILED / "eds" / "AndroidHigh.plist").read_bytes()
        for level, keys in rr3gfx.HDR_LEVELS.items():
            with self.subTest(level=level):
                patched, changed = rr3gfx.apply_hdr(text, level)
                after = rr3gfx.plist_settings(patched)
                before = rr3gfx.plist_settings(text)
                self.assertTrue(all(after[k] == "true" for k in keys))
                self.assertEqual({k for k in before if before[k] != after[k]}, set(changed))
                self.assertEqual(len(patched), len(text) - len(changed))  # <false/> -> <true/>

    def test_hdr_command_writes_loadable_compiled_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "AndroidHigh.plist"
            rc, _, _ = run("hdr", str(COMPILED / "eds" / "AndroidHigh.plist"), "--level", "B", "-o", str(out))
            self.assertEqual(rc, 0)
            settings = rr3gfx.plist_settings(rr3gfx.decompile_bytes(out.read_bytes(), "plist"))
            self.assertEqual(settings["TONEMAP"], "true")
            self.assertEqual(settings["PLIST_IDENTIFIER"], "AndroidHigh")


class CliTests(unittest.TestCase):
    def test_decompile_then_compile_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            dec, comp = Path(tmp) / "dec", Path(tmp) / "comp"
            self.assertEqual(run("decompile", str(COMPILED), "-o", str(dec), "-q")[0], 0)
            self.assertEqual(run("compile", str(dec), "-o", str(comp), "-q")[0], 0)
            for c, _ in pairs():
                rel = c.relative_to(COMPILED)
                self.assertEqual((comp / rel).read_bytes(), c.read_bytes(), rel)

    def test_verify_command(self):
        rc, out, _ = run("verify", str(ROOT / "profiles"))
        self.assertEqual(rc, 0)
        self.assertTrue(re.search(r"verify: 166 ok, 0 failed", out), out)

    def test_diff_command(self):
        rc, out, _ = run("diff", str(COMPILED / "eds" / "AndroidHigh.plist"), str(DECOMPILED / "eds" / "AndroidXtraHigh.plist"))
        self.assertEqual(rc, 0)
        self.assertIn("USE_HDR_POST_PROCESS", out)


if __name__ == "__main__":
    unittest.main()
