"""Compare the official policy pages on chiao.tw with the last saved snapshot.

The site is an unofficial digest, so the riskiest failure is going stale when the
campaign adds or edits a policy. This script downloads the policy list and every
policy page, keeps the main text, and compares it with tools/source_snapshot.json.

    python3 tools/check_source.py           # report changes; exit 1 if anything changed, 2 if the check failed
    python3 tools/check_source.py --update  # save the current text as the new snapshot

The snapshot's text is also what build_static.py uses to find which districts each
policy mentions, so update it after reviewing a change, then rebuild.
"""
import datetime
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "tools" / "source_snapshot.json"
LIST_URL = "https://chiao.tw/policies"
UA = "Mozilla/5.0 (compatible; ntpc-island-source-check; +https://ntpc-island.github.io/about/)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def page_text(markup):
    """Visible text of the page's <main> content, one line per block."""
    main = re.search(r"<main.*?</main>", markup, re.S)
    body = main.group(0) if main else markup
    body = re.sub(r"<(script|style|nav|footer)[^>]*>.*?</\1>", "", body, flags=re.S)
    body = re.sub(r"<[^>]+>", "\n", body)
    lines = [html.unescape(line).strip() for line in body.split("\n")]
    return [line for line in lines if line]


def policy_links():
    """Every policy page URL, across all pages of the list (archive_page=2, 3, …)."""
    links, page = [], 1
    while True:
        url = LIST_URL if page == 1 else f"{LIST_URL}?archive_page={page}"
        found = re.findall(r'href="(https://chiao\.tw/policies/[^"?#]+)"', fetch(url))
        new = [u for u in dict.fromkeys(found) if u not in links]
        if not new:
            return links
        links += new
        page += 1


def policy_body(url):
    """The policy's own text: its title (first line of <main>) down to the downloadable cards."""
    lines = page_text(fetch(url))
    for stop in ("政策圖卡 /", "延伸閱讀 /"):
        if stop in lines:
            lines = lines[: lines.index(stop)]
    slug = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    return {"slug": slug, "url": url, "title": lines[0] if lines else slug, "text": "\n".join(lines)}


def snapshot_now():
    policies = [policy_body(u) for u in policy_links()]
    for p in policies:
        p["hash"] = hashlib.sha256(p["text"].encode("utf-8")).hexdigest()[:16]
    return {"fetched": datetime.date.today().isoformat(), "policies": policies}


def compare(old, new):
    before = {p["slug"]: p for p in old["policies"]}
    after = {p["slug"]: p for p in new["policies"]}
    changes = [f"新增：{after[s]['title']}（{after[s]['url']}）" for s in after if s not in before]
    changes += [f"移除：{before[s]['title']}" for s in before if s not in after]
    changes += [f"內容變更：{after[s]['title']}（{after[s]['url']}）" for s in after if s in before and before[s]["hash"] != after[s]["hash"]]
    return changes


def main():
    current = snapshot_now()
    if "--update" in sys.argv or not SNAPSHOT.exists():
        SNAPSHOT.write_text(json.dumps(current, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"saved snapshot: {len(current['policies'])} policies, fetched {current['fetched']}")
        return 0
    changes = compare(json.loads(SNAPSHOT.read_text(encoding="utf-8")), current)
    if not changes:
        print(f"no changes ({len(current['policies'])} policies)")
        return 0
    print("\n".join(changes))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:  # network or page-structure problems: report, but do not claim a change
        print(f"check failed: {err!r}", file=sys.stderr)
        sys.exit(2)
