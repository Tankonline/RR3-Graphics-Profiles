#!/usr/bin/env python3
"""
rr3gfx - Real Racing 3 graphics profile decompiler / compiler.

Real Racing 3 stores its per-device graphics profiles as two kinds of file:

    eds/<Device>.plist    Apple XML property list with render settings
    feats/<Device>.feats  <ShaderFeatures> XML with shader feature switches

Both are stored on disk XOR-encrypted with one fixed keystream. "Decompiling" removes
that layer (you get the readable XML); "compiling" puts it back (you get a file RR3 loads).
The transformation is lossless: compile(decompile(x)) == x, byte for byte.

Usage (run `python rr3gfx.py <command> --help` for details):

    python rr3gfx.py decompile <file-or-folder> [-o OUT]
    python rr3gfx.py compile   <file-or-folder> [-o OUT]
    python rr3gfx.py info      <file> [<file> ...]
    python rr3gfx.py verify    <file-or-folder>
    python rr3gfx.py hdr       <plist> --level B|C [-o OUT]
    python rr3gfx.py diff      <file-a> <file-b>
    python rr3gfx.py keystream [--export FILE]

Requires Python 3.8+ and nothing else.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

__version__ = "1.0.0"
GAME_VERSION = "Real Racing 3 14.0.1"

# ---------------------------------------------------------------------------------------------
# Keystream
# ---------------------------------------------------------------------------------------------
# Recovered from RR3 14.0.1 factory files (see docs/REVERSE_ENGINEERING.md). It covers every
# .plist and .feats file shipped with that version. Files longer than the keystream cannot be
# processed (none exist in 14.0.1).
KEYSTREAM_SHA256 = "b8700d285217c1631d824c9521f3bf392d7f0d9bde79dd4ecb435af4347329c1"
KEYSTREAM_B64 = (
    "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"
)


def _load_keystream() -> bytes:
    data = base64.b64decode("".join(KEYSTREAM_B64))
    if hashlib.sha256(data).hexdigest() != KEYSTREAM_SHA256:
        raise SystemExit("rr3gfx: embedded keystream is corrupted (SHA-256 mismatch)")
    return data


KEYSTREAM = _load_keystream()

# ---------------------------------------------------------------------------------------------
# Core transform
# ---------------------------------------------------------------------------------------------


class Rr3GfxError(Exception):
    """A problem with an input file (reported without a stack trace)."""


def xor(data: bytes) -> bytes:
    """XOR with the keystream. The same call encrypts and decrypts."""
    if len(data) > len(KEYSTREAM):
        raise Rr3GfxError(f"file is {len(data)} bytes; the keystream only covers {len(KEYSTREAM)} bytes")
    ks = KEYSTREAM
    return bytes(b ^ ks[i] for i, b in enumerate(data))


PLIST_HEAD = b"<?xml"
FEATS_HEAD = b"<ShaderFeatures>"


def kind_of(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".plist":
        return "plist"
    if ext == ".feats":
        return "feats"
    raise Rr3GfxError(f"{path.name}: unknown extension (expected .plist or .feats)")


def is_decompiled(data: bytes) -> bool:
    """True when the bytes are already readable text (start of an XML document)."""
    return data.startswith(PLIST_HEAD) or data.startswith(FEATS_HEAD)


def check_text(text: bytes, kind: str, name: str) -> None:
    """Validate decompiled text so we never compile something RR3 cannot parse."""
    expected = PLIST_HEAD if kind == "plist" else FEATS_HEAD
    if not text.startswith(expected):
        raise Rr3GfxError(f"{name}: does not start with {expected.decode()} - not a valid {kind} (or not decompiled)")
    # RR3 profiles never declare entities. Refusing them avoids entity-expansion attacks
    # (e.g. "billion laughs") without needing a third-party XML library.
    if b"<!ENTITY" in text or re.search(rb"<!DOCTYPE[^>]*\[", text):
        raise Rr3GfxError(f"{name}: XML entity / internal DTD declarations are not allowed")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise Rr3GfxError(f"{name}: XML error: {e}") from None
    if kind == "plist" and (root.tag != "plist" or root.find("dict") is None):
        raise Rr3GfxError(f"{name}: expected <plist><dict>...</dict></plist>")
    if kind == "feats" and (root.tag != "ShaderFeatures" or root.find("Device") is None):
        raise Rr3GfxError(f"{name}: expected <ShaderFeatures><Device ...>...</Device></ShaderFeatures>")


def eol_report(text: bytes, kind: str) -> Optional[str]:
    """RR3's own files use CRLF in .plist and LF in .feats. Mixed or unusual endings get a warning."""
    crlf = text.count(b"\r\n")
    lf = text.count(b"\n") - crlf
    want = "CRLF" if kind == "plist" else "LF"
    have = "CRLF" if crlf and not lf else "LF" if lf and not crlf else "mixed" if crlf and lf else "none"
    if have != want:
        return f"line endings are {have}; RR3's own {kind} files use {want} (use --eol to normalise)"
    return None


def normalise_eol(text: bytes, kind: str) -> bytes:
    text = text.replace(b"\r\n", b"\n")
    return text.replace(b"\n", b"\r\n") if kind == "plist" else text


def decompile_bytes(data: bytes, kind: str, name: str = "file") -> bytes:
    if is_decompiled(data):
        raise Rr3GfxError(f"{name}: already decompiled")
    text = xor(data)
    check_text(text, kind, name)
    return text


def compile_bytes(text: bytes, kind: str, name: str = "file", eol: bool = False) -> Tuple[bytes, List[str]]:
    if not is_decompiled(text):
        raise Rr3GfxError(f"{name}: already compiled (not readable XML)")
    warnings = []
    if eol:
        text = normalise_eol(text, kind)
    else:
        w = eol_report(text, kind)
        if w:
            warnings.append(f"{name}: {w}")
    check_text(text, kind, name)
    out = xor(text)
    if xor(out) != text:  # paranoia: the round trip must be exact
        raise Rr3GfxError(f"{name}: round-trip check failed")
    return out, warnings


# ---------------------------------------------------------------------------------------------
# Parsing helpers (for info / diff / hdr)
# ---------------------------------------------------------------------------------------------


def plist_settings(text: bytes) -> Dict[str, str]:
    """Key -> value (as text) for a decompiled plist."""
    d = ET.fromstring(text).find("dict")
    out: Dict[str, str] = {}
    items = list(d)
    for k, v in zip(items[0::2], items[1::2]):
        if v.tag in ("true", "false"):
            out[k.text] = v.tag
        else:
            out[k.text] = (v.text or "").replace("\r\n", "\\n").replace("\n", "\\n")
    return out


def feats_settings(text: bytes) -> Tuple[str, Dict[str, str]]:
    dev = ET.fromstring(text).find("Device")
    items = list(dev)
    return dev.get("name", "?"), {k.text: (v.text or "") for k, v in zip(items[0::2], items[1::2])}


HDR_LEVELS = {
    "A": ["USE_HDR_POST_PROCESS"],
    "B": ["USE_HDR_POST_PROCESS", "TONEMAP", "GAMMA_CORRECTION"],
    "C": ["USE_HDR_POST_PROCESS", "TONEMAP", "GAMMA_CORRECTION", "ENV_MAP_HDR", "USE_HDR_AUTOMATIC_EXPOSURE"],
}


def apply_hdr(text: bytes, level: str) -> Tuple[bytes, List[str]]:
    """Set the level's boolean keys to <true/>; nothing else changes. Returns (text, changed keys)."""
    changed = []
    for key in HDR_LEVELS[level]:
        pat = re.compile(rb"(<key>" + re.escape(key.encode()) + rb"</key>\s*)<(true|false)/>")
        matches = pat.findall(text)
        if len(matches) != 1:
            raise Rr3GfxError(f"{key} found {len(matches)} times (expected 1)")
        if matches[0][1] == b"false":
            changed.append(key)
        text = pat.sub(rb"\1<true/>", text)
    return text, changed


def read_any(path: Path) -> bytes:
    """Readable text for a file, whether it is stored compiled or decompiled."""
    data = path.read_bytes()
    return data if is_decompiled(data) else decompile_bytes(data, kind_of(path), path.name)


# ---------------------------------------------------------------------------------------------
# File / folder walking
# ---------------------------------------------------------------------------------------------


def iter_inputs(src: Path) -> Iterable[Tuple[Path, Path]]:
    """(file, path relative to src) for every .plist/.feats under src (or src itself)."""
    if src.is_file():
        yield src, Path(src.name)
        return
    if not src.is_dir():
        raise Rr3GfxError(f"{src}: not found")
    for p in sorted(src.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".plist", ".feats"):
            yield p, p.relative_to(src)


def output_path(src: Path, rel: Path, out: Optional[Path], suffix_tag: str) -> Path:
    if out is None:
        if src.is_file():
            return src.with_name(f"{src.stem}.{suffix_tag}{src.suffix}")
        return src.parent / f"{src.name}_{suffix_tag}" / rel
    if src.is_file() and not (out.exists() and out.is_dir()) and out.suffix:
        return out
    return out / rel


# ---------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------


def cmd_transform(args, mode: str) -> int:
    src = Path(args.input)
    out = Path(args.output) if args.output else None
    done = skipped = failed = 0
    for path, rel in iter_inputs(src):
        try:
            data = path.read_bytes()
            kind = kind_of(path)
            if mode == "decompile":
                if is_decompiled(data):
                    if not args.quiet:
                        print(f"skip  {rel} (already decompiled)")
                    skipped += 1
                    continue
                result, warnings = decompile_bytes(data, kind, str(rel)), []
            else:
                if not is_decompiled(data):
                    if not args.quiet:
                        print(f"skip  {rel} (already compiled)")
                    skipped += 1
                    continue
                result, warnings = compile_bytes(data, kind, str(rel), eol=args.eol)
            dest = output_path(src, rel, out, mode + "d")
            if dest.resolve() == path.resolve() and not args.in_place:
                raise Rr3GfxError(f"{rel}: output would overwrite the input (use --in-place to allow)")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(result)
            for w in warnings:
                print(f"warn  {w}", file=sys.stderr)
            if not args.quiet:
                print(f"ok    {rel} -> {dest}")
            done += 1
        except Rr3GfxError as e:
            print(f"error {e}", file=sys.stderr)
            failed += 1
    print(f"{mode}: {done} written, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


def cmd_info(args) -> int:
    rc = 0
    for name in args.files:
        path = Path(name)
        try:
            raw = path.read_bytes()
            kind = kind_of(path)
            state = "decompiled" if is_decompiled(raw) else "compiled"
            text = raw if state == "decompiled" else decompile_bytes(raw, kind, path.name)
            sha = hashlib.sha256(raw).hexdigest()[:16]
            print(f"{path.name}")
            print(f"  type       : {kind} ({state}), {len(raw)} bytes, sha256 {sha}...")
            if kind == "plist":
                s = plist_settings(text)
                print(f"  identifier : {s.get('PLIST_IDENTIFIER', '?')}")
                print(f"  notes      : {s.get('Notes:', '')}")
                print(f"  screen     : {s.get('EXPECTED_SCREEN_WIDTH', '?')}x{s.get('EXPECTED_SCREEN_HEIGHT', '?')}  "
                      f"gui layout {s.get('GUI_LAYOUT_EXTENSION', '') or '-'}  high-res menu {s.get('HIGH_RES_MENU', '?')}")
                print(f"  renderer   : {s.get('EXPECTED_RENDERER', '?')}  scene scale {s.get('3D_SCENE_SCALE', '?')}  AA {s.get('AA_LEVEL', '?')}")
                hdr = {k: s.get(k, "?") for k in HDR_LEVELS["C"]}
                print("  hdr        : " + "  ".join(f"{k}={v}" for k, v in hdr.items()))
                print(f"  keys       : {len(s)}")
            else:
                dev, s = feats_settings(text)
                on = sum(v == "true" for v in s.values())
                print(f"  device     : {dev}")
                print(f"  features   : {len(s)} ({on} on, {len(s) - on} off)")
        except (Rr3GfxError, OSError) as e:
            print(f"error {name}: {e}", file=sys.stderr)
            rc = 1
    return rc


def cmd_verify(args) -> int:
    ok = bad = 0
    for path, rel in iter_inputs(Path(args.input)):
        try:
            raw = path.read_bytes()
            kind = kind_of(path)
            if is_decompiled(raw):
                comp, _ = compile_bytes(raw, kind, str(rel))
                assert decompile_bytes(comp, kind, str(rel)) == raw
            else:
                text = decompile_bytes(raw, kind, str(rel))
                comp, _ = compile_bytes(text, kind, str(rel))
                assert comp == raw
            ok += 1
        except (Rr3GfxError, AssertionError) as e:
            print(f"FAIL  {rel}: {e or 'round trip differs'}", file=sys.stderr)
            bad += 1
    print(f"verify: {ok} ok, {bad} failed")
    return 1 if bad else 0


def cmd_hdr(args) -> int:
    path = Path(args.input)
    if kind_of(path) != "plist":
        raise Rr3GfxError("hdr works on .plist files only")
    raw = path.read_bytes()
    compiled_input = not is_decompiled(raw)
    text = decompile_bytes(raw, "plist", path.name) if compiled_input else raw
    patched, changed = apply_hdr(text, args.level)
    as_compiled = compiled_input if args.format == "same" else args.format == "compiled"
    out_bytes = compile_bytes(patched, "plist", path.name)[0] if as_compiled else patched
    dest = Path(args.output) if args.output else path.with_name(f"{path.stem}.hdr{args.level}{path.suffix}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out_bytes)
    print(f"HDR level {args.level}: changed {', '.join(changed) if changed else 'nothing (already on)'}")
    print(f"wrote {dest} ({'compiled' if as_compiled else 'decompiled'}, {len(out_bytes)} bytes)")
    return 0


def cmd_diff(args) -> int:
    a, b = Path(args.a), Path(args.b)
    ka, kb = kind_of(a), kind_of(b)
    if ka != kb:
        raise Rr3GfxError("both files must be the same type")
    ta, tb = read_any(a), read_any(b)
    if ka == "plist":
        sa, sb = plist_settings(ta), plist_settings(tb)
    else:
        sa, sb = feats_settings(ta)[1], feats_settings(tb)[1]
    keys = sorted(set(sa) | set(sb))
    diffs = [(k, sa.get(k, "<missing>"), sb.get(k, "<missing>")) for k in keys if sa.get(k) != sb.get(k)]
    w = max([len(k) for k, _, _ in diffs] + [3])
    print(f"{'key':<{w}}  {a.name}  |  {b.name}")
    for k, va, vb in diffs:
        print(f"{k:<{w}}  {va}  |  {vb}")
    print(f"{len(diffs)} of {len(keys)} keys differ")
    return 0


def cmd_keystream(args) -> int:
    print(f"keystream: {len(KEYSTREAM)} bytes, sha256 {KEYSTREAM_SHA256}")
    if args.export:
        Path(args.export).write_bytes(KEYSTREAM)
        print(f"exported to {args.export}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rr3gfx",
        description=f"Decompile / compile Real Racing 3 graphics profiles (.plist / .feats). Built for {GAME_VERSION}.",
    )
    p.add_argument("--version", action="version", version=f"rr3gfx {__version__} ({GAME_VERSION})")
    sub = p.add_subparsers(dest="command", required=True)

    for name, help_text in (("decompile", "encrypted game file(s) -> readable XML"),
                            ("compile", "readable XML -> encrypted game file(s)")):
        s = sub.add_parser(name, help=help_text, description=help_text)
        s.add_argument("input", help="a .plist/.feats file or a folder (searched recursively)")
        s.add_argument("-o", "--output", help="output file or folder (default: next to the input)")
        s.add_argument("--in-place", action="store_true", help="allow overwriting the input files")
        s.add_argument("-q", "--quiet", action="store_true", help="only print the summary and problems")
        if name == "compile":
            s.add_argument("--eol", action="store_true", help="normalise line endings (CRLF for .plist, LF for .feats)")

    s = sub.add_parser("info", help="show a profile's key settings (compiled or decompiled)")
    s.add_argument("files", nargs="+", help="one or more .plist/.feats files")

    s = sub.add_parser("verify", help="check that every file round-trips byte for byte")
    s.add_argument("input", help="a .plist/.feats file or a folder (searched recursively)")

    s = sub.add_parser("hdr", help="turn on HDR switches in a .plist (fixes black screens on some GPUs)")
    s.add_argument("input", help="a .plist file (compiled or decompiled)")
    s.add_argument("--level", choices=sorted(HDR_LEVELS), default="B",
                   help="A: post-process only, B: + tonemap & gamma (recommended), C: all HDR switches")
    s.add_argument("--format", choices=("same", "compiled", "decompiled"), default="same",
                   help="output format (default: same as the input)")
    s.add_argument("-o", "--output", help="output file (default: <name>.hdr<LEVEL>.plist next to the input)")

    s = sub.add_parser("diff", help="list settings that differ between two profiles")
    s.add_argument("a", help="first profile (compiled or decompiled)")
    s.add_argument("b", help="second profile of the same type")

    s = sub.add_parser("keystream", help="show (or export) the embedded keystream")
    s.add_argument("--export", metavar="FILE", help="write the raw keystream bytes to FILE")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in ("decompile", "compile"):
            return cmd_transform(args, args.command)
        return {"info": cmd_info, "verify": cmd_verify, "hdr": cmd_hdr, "diff": cmd_diff, "keystream": cmd_keystream}[args.command](args)
    except Rr3GfxError as e:
        print(f"error {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
