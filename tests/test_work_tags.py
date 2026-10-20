from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from work_tags import (  # noqa: E402
    TagFileError,
    load_tag_file,
    merge_tag_map,
    sync_work_tags,
    write_tag_file,
)


class MergeTagMapTests(unittest.TestCase):
    def test_new_works_are_appended_with_empty_tags(self) -> None:
        existing = {"A": ["yuri"], "B": []}
        report = merge_tag_map(existing, ["A", "B", "C"])
        self.assertEqual(list(report.tags), ["A", "B", "C"])
        self.assertEqual(report.tags["C"], [])
        self.assertEqual(report.added, ["C"])
        self.assertEqual(report.untagged, ["B", "C"])

    def test_empty_tags_move_to_the_end(self) -> None:
        existing = {"A": [], "B": ["key"], "C": [], "D": ["music"]}
        report = merge_tag_map(existing, ["A", "B", "C", "D"])
        self.assertEqual(list(report.tags), ["B", "D", "A", "C"])
        self.assertEqual(report.added, [])

    def test_tags_survive_reordering(self) -> None:
        existing = {"B": ["key"], "A": ["yuri"], "C": []}
        report = merge_tag_map(existing, ["C", "B", "A"])
        self.assertEqual(report.tags, {"B": ["key"], "A": ["yuri"], "C": []})
        self.assertEqual(report.untagged, ["C"])

    def test_removed_works_are_kept_unless_pruned(self) -> None:
        existing = {"Gone": ["key"], "Here": []}
        kept = merge_tag_map(existing, ["Here"])
        self.assertEqual(kept.removed, ["Gone"])
        self.assertIn("Gone", kept.tags)
        pruned = merge_tag_map(existing, ["Here"], prune=True)
        self.assertNotIn("Gone", pruned.tags)

    def test_duplicate_work_names_are_collapsed(self) -> None:
        report = merge_tag_map({}, ["A", "A", "B"])
        self.assertEqual(list(report.tags), ["A", "B"])
        self.assertEqual(report.added, ["A", "B"])


class TagFileTests(unittest.TestCase):
    def test_missing_file_means_no_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_tag_file(Path(tmp) / "tags.json"), {})

    def test_invalid_shapes_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tags.json"
            for payload in ("[]", '{"A": "yuri"}', '{"A": [""]}', '{"A": ["a b"]}'):
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(TagFileError):
                    load_tag_file(path)

    def test_write_and_reload_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tags.json"
            mapping = {"作品 A": ["yuri", "romance"], "作品 B": []}
            self.assertTrue(write_tag_file(path, mapping))
            self.assertFalse(write_tag_file(path, mapping))
            self.assertEqual(load_tag_file(path), mapping)
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_sync_work_tags_reads_file_without_touching_the_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tags.json"
            path.write_text(json.dumps({"A": ["key"]}, ensure_ascii=False), encoding="utf-8")
            dataset = {"works": [{"name": "A"}, {"name": "B"}]}
            report = sync_work_tags(dataset, path)
            self.assertEqual(report.tags, {"A": ["key"], "B": []})
            self.assertEqual(report.added, ["B"])
            self.assertNotIn("tags", dataset["works"][0])
            self.assertNotIn("tags", dataset["works"][1])


if __name__ == "__main__":
    unittest.main()
