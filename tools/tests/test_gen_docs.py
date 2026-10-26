"""Tests for tools/gen_docs.py. Run from the repo root:  python -m unittest discover -s tools/tests -v"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import gen_docs  # noqa: E402


def load(order):
    """Profiles read in the given file order (sorted or reversed), like different OSes can do."""
    eds = order(gen_docs.EDS.glob("*.plist"))
    feats = order(gen_docs.FEATS.glob("*.feats"))
    return ({p.stem: gen_docs.plist_entries(p) for p in eds},
            {p.stem: gen_docs.feats_entries(p) for p in feats})


def forward(paths):
    return sorted(paths, key=lambda p: p.name)


def backward(paths):
    return sorted(paths, key=lambda p: p.name, reverse=True)


class GenDocsTests(unittest.TestCase):
    def test_output_does_not_depend_on_file_order(self):
        a, b = load(forward), load(backward)
        self.assertEqual(gen_docs.presets_md(*a), gen_docs.presets_md(*b))
        self.assertEqual(gen_docs.settings_md(*a), gen_docs.settings_md(*b))

    def test_committed_docs_are_up_to_date(self):
        plists, feats = load(forward)
        for name, text in (("PRESETS.md", gen_docs.presets_md(plists, feats)),
                           ("SETTINGS_REFERENCE.md", gen_docs.settings_md(plists, feats))):
            with self.subTest(doc=name):
                committed = (gen_docs.DOCS / name).read_bytes().decode("utf-8")
                self.assertEqual(committed, text, f"docs/{name} is stale: run python tools/gen_docs.py")

    def test_ties_are_broken_by_value(self):
        import collections
        self.assertEqual(gen_docs.ranked(collections.Counter(["b", "a", "c", "a", "b"])),
                         [("a", 2), ("b", 2), ("c", 1)])


if __name__ == "__main__":
    unittest.main()
