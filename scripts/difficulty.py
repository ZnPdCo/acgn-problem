"""Fetch Luogu problem difficulties and apply the final labels to the dataset.

Luogu publishes a gzipped NDJSON snapshot at
``https://cdn.luogu.com.cn/problemset-open/latest.ndjson.gz``.  Only the
``pid`` and ``difficulty`` fields are used.  The archive is written to a
temporary directory, streamed line by line, and deleted automatically; it is
never committed.

UOJ and QOJ problems have no comparable public difficulty feed, so their
labels come from the manually maintained ``data/difficulty.json``.
"""

from __future__ import annotations

import gzip
import json
import shutil
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIFFICULTY_FILE = REPO_ROOT / "data" / "difficulty.json"
DEFAULT_DIFFICULTY_URL = "https://cdn.luogu.com.cn/problemset-open/latest.ndjson.gz"

# Luogu's numeric difficulty is 0-8.  The order is part of the public API.
DIFFICULTY_LABELS = (
    "暂无评定",
    "入门",
    "普及−",
    "普及",
    "普及+/提高−",
    "提高",
    "提高+/省选−",
    "省选/NOI−",
    "NOI/NOI+/CTS",
)
UNSET_DIFFICULTY = "未设置难度"
VALID_DIFFICULTIES = frozenset(DIFFICULTY_LABELS) | {UNSET_DIFFICULTY}


class DifficultyError(ValueError):
    """Raised when a difficulty file or feed cannot be parsed."""


@dataclass
class DifficultyReport:
    counts: dict[str, int] = field(default_factory=dict)
    missing_luogu: list[str] = field(default_factory=list)
    missing_extra: list[str] = field(default_factory=list)
    used_previous: list[str] = field(default_factory=list)


def normalize_difficulty(value: Any) -> str:
    """Convert an integer index or label into one canonical label."""

    if value is None:
        return UNSET_DIFFICULTY
    if isinstance(value, bool):
        raise DifficultyError(f"invalid difficulty {value!r}")
    if isinstance(value, int):
        if 0 <= value < len(DIFFICULTY_LABELS):
            return DIFFICULTY_LABELS[value]
        raise DifficultyError(f"difficulty index out of range: {value!r}")
    if not isinstance(value, str):
        raise DifficultyError(f"invalid difficulty {value!r}")

    text = value.strip()
    if not text:
        return UNSET_DIFFICULTY
    if text in VALID_DIFFICULTIES:
        return text
    if text.isdigit():
        return normalize_difficulty(int(text))

    # Accept common dash variants so hand-written files are forgiving.
    normalized = text.replace("-", "−").replace("–", "−").replace("—", "−")
    if normalized in VALID_DIFFICULTIES:
        return normalized
    raise DifficultyError(
        f"unknown difficulty {value!r}; expected one of: "
        + ", ".join((*DIFFICULTY_LABELS, UNSET_DIFFICULTY))
    )


def load_difficulty_file(path: Path | str = DEFAULT_DIFFICULTY_FILE) -> dict[str, str]:
    """Load ``data/difficulty.json``; a missing file means no manual labels."""

    path = Path(path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DifficultyError(f"could not read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DifficultyError(f"{path} must contain a JSON object")

    result: dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise DifficultyError(f"{path} contains an empty problem key")
        key = raw_key.strip()
        if key in result:
            raise DifficultyError(f"{path} repeats problem {key!r}")
        result[key] = normalize_difficulty(raw_value)
    return result


def fetch_luogu_difficulties(
    problem_ids: Iterable[str],
    *,
    url: str = DEFAULT_DIFFICULTY_URL,
    timeout: float = 120.0,
) -> dict[str, str]:
    """Download the temporary NDJSON snapshot and return matching labels."""

    wanted = {
        str(problem_id).strip()
        for problem_id in problem_ids
        if str(problem_id).strip()
    }
    if not wanted:
        return {}

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "acgn-problem/1.0 (data updater)"},
    )
    found: dict[str, str] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="acgn-difficulty-") as temp_dir:
            archive = Path(temp_dir) / "latest.ndjson.gz"
            with urllib.request.urlopen(request, timeout=timeout) as response:
                with archive.open("wb") as output:
                    shutil.copyfileobj(response, output)

            with gzip.open(archive, "rt", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise DifficultyError(
                            f"invalid NDJSON at line {line_number}: {exc}"
                        ) from exc
                    if not isinstance(record, dict):
                        continue
                    pid = record.get("pid")
                    if pid not in wanted:
                        continue
                    found[pid] = normalize_difficulty(record.get("difficulty"))
    except (OSError, UnicodeError, urllib.error.URLError) as exc:
        raise DifficultyError(f"could not download {url}: {exc}") from exc
    return found


def apply_difficulties(
    dataset: dict[str, Any],
    *,
    luogu_difficulties: dict[str, str] | None = None,
    extra_difficulties: dict[str, str] | None = None,
    previous_difficulties: dict[str, str] | None = None,
) -> DifficultyReport:
    """Write ``problems[*].difficulty`` and return a small report."""

    problems = dataset.get("problems")
    if not isinstance(problems, dict):
        raise DifficultyError("dataset is missing a problems map")

    luogu_difficulties = luogu_difficulties or {}
    extra_difficulties = extra_difficulties or {}
    previous_difficulties = previous_difficulties or {}
    report = DifficultyReport()
    counts: Counter[str] = Counter()

    for key, problem in problems.items():
        if not isinstance(problem, dict):
            raise DifficultyError(f"problem {key!r} is not an object")
        oj = problem.get("oj")
        if oj == "luogu":
            label = luogu_difficulties.get(key)
            if label is None:
                report.missing_luogu.append(key)
                label = previous_difficulties.get(key)
                if label is not None:
                    report.used_previous.append(key)
        else:
            label = extra_difficulties.get(key)
            if label is None:
                report.missing_extra.append(key)

        label = normalize_difficulty(label)
        problem["difficulty"] = label
        counts[label] += 1

    report.counts = dict(counts)
    return report


def difficulties_from_dataset(dataset: dict[str, Any] | None) -> dict[str, str]:
    """Read labels from a previous ``acgn.json`` as a fallback."""

    if not isinstance(dataset, dict):
        return {}
    problems = dataset.get("problems")
    if not isinstance(problems, dict):
        return {}
    result: dict[str, str] = {}
    for key, problem in problems.items():
        if not isinstance(problem, dict):
            continue
        value = problem.get("difficulty")
        try:
            result[key] = normalize_difficulty(value)
        except DifficultyError:
            continue
    return result
