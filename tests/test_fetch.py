from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fetch_article import (  # noqa: E402
    FetchError,
    article_from_payload,
    extract_lentille_payload,
)

PAYLOAD = {
    "instance": "main",
    "template": "article.show",
    "status": 200,
    "data": {
        "article": {
            "lid": "93r0yhdc",
            "title": "以 ACGN 为题目背景的题",
            "time": 1791195783,
            "author": {"uid": 400269, "name": "Jorisy"},
            "upvote": 184,
            "favorCount": 171,
            "replyCount": 86,
            "contentFull": True,
            "content": "upd on 2026.10.18: hello\n\n- 作品 $\\jp{作品名}$\n  - [P1000 题目](/problem/P1000)\n",
        }
    },
}


class FetchTests(unittest.TestCase):
    def test_extract_html_payload(self) -> None:
        html = (
            "<html><body>"
            '<script id="lentille-context" type="application/json">'
            + json.dumps(PAYLOAD, ensure_ascii=False)
            + "</script></body></html>"
        )
        payload = extract_lentille_payload(html)
        self.assertEqual(payload["data"]["article"]["title"], "以 ACGN 为题目背景的题")

    def test_extract_missing_script(self) -> None:
        with self.assertRaises(FetchError):
            extract_lentille_payload("<html><body>blocked</body></html>")

    def test_article_source_meta(self) -> None:
        article = article_from_payload(PAYLOAD, fetched_at="2026-10-19T00:00:00Z")
        self.assertEqual(article.fetched_at, "2026-10-19T00:00:00Z")
        self.assertEqual(
            article.source_meta(),
            {
                "url": "https://www.luogu.com.cn/article/93r0yhdc",
                "fetchedAt": "2026-10-19T00:00:00Z",
            },
        )
        self.assertEqual(len(article.sha256), 64)
        self.assertIn("/problem/P1000", article.markdown)

    def test_empty_content_rejected(self) -> None:
        payload = json.loads(json.dumps(PAYLOAD))
        payload["data"]["article"]["content"] = ""
        with self.assertRaises(FetchError):
            article_from_payload(payload)

    def test_http_status_rejected(self) -> None:
        payload = json.loads(json.dumps(PAYLOAD))
        payload["status"] = 404
        with self.assertRaises(FetchError):
            extract_lentille_payload(
                '<script id="lentille-context" type="application/json">'
                + json.dumps(payload)
                + "</script>"
            )


if __name__ == "__main__":
    unittest.main()
