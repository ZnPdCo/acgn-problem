from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from acgn_parser import (  # noqa: E402
    ParserError,
    build_dataset,
    parse_markdown,
    resolve_problem_url,
    summarize_dataset,
    validate_dataset,
)

SAMPLE = """upd on 2026.10.18: hello

本文的「ACGN」使用**相对狭义**的定义：
- **A**nimation
- **C**omics

Some other fun facts:
- a fact

---

- 9-nine-
  - [P12533 [XJTUPC 2025] 9-Nine](/problem/P12533)
- Work B $\\jp{作品B}$
  - [UOJ1094 【UNR #10】麦田](https://uoj.ac/problem/1094)
  - [QOJ18255 Secret Key Transfer](https://qoj.ac/problem/18255)
  - [P12533 [XJTUPC 2025] 9-Nine](/problem/P12533)
- [^1]东方 Project $\\jp{東方Project}$
  - [B3709 最澄澈的空与海](/problem/B3709)

[^1]:非常感谢 @[zhoumurui](/user/305928) 的[整理](/paste/mgi7nok1)。
"""


class ParserTests(unittest.TestCase):
    def test_sample_structure(self) -> None:
        parsed = parse_markdown(SAMPLE)
        self.assertEqual([work.name for work in parsed.works], ["9-nine-", "Work B", "东方 Project"])
        self.assertEqual(len(parsed.problems["P12533"].works), 2)
        self.assertEqual(parsed.problems["UOJ1094"].oj, "uoj")
        self.assertEqual(parsed.problems["QOJ18255"].oj, "qoj")
        self.assertEqual(parsed.problems["B3709"].oj, "luogu")

    def test_jp_macro_and_footnote_ignored(self) -> None:
        parsed = parse_markdown(SAMPLE)
        work = parsed.works[1]
        self.assertEqual(work.name, "Work B")
        self.assertEqual(work.original, "作品B")
        touhou = parsed.works[2]
        self.assertEqual(touhou.name, "东方 Project")
        self.assertEqual(touhou.original, "東方Project")
        self.assertFalse(hasattr(touhou, "note_refs"))
        self.assertEqual(
            [ref.key for ref in touhou.problems],
            ["B3709"],
        )

    def test_rows_keep_order_and_duplicates(self) -> None:
        parsed = parse_markdown(SAMPLE)
        work_b = parsed.works[1]
        self.assertEqual(
            [ref.key for ref in work_b.problems],
            ["UOJ1094", "QOJ18255", "P12533"],
        )
        # P12533 is under both 9-nine- and Work B; the problem links two works.
        self.assertEqual(len(parsed.problems["P12533"].works), 2)

    def test_duplicate_rows_are_not_merged(self) -> None:
        markdown = """intro
- Work
  - [P7289 Chasse Neige](/problem/P7289)
  - [P7289 Chasse Neige 加强版](/problem/P7289)
"""
        parsed = parse_markdown(markdown)
        self.assertEqual(len(parsed.works[0].problems), 2)
        self.assertEqual(
            [ref.title for ref in parsed.works[0].problems],
            ["Chasse Neige", "Chasse Neige 加强版"],
        )
        self.assertEqual(len(parsed.problems["P7289"].works), 1)
        self.assertEqual(parsed.warnings, [])

    def test_different_problems_with_same_title_are_not_merged(self) -> None:
        markdown = """intro
- Work
  - [P1000 Same Title](/problem/P1000)
  - [P1001 Same Title](/problem/P1001)
"""
        parsed = parse_markdown(markdown)
        self.assertEqual([ref.key for ref in parsed.works[0].problems], ["P1000", "P1001"])
        self.assertEqual(len(parsed.problems), 2)

    def test_dataset_is_minimal(self) -> None:
        parsed = parse_markdown(SAMPLE)
        dataset = build_dataset(
            parsed,
            source={"url": "https://www.luogu.com.cn/article/93r0yhdc", "fetchedAt": "x"},
        )
        self.assertEqual(validate_dataset(dataset), [])
        self.assertEqual(
            set(dataset),
            {"schemaVersion", "source", "works", "problems"},
        )
        self.assertNotIn("notes", json.dumps(dataset, ensure_ascii=False))
        self.assertTrue(all("noteRefs" not in work for work in dataset["works"]))
        self.assertEqual(
            set(dataset["works"][0]["problems"][0]),
            {"key", "title"},
        )
        summary = summarize_dataset(dataset)
        self.assertEqual(summary["workCount"], 3)
        self.assertEqual(summary["problemCount"], 4)
        self.assertEqual(summary["rowCount"], 5)
        self.assertEqual(summary["multiWorkProblemCount"], 1)
        self.assertEqual(summary["ojCounts"], {"luogu": 2, "uoj": 1, "qoj": 1})
        json.dumps(dataset, ensure_ascii=False)

    def test_tabs_and_trailing_spaces(self) -> None:
        markdown = """intro
- Work
  - [P16928\t聚魔石](/problem/P16928)   
"""
        parsed = parse_markdown(markdown)
        self.assertEqual(parsed.works[0].problems[0].title, "聚魔石")
        self.assertEqual(parsed.problems["P16928"].title, "聚魔石")

    def test_url_resolution(self) -> None:
        self.assertEqual(
            resolve_problem_url("/problem/P12533"),
            ("luogu", "洛谷", "P12533", "https://www.luogu.com.cn/problem/P12533"),
        )
        self.assertEqual(
            resolve_problem_url("https://uoj.ac/problem/1094"),
            ("uoj", "UOJ", "UOJ1094", "https://uoj.ac/problem/1094"),
        )
        self.assertEqual(
            resolve_problem_url("https://qoj.ac/problem/18255"),
            ("qoj", "QOJ", "QOJ18255", "https://qoj.ac/problem/18255"),
        )
        self.assertIsNone(resolve_problem_url("https://example.com/foo"))

    def test_empty_input_raises(self) -> None:
        with self.assertRaises(ParserError):
            parse_markdown("")

    def test_full_snapshot(self) -> None:
        snapshot = REPO_ROOT / "data" / "article.md"
        if not snapshot.exists():
            self.skipTest("data/article.md is not present")
        parsed = parse_markdown(snapshot.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(parsed.works), 100)
        self.assertGreaterEqual(len(parsed.problems), 500)
        self.assertGreaterEqual(len(parsed.problems["QOJ18255"].works), 3)
        touhou = next(work for work in parsed.works if work.name == "东方 Project")
        self.assertFalse(hasattr(touhou, "note_refs"))
        self.assertGreater(len(touhou.problems), 100)
        # The article has a repeated P7289 row with a different title; it must
        # remain as two rows instead of being collapsed.
        naka = next(work for work in parsed.works if work.name == "中二病也要谈恋爱！")
        self.assertEqual(sum(1 for ref in naka.problems if ref.key == "P7289"), 2)


if __name__ == "__main__":
    unittest.main()
