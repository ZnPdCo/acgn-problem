#!/usr/bin/env python3
"""Fetch + parse the article and write the dataset consumed by the web app.

Typical usage::

    python scripts/update.py                     # fetch Luogu, rebuild data
    python scripts/update.py --from-file content.md --allow-shrink
    python scripts/update.py --min-works 50 --min-problems 200
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from acgn_parser import (  # noqa: E402  (path setup above)
    ParserError,
    build_dataset,
    parse_markdown,
    summarize_dataset,
    validate_dataset,
)
from fetch_article import (  # noqa: E402
    DEFAULT_URL,
    Article,
    FetchError,
    article_from_file,
    fetch_article,
)

DEFAULT_OUTPUT = REPO_ROOT / "web" / "public" / "data" / "acgn.json"
DEFAULT_RAW_OUTPUT = REPO_ROOT / "data" / "article.md"


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


def _load_existing(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_article(args: argparse.Namespace) -> Article:
    if args.from_file:
        return article_from_file(args.from_file)
    cookie = args.cookie or os.environ.get("LUOGU_COOKIE") or None
    return fetch_article(
        args.url,
        cookie=cookie,
        attempts=args.attempts,
        timeout=args.timeout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="article URL")
    parser.add_argument("--cookie", default=None, help="optional Luogu cookie")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--from-file",
        type=Path,
        help="parse local Markdown instead of fetching (for offline testing)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=DEFAULT_RAW_OUTPUT,
        help="where to keep the fetched Markdown (default: data/article.md)",
    )
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="allow the dataset to shrink by more than 20%% (skips the safety guard)",
    )
    parser.add_argument("--min-works", type=int, default=1)
    parser.add_argument("--min-problems", type=int, default=1)
    parser.add_argument("--no-write", action="store_true", help="parse only, do not write")
    args = parser.parse_args(argv)

    try:
        article = _resolve_article(args)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        parsed = parse_markdown(article.markdown)
    except ParserError as exc:
        print(f"error: could not parse article: {exc}", file=sys.stderr)
        return 1

    source = article.source_meta()
    dataset = build_dataset(parsed, source=source)

    errors = validate_dataset(dataset)
    if errors:
        print("dataset validation failed:", file=sys.stderr)
        for error in errors[:20]:
            print(f"  - {error}", file=sys.stderr)
        return 1

    stats = summarize_dataset(dataset)
    if stats["workCount"] < args.min_works:
        print(
            f"error: only {stats['workCount']} works parsed "
            f"(minimum {args.min_works}); refusing to write",
            file=sys.stderr,
        )
        return 1
    if stats["problemCount"] < args.min_problems:
        print(
            f"error: only {stats['problemCount']} problems parsed "
            f"(minimum {args.min_problems}); refusing to write",
            file=sys.stderr,
        )
        return 1

    previous = _load_existing(args.output)
    if previous and not args.allow_shrink:
        old_problems = len(previous.get("problems") or {})
        old_works = len(previous.get("works") or [])
        if old_problems and stats["problemCount"] < old_problems * 0.8:
            print(
                f"error: problem count dropped from {old_problems} to "
                f"{stats['problemCount']}; this looks like a parsing regression. "
                "Re-run with --allow-shrink if the article really got shorter.",
                file=sys.stderr,
            )
            return 1
        if old_works and stats["workCount"] < old_works * 0.8:
            print(
                f"error: work count dropped from {old_works} to "
                f"{stats['workCount']}; this looks like a parsing regression. "
                "Re-run with --allow-shrink if the article really got shorter.",
                file=sys.stderr,
            )
            return 1

    print(
        f"parsed {stats['workCount']} works, {stats['problemCount']} problems, "
        f"{stats['rowCount']} rows, "
        f"{stats['multiWorkProblemCount']} multi-work problems "
        f"(OJ: {stats['ojCounts']})"
    )
    for warning in parsed.warnings:
        print(f"warning (line {warning.line}): {warning.message}", file=sys.stderr)

    if args.no_write:
        return 0

    raw_output = args.raw_output
    # Never overwrite the fetched snapshot when the input came from a local
    # file (e.g. the truncated content.md sample).
    if raw_output and not args.from_file:
        _atomic_write(raw_output, article.markdown.rstrip("\n") + "\n")

    payload = json.dumps(dataset, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(args.output, payload)
    print(
        f"wrote {args.output} ({len(payload):,} chars), "
        f"contentSha256={article.sha256[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
