"""Keep ``web/public/data/tags.json`` in sync with the work list in the dataset.

The tag file is a flat ``{work name: [tag, ...]}`` mapping.  It is the single
source of truth for category achievements: additions to ``CATEGORY_ACHIEVEMENTS``
only reference tag slugs, never work names.

Rules:

* works already present keep their tags;
* works that appear in the article for the first time are appended with an
  empty tag list, so they stay visible as a manual-tagging reminder;
* entries whose tag list is empty are moved to the end of the file;
* works that disappeared from the article are kept by default (their tags may
  be useful if the article restores them) and can be dropped with ``--prune``.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAG_FILE = REPO_ROOT / "web" / "public" / "data" / "tags.json"
DEFAULT_DATA_FILE = REPO_ROOT / "web" / "public" / "data" / "acgn.json"


class TagFileError(ValueError):
    """Raised when ``tags.json`` does not have the expected shape."""


@dataclass
class MergeResult:
    tags: dict[str, list[str]] = field(default_factory=dict)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    untagged: list[str] = field(default_factory=list)


def _normalise_tags(name: str, raw: Any) -> list[str]:
    if not isinstance(raw, list):
        raise TagFileError(f"tags for {name!r} must be a list")

    tags: list[str] = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            raise TagFileError(f"tag {value!r} for {name!r} must be a string")
        tag = value.strip()
        if not tag:
            raise TagFileError(f"work {name!r} has an empty tag")
        if any(char.isspace() for char in tag):
            raise TagFileError(f"tag {tag!r} for {name!r} must not contain whitespace")
        if tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def load_tag_file(path: Path | str = DEFAULT_TAG_FILE) -> dict[str, list[str]]:
    """Read the tag mapping; a missing file simply means "no tags yet"."""

    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TagFileError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise TagFileError(f"{path}: expected an object mapping work names to tag lists")

    mapping: dict[str, list[str]] = {}
    for raw_name, raw_tags in payload.items():
        if not isinstance(raw_name, str):
            raise TagFileError(f"{path}: work name must be a string")
        name = raw_name.strip()
        if not name:
            raise TagFileError(f"{path}: work name must not be empty")
        if name in mapping:
            raise TagFileError(f"{path}: duplicate work name {name!r}")
        mapping[name] = _normalise_tags(name, raw_tags)
    return mapping


def merge_tag_map(
    existing: Mapping[str, Iterable[str]],
    work_names: Iterable[str],
    *,
    prune: bool = False,
) -> MergeResult:
    """Merge the article's work list into an existing tag mapping."""

    dataset_names: list[str] = []
    seen_names: set[str] = set()
    for raw_name in work_names:
        if not isinstance(raw_name, str):
            raise TagFileError("work names must be strings")
        name = raw_name.strip()
        if not name:
            raise TagFileError("work names must not be empty")
        if name not in seen_names:
            dataset_names.append(name)
            seen_names.add(name)

    merged: dict[str, list[str]] = {}
    for name, tags in existing.items():
        if name in seen_names:
            merged[name] = list(tags)

    removed = [name for name in existing if name not in seen_names]
    if not prune:
        for name in removed:
            merged[name] = list(existing[name])

    added = [name for name in dataset_names if name not in merged]
    for name in added:
        merged[name] = []

    # Stable partition: tagged works first, untagged works form the reminder
    # block at the end of the file.
    tagged = {name: tags for name, tags in merged.items() if tags}
    untagged = {name: tags for name, tags in merged.items() if not tags}

    return MergeResult(
        tags={**tagged, **untagged},
        added=added,
        removed=removed,
        untagged=list(untagged),
    )


def sync_work_tags(
    dataset: dict[str, Any],
    tag_file: Path | str = DEFAULT_TAG_FILE,
    *,
    prune: bool = False,
) -> MergeResult:
    """Merge the dataset's work list into the tag file (without touching the dataset)."""

    existing = load_tag_file(tag_file)
    return merge_tag_map(
        existing,
        (work.get("name", "") for work in dataset.get("works", [])),
        prune=prune,
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_json_file(path: Path | str, payload: Any) -> bool:
    """Write pretty JSON atomically; return ``True`` when the file changed."""

    path = Path(path)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except FileNotFoundError:
        pass
    _atomic_write(path, content)
    return True


def write_tag_file(path: Path | str, tag_map: Mapping[str, Iterable[str]]) -> bool:
    return write_json_file(path, {name: list(tags) for name, tags in tag_map.items()})
