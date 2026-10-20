from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from difficulty import (  # noqa: E402
    DIFFICULTY_LABELS,
    UNSET_DIFFICULTY,
    DifficultyError,
    apply_difficulties,
    difficulties_from_dataset,
    fetch_luogu_difficulties,
    load_difficulty_file,
    normalize_difficulty,
)


class DifficultyLabelTests(unittest.TestCase):
    def test_numeric_indices_map_to_labels(self) -> None:
        for index, label in enumerate(DIFFICULTY_LABELS):
            self.assertEqual(normalize_difficulty(index), label)
        self.assertEqual(normalize_difficulty(0), "暂无评定")
        self.assertEqual(normalize_difficulty(8), "NOI/NOI+/CTS")

    def test_labels_and_empty_values_are_accepted(self) -> None:
        self.assertEqual(normalize_difficulty("提高"), "提高")
        self.assertEqual(normalize_difficulty(" 普及- "), "普及−")
        self.assertEqual(normalize_difficulty("省选/NOI-"), "省选/NOI−")
        self.assertEqual(normalize_difficulty(""), UNSET_DIFFICULTY)
        self.assertEqual(normalize_difficulty(None), UNSET_DIFFICULTY)

    def test_invalid_values_are_rejected(self) -> None:
        for value in (9, -1, True, "神话", []):
            with self.assertRaises(DifficultyError):
                normalize_difficulty(value)


class DifficultyFileTests(unittest.TestCase):
    def test_missing_file_means_no_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_difficulty_file(Path(tmp) / "difficulty.json"), {})

    def test_file_accepts_indices_labels_and_empty_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "difficulty.json"
            path.write_text(
                json.dumps(
                    {"UOJ1": 5, "QOJ2": "省选/NOI−", "UOJ3": ""},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                load_difficulty_file(path),
                {
                    "UOJ1": "提高",
                    "QOJ2": "省选/NOI−",
                    "UOJ3": UNSET_DIFFICULTY,
                },
            )

    def test_a_utf8_bom_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "difficulty.json"
            path.write_bytes(b"\xef\xbb\xbf" + '{"UOJ1": "提高"}'.encode("utf-8"))
            self.assertEqual(load_difficulty_file(path), {"UOJ1": "提高"})

    def test_invalid_shapes_and_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "difficulty.json"
            for payload in ("[]", '{"UOJ1": 99}', '{"": "提高"}', '{"UOJ1": "??"}'):
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(DifficultyError):
                    load_difficulty_file(path)


class ApplyDifficultyTests(unittest.TestCase):
    def test_apply_uses_luogu_feed_manual_file_and_previous_fallback(self) -> None:
        dataset = {
            "problems": {
                "P1": {"oj": "luogu"},
                "P2": {"oj": "luogu"},
                "P3": {"oj": "luogu"},
                "U1": {"oj": "uoj"},
                "Q1": {"oj": "qoj"},
            }
        }
        report = apply_difficulties(
            dataset,
            luogu_difficulties={"P1": "提高", "P2": "省选/NOI−"},
            extra_difficulties={"P2": "NOI/NOI+/CTS", "U1": "入门"},
            previous_difficulties={"P3": "普及"},
        )
        self.assertEqual(dataset["problems"]["P1"]["difficulty"], "提高")
        self.assertEqual(dataset["problems"]["P2"]["difficulty"], "NOI/NOI+/CTS")
        self.assertEqual(dataset["problems"]["P3"]["difficulty"], "普及")
        self.assertEqual(dataset["problems"]["U1"]["difficulty"], "入门")
        self.assertEqual(dataset["problems"]["Q1"]["difficulty"], UNSET_DIFFICULTY)
        self.assertEqual(report.missing_luogu, ["P3"])
        self.assertEqual(report.missing_extra, ["Q1"])
        self.assertEqual(report.used_previous, ["P3"])
        self.assertEqual(report.counts[UNSET_DIFFICULTY], 1)

    def test_manual_override_fills_a_luogu_gap(self) -> None:
        dataset = {
            "problems": {
                "P1": {"oj": "luogu"},
                "P2": {"oj": "luogu"},
            }
        }
        report = apply_difficulties(
            dataset,
            luogu_difficulties={"P1": "提高"},
            extra_difficulties={"P2": "省选/NOI−"},
        )
        self.assertEqual(dataset["problems"]["P1"]["difficulty"], "提高")
        self.assertEqual(dataset["problems"]["P2"]["difficulty"], "省选/NOI−")
        self.assertEqual(report.missing_luogu, [])
        self.assertEqual(report.missing_extra, [])
        self.assertEqual(report.used_previous, [])

    def test_previous_labels_are_read_from_a_dataset(self) -> None:
        dataset = {
            "problems": {
                "P1": {"difficulty": "提高"},
                "U1": {"difficulty": "入门"},
                "BAD": {"difficulty": "??"},
            }
        }
        self.assertEqual(
            difficulties_from_dataset(dataset),
            {"P1": "提高", "U1": "入门"},
        )


class FetchDifficultyTests(unittest.TestCase):
    def test_fetch_matches_only_requested_ids_from_gzipped_ndjson(self) -> None:
        records = [
            {"pid": "P1", "difficulty": 1, "title": "one"},
            {"pid": "P2", "difficulty": 8, "title": "two"},
            {"pid": "P3", "difficulty": 3, "title": "three"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest.ndjson.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record) + "\n")
            found = fetch_luogu_difficulties(
                ["P1", "P2", "P9"],
                url=path.as_uri(),
                timeout=5,
            )
        self.assertEqual(found, {"P1": "入门", "P2": "NOI/NOI+/CTS"})


if __name__ == "__main__":
    unittest.main()
