#!/usr/bin/env python3
"""Merge the current work list into ``web/public/data/tags.json``.

Usage::

    python scripts/sync_tags.py              # add new works to the tag file
    python scripts/sync_tags.py --check      # CI: fail when the tag file is stale
    python scripts/sync_tags.py --prune      # drop works no longer in the article
    python scripts/sync_tags.py --list-untagged

The script reads the work list from ``web/public/data/acgn.json`` and appends
every new work to the tag file with an empty tag list (at the end, as a
reminder).  The frontend fetches ``data/tags.json`` at runtime, so neither this
script nor ``update.py`` writes tags into ``acgn.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from work_tags import (  # noqa: E402
    DEFAULT_DATA_FILE,
    DEFAULT_TAG_FILE,
    TagFileError,
    sync_work_tags,
    write_tag_file,
)


def _load_dataset(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            dataset = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: could not read {path}: {exc}") from exc
    if not isinstance(dataset, dict) or not isinstance(dataset.get("works"), list):
        raise SystemExit(f"error: {path} does not look like an ACGN dataset")
    return dataset


def _print_preview(names: list[str], *, limit: int = 12) -> None:
    for name in names[:limit]:
        print(f"  - {name}")
    if len(names) > limit:
        print(f"  ... and {len(names) - limit} more")


def _print_report(report, *, prune: bool) -> None:
    tagged = len(report.tags) - len(report.untagged)
    print(
        f"tag file: {len(report.tags)} works, {tagged} tagged, "
        f"{len(report.untagged)} untagged"
    )
    if report.added:
        print(f"new works added with empty tags ({len(report.added)}):")
        _print_preview(report.added)
    if report.removed:
        action = "pruned" if prune else "kept"
        print(f"works no longer in the article ({len(report.removed)}, {action}):")
        _print_preview(report.removed)
    if report.untagged:
        print("works still waiting for tags:")
        _print_preview(report.untagged)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--tag-file", type=Path, default=DEFAULT_TAG_FILE)
    parser.add_argument(
        "--prune",
        action="store_true",
        help="drop tag entries for works that disappeared from the dataset",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 when the tag file is stale",
    )
    parser.add_argument(
        "--list-untagged",
        action="store_true",
        help="only print works whose tag list is empty, then exit",
    )
    args = parser.parse_args(argv)

    dataset = _load_dataset(args.data)
    try:
        report = sync_work_tags(dataset, args.tag_file, prune=args.prune)
    except TagFileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.list_untagged:
        for name in report.untagged:
            print(name)
        return 0

    _print_report(report, prune=args.prune)

    if args.check:
        payload = json.dumps(report.tags, ensure_ascii=False, indent=2) + "\n"
        try:
            current = args.tag_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = None
        if current != payload:
            print(f"stale file: {args.tag_file}", file=sys.stderr)
            return 1
        print("tag file is up to date")
        return 0

    if write_tag_file(args.tag_file, report.tags):
        print(f"wrote {args.tag_file}")
    else:
        print("nothing to update")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
