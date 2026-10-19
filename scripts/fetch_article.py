#!/usr/bin/env python3
"""Fetch a Luogu article and extract the Markdown source.

Luogu embeds the data needed by the front end in::

    <script id="lentille-context" type="application/json">{...}</script>

The article Markdown lives at ``data.article.content``.  Only the source URL,
fetch time and Markdown are kept; article metadata and prose are not needed by
this static site.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

DEFAULT_URL = "https://www.luogu.com.cn/article/93r0yhdc"
_LENTILLE_RE = re.compile(
    r"<script[^>]*\bid=[\"']lentille-context[\"'][^>]*>(?P<json>.*?)</script>",
    re.DOTALL,
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


class FetchError(RuntimeError):
    """Raised when the article cannot be fetched or decoded."""


@dataclass
class Article:
    markdown: str
    source_url: str
    fetched_at: str

    @property
    def sha256(self) -> str:
        return sha256(self.markdown.encode("utf-8")).hexdigest()

    def source_meta(self) -> dict[str, str]:
        return {"url": self.source_url, "fetchedAt": self.fetched_at}


def _iso_utc(timestamp: float) -> str:
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def extract_lentille_payload(html: str) -> dict[str, Any]:
    match = _LENTILLE_RE.search(html)
    if not match:
        raise FetchError(
            "could not find <script id=\"lentille-context\"> in the page; "
            "Luogu may have changed its page structure or returned an anti-bot page"
        )
    raw = match.group("json").strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FetchError(f"lentille-context is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise FetchError("lentille-context JSON is not an object")
    status = payload.get("status")
    if isinstance(status, int) and status >= 400:
        raise FetchError(f"Luogu returned status {status} inside lentille-context")
    return payload


def article_from_payload(
    payload: dict[str, Any],
    *,
    source_url: str = DEFAULT_URL,
    fetched_at: str | None = None,
) -> Article:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise FetchError("lentille-context has no data object")
    article = data.get("article")
    if not isinstance(article, dict):
        raise FetchError("lentille-context has no article object")

    markdown = article.get("content")
    if not isinstance(markdown, str) or not markdown.strip():
        raise FetchError("article content is empty (maybe the article is private or deleted)")
    if (
        "/problem/" not in markdown
        and "uoj.ac/problem" not in markdown
        and "qoj.ac/problem" not in markdown
    ):
        raise FetchError("article content does not contain any problem links")

    return Article(
        markdown=markdown.replace("\r\n", "\n"),
        source_url=source_url,
        fetched_at=fetched_at or _iso_utc(time.time()),
    )


def fetch_html(
    url: str = DEFAULT_URL,
    *,
    attempts: int = 4,
    timeout: float = 30.0,
    cookie: str | None = None,
    retry_delay: float = 3.0,
) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
        "Referer": "https://www.luogu.com.cn/",
        "Cache-Control": "no-cache",
    }
    if cookie:
        headers["Cookie"] = cookie

    # Luogu's CDN answers the first request with a 302 back to the same URL and
    # a short-lived C3VK cookie.  A cookie jar is required to complete that
    # handshake; otherwise urllib reports an infinite redirect loop.
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers=headers)
            with opener.open(request, timeout=timeout) as response:  # noqa: S310
                status = getattr(response, "status", 200)
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
            if status >= 400:
                raise FetchError(f"HTTP {status}")
            return body
        except HTTPError as exc:
            last_error = exc
            retryable = exc.code in {408, 425, 429, 500, 502, 503, 504}
            if not retryable or attempt == attempts:
                break
            print(
                f"[fetch] HTTP {exc.code} on attempt {attempt}/{attempts}; retrying...",
                file=sys.stderr,
            )
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            print(
                f"[fetch] {exc} on attempt {attempt}/{attempts}; retrying...",
                file=sys.stderr,
            )
        time.sleep(retry_delay * attempt)

    raise FetchError(
        f"failed to fetch {url}: {last_error}. "
        "If Luogu is rate-limiting the runner, set the LUOGU_COOKIE secret."
    )


def fetch_article(
    url: str = DEFAULT_URL,
    *,
    cookie: str | None = None,
    attempts: int = 4,
    timeout: float = 30.0,
) -> Article:
    html = fetch_html(url, attempts=attempts, timeout=timeout, cookie=cookie)
    payload = extract_lentille_payload(html)
    return article_from_payload(payload, source_url=url)


def article_from_file(path: Path) -> Article:
    markdown = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not markdown.strip():
        raise FetchError(f"{path} is empty")
    return Article(markdown=markdown, source_url=DEFAULT_URL, fetched_at=_iso_utc(time.time()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="article URL")
    parser.add_argument("--output", type=Path, help="write Markdown to this file")
    parser.add_argument("--cookie", default=None, help="optional Luogu cookie")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--from-file",
        type=Path,
        help="skip the network and read Markdown from a local file",
    )
    args = parser.parse_args(argv)

    try:
        if args.from_file:
            article = article_from_file(args.from_file)
        else:
            article = fetch_article(
                args.url,
                cookie=args.cookie,
                attempts=args.attempts,
                timeout=args.timeout,
            )
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(article.markdown, encoding="utf-8")
        print(f"wrote {len(article.markdown)} chars of Markdown to {args.output}")
    else:
        print(article.markdown)

    print(f"sha256={article.sha256[:12]} source={article.source_url}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
