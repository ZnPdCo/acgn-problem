"""Parse the Luogu article "以 ACGN 为题目背景的题" into structured data.

The article body is a two-level Markdown list::

    - 作品名 $\\jp{原名}$
      - [P1000 题目名](/problem/P1000)
      - [UOJ1094 ...](https://uoj.ac/problem/1094)

Only the data the static site actually renders is produced:

* works (name, original name, ordered problem rows);
* canonical problems (OJ, id, title, url, works);
* source url + fetch time.

Article prose, source metadata, footnotes and duplicates are not stored.
Duplicate rows are preserved verbatim; the global problem key is only used to
share solved state between identical links.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

SOURCE_URL = "https://www.luogu.com.cn/article/93r0yhdc"
SCHEMA_VERSION = 1

OJ_NAMES = {"luogu": "洛谷", "uoj": "UOJ", "qoj": "QOJ"}

_TOP_ITEM_RE = re.compile(r"^[-*+]\s+(?P<body>.*\S)\s*$")
_NESTED_ITEM_RE = re.compile(r"^[ \t]+[-*+]\s+(?P<body>.*\S)\s*$")
_LINK_RE = re.compile(r"\[(?P<title>.+?)\]\((?P<url>[^()\s]+)\)")
_FOOTNOTE_DEF_RE = re.compile(r"^\[\^(?P<id>[^\]]+)\]:\s*(?P<body>.*)$")
_FOOTNOTE_REF_RE = re.compile(r"\[\^(?P<id>[^\]]+)\]")
_LATEX_ESCAPE_RE = re.compile(r"\\([_&%$#{}])")
_LATEX_SPACE_RE = re.compile(r"\\ ")
_TITLE_ID_RE = re.compile(
    r"^(?P<id>(?:[PB]\s*\d{1,7}|(?:UOJ|QOJ)\s*#?\s*\d{1,7}))\b[\s:：\-—]*",
    re.IGNORECASE,
)
_WORK_ID_RE = re.compile(r"^w[0-9a-f]{8}(?:\d+)?$")


@dataclass
class Warning:
    line: int
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"line": self.line, "message": self.message}


@dataclass
class ProblemRef:
    """One row in a work's list. Title is row-specific so reprints stay distinct."""

    key: str
    title: str


@dataclass
class ParsedProblem:
    key: str
    oj: str
    oj_name: str
    problem_id: str
    title: str
    url: str
    works: list[str] = field(default_factory=list)


@dataclass
class ParsedWork:
    id: str
    name: str
    original: str
    problems: list[ProblemRef]
    line: int


@dataclass
class ParsedArticle:
    works: list[ParsedWork]
    problems: dict[str, ParsedProblem]
    warnings: list[Warning]


class ParserError(ValueError):
    """Raised when the input does not look like the expected article."""


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def _strip_jp_macros(text: str) -> tuple[str, list[str]]:
    """Remove ``$\\jp{...}$`` spans, returning their (balanced) contents."""

    originals: list[str] = []
    cursor = 0
    while True:
        start = text.find(r"\jp{", cursor)
        if start < 0:
            break
        math_start = start
        if math_start > 0 and text[math_start - 1] == "$":
            math_start -= 1
        body_start = start + len(r"\jp{")
        depth = 1
        index = body_start
        while index < len(text) and depth:
            char = text[index]
            if char == "\\":
                index += 2
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        if depth:
            break
        math_end = index
        if math_end < len(text) and text[math_end] == "$":
            math_end += 1
        originals.append(text[body_start : index - 1])
        text = text[:math_start] + text[math_end:]
        cursor = math_start
    return text, originals


def _unescape_latex(text: str) -> str:
    text = _LATEX_ESCAPE_RE.sub(r"\1", text)
    return _LATEX_SPACE_RE.sub(" ", text)


def _clean_work_name(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    # Footnote markers are source noise for this app; strip them and keep
    # neither the reference nor the footnote text.
    raw = _FOOTNOTE_REF_RE.sub("", raw)
    raw, originals = _strip_jp_macros(raw)
    name = re.sub(r"\s+", " ", raw).strip().strip("*_`")
    original = _unescape_latex(originals[0].strip()) if originals else ""
    original = re.sub(r"\s+", " ", original).strip()
    return name, original


def _clean_problem_title(raw: str, fallback: str) -> str:
    title = raw.replace("\t", " ").replace("\u3000", " ")
    title = re.sub(r"\s+", " ", title).strip()
    title = _TITLE_ID_RE.sub("", title, count=1).strip()
    title = title.strip(" .")
    return title or fallback


def _slug_work_id(name: str, original: str, seen: set[str]) -> str:
    digest = hashlib.sha1(f"{name}\0{original}".encode("utf-8")).hexdigest()[:8]
    candidate = f"w{digest}"
    suffix = 1
    while candidate in seen:
        suffix += 1
        candidate = f"w{digest}{suffix}"
    seen.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Problem URL handling
# ---------------------------------------------------------------------------


def resolve_problem_url(url: str) -> tuple[str, str, str, str] | None:
    """Return ``(oj, oj_name, problem_id, canonical_url)`` or ``None``."""

    url = url.strip()
    if not url:
        return None

    if url.startswith("/problem/"):
        problem_id = url[len("/problem/") :].split("?")[0].split("#")[0].strip("/").upper()
        if re.fullmatch(r"[PB]\d{1,7}", problem_id):
            return ("luogu", "洛谷", problem_id, f"https://www.luogu.com.cn/problem/{problem_id}")
        return None

    if url.startswith("//"):
        url = "https:" + url
    elif not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://www.luogu.com.cn/" + url.lstrip("/")

    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.strip("/")
    parts = [part for part in path.split("/") if part]

    if host == "luogu.com.cn" or host.endswith(".luogu.com.cn"):
        if len(parts) >= 2 and parts[0] == "problem":
            problem_id = parts[1].upper()
            if re.fullmatch(r"[PB]\d{1,7}", problem_id):
                return (
                    "luogu",
                    "洛谷",
                    problem_id,
                    f"https://www.luogu.com.cn/problem/{problem_id}",
                )
        return None

    if host == "uoj.ac" or host.endswith(".uoj.ac"):
        if len(parts) >= 2 and parts[0] == "problem":
            number = re.search(r"\d+", parts[1])
            if number:
                problem_id = f"UOJ{int(number.group())}"
                return ("uoj", "UOJ", problem_id, f"https://uoj.ac/problem/{int(number.group())}")
        return None

    if host == "qoj.ac" or host.endswith(".qoj.ac"):
        if len(parts) >= 2 and parts[0] == "problem":
            number = re.search(r"\d+", parts[1])
            if number:
                problem_id = f"QOJ{int(number.group())}"
                return ("qoj", "QOJ", problem_id, f"https://qoj.ac/problem/{int(number.group())}")
        return None

    # The article only supports Luogu / UOJ / QOJ.
    return None


def problem_key(oj: str, problem_id: str) -> str:
    return problem_id


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_markdown(markdown: str) -> ParsedArticle:
    if not isinstance(markdown, str) or not markdown.strip():
        raise ParserError("empty Markdown input")

    text = markdown.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    raw_lines = text.split("\n")

    # Drop footnote definition lines (and indented continuations) entirely.
    lines: list[str] = []
    index = 0
    while index < len(raw_lines):
        if not _FOOTNOTE_DEF_RE.match(raw_lines[index]):
            lines.append(raw_lines[index])
            index += 1
            continue
        cursor = index + 1
        while cursor < len(raw_lines) and raw_lines[cursor].startswith(("    ", "\t")):
            cursor += 1
        lines.extend([""] * (cursor - index))
        index = cursor

    # Split into top-level list blocks.
    starts = [i for i, line in enumerate(lines) if _TOP_ITEM_RE.match(line)]
    if not starts:
        raise ParserError("no top-level Markdown list found")

    warnings: list[Warning] = []
    blocks: list[tuple[int, int, list[int]]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        nested_lines = [
            line_index
            for line_index in range(start + 1, end)
            if _NESTED_ITEM_RE.match(lines[line_index])
        ]
        if nested_lines:
            blocks.append((start, end, nested_lines))

    if not blocks:
        raise ParserError("no work blocks (top-level item with nested problems) found")

    parsed_blocks: list[tuple[int, int, list[int]]] = []
    for start, end, nested_lines in blocks:
        if any(_LINK_RE.search(lines[line_index]) for line_index in nested_lines):
            parsed_blocks.append((start, end, nested_lines))

    if not parsed_blocks:
        raise ParserError("no problem links found inside the list")

    works: list[ParsedWork] = []
    problems: dict[str, ParsedProblem] = {}
    seen_work_ids: set[str] = set()

    for start, end, nested_lines in parsed_blocks:
        top_match = _TOP_ITEM_RE.match(lines[start])
        assert top_match is not None
        name, original = _clean_work_name(top_match.group("body"))
        if not name:
            name = original or f"未命名作品 {len(works) + 1}"

        if any(work.name == name for work in works):
            warnings.append(
                Warning(start + 1, f"duplicate work name {name!r}; both will be kept")
            )

        work_id = _slug_work_id(name, original, seen_work_ids)
        refs: list[ProblemRef] = []

        for line_index in nested_lines:
            nested_match = _NESTED_ITEM_RE.match(lines[line_index])
            assert nested_match is not None
            item = nested_match.group("body")
            link_match = _LINK_RE.search(item)
            if not link_match:
                warnings.append(
                    Warning(line_index + 1, f"could not parse problem link: {item!r}")
                )
                continue
            raw_title = link_match.group("title")
            raw_url = link_match.group("url")
            resolved = resolve_problem_url(raw_url)
            if resolved is None:
                warnings.append(
                    Warning(line_index + 1, f"unsupported problem URL: {raw_url!r}")
                )
                continue

            oj, oj_name, problem_id, canonical_url = resolved
            key = problem_key(oj, problem_id)
            title = _clean_problem_title(raw_title, fallback=problem_id)

            existing = problems.get(key)
            if existing is None:
                existing = ParsedProblem(
                    key=key,
                    oj=oj,
                    oj_name=oj_name,
                    problem_id=problem_id,
                    title=title,
                    url=canonical_url,
                )
                problems[key] = existing
            elif canonical_url != existing.url:
                warnings.append(
                    Warning(
                        line_index + 1,
                        f"same problem {key} has conflicting URLs: "
                        f"{existing.url} vs {canonical_url}",
                    )
                )

            if work_id not in existing.works:
                existing.works.append(work_id)
            refs.append(ProblemRef(key=key, title=title))

        if not refs:
            warnings.append(Warning(start + 1, f"work {name!r} has no valid problems; skipped"))
            continue

        works.append(
            ParsedWork(
                id=work_id,
                name=name,
                original=original,
                problems=refs,
                line=start + 1,
            )
        )

    if not works or not problems:
        raise ParserError("parser produced no works/problems")

    valid_work_ids = {work.id for work in works}
    for problem in problems.values():
        problem.works = [work_id for work_id in problem.works if work_id in valid_work_ids]
    problems = {key: problem for key, problem in problems.items() if problem.works}

    return ParsedArticle(works=works, problems=problems, warnings=warnings)


def build_dataset(parsed: ParsedArticle, *, source: dict[str, Any]) -> dict[str, Any]:
    works_payload = [
        {
            "id": work.id,
            "name": work.name,
            "original": work.original,
            "problems": [
                {"key": ref.key, "title": ref.title} for ref in work.problems
            ],
        }
        for work in parsed.works
    ]

    problems_payload = {
        key: {
            "key": problem.key,
            "id": problem.problem_id,
            "oj": problem.oj,
            "ojName": problem.oj_name,
            "title": problem.title,
            "url": problem.url,
            "works": problem.works,
        }
        for key, problem in parsed.problems.items()
    }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": source,
        "works": works_payload,
        "problems": problems_payload,
    }


def summarize_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    works = dataset.get("works", [])
    problems = dataset.get("problems", {})
    oj_counts: dict[str, int] = {}
    for problem in problems.values():
        oj_counts[problem["oj"]] = oj_counts.get(problem["oj"], 0) + 1
    return {
        "workCount": len(works),
        "problemCount": len(problems),
        "rowCount": sum(len(work.get("problems", [])) for work in works),
        "multiWorkProblemCount": sum(
            1 for problem in problems.values() if len(problem.get("works", [])) > 1
        ),
        "ojCounts": oj_counts,
    }


def validate_dataset(dataset: dict[str, Any]) -> list[str]:
    """Return a list of hard validation errors (empty means valid)."""

    errors: list[str] = []
    works = dataset.get("works")
    problems = dataset.get("problems")
    if not isinstance(works, list) or not isinstance(problems, dict):
        return ["dataset is missing works/problems"]
    if not works:
        errors.append("dataset has no works")
    if not problems:
        errors.append("dataset has no problems")

    work_ids: set[str] = set()
    referenced: set[str] = set()
    for work in works:
        work_id = work.get("id")
        if not isinstance(work_id, str) or not _WORK_ID_RE.match(work_id):
            errors.append(f"invalid work id: {work_id!r}")
            continue
        if work_id in work_ids:
            errors.append(f"duplicate work id: {work_id}")
        work_ids.add(work_id)
        name = work.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"work {work_id} has an empty name")
        refs = work.get("problems")
        if not isinstance(refs, list) or not refs:
            errors.append(f"work {work_id} has no problems")
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"work {work_id} has a non-object problem row")
                continue
            key = ref.get("key")
            if key not in problems:
                errors.append(f"work {work_id} references unknown problem {key!r}")
            if not isinstance(ref.get("title"), str) or not ref.get("title", "").strip():
                errors.append(f"work {work_id} row {key!r} has an empty title")
            referenced.add(key)

    for key, problem in problems.items():
        if problem.get("key") != key:
            errors.append(f"problem key mismatch: {key} != {problem.get('key')!r}")
        if not problem.get("title"):
            errors.append(f"problem {key} has an empty title")
        if not str(problem.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"problem {key} has an invalid url")
        works_list = problem.get("works")
        if not isinstance(works_list, list) or not works_list:
            errors.append(f"problem {key} has no works")
            continue
        for work_id in works_list:
            if work_id not in work_ids:
                errors.append(f"problem {key} references unknown work {work_id!r}")
        if key not in referenced:
            errors.append(f"problem {key} is not listed under any work")

    return errors
