"""Generate share/*.html: one link-preview page per policy and landmark.

Social crawlers never see the part of a URL after '#', so each item gets a
real page carrying its own Open Graph tags, which then redirects to the hash
URL inside the app. Re-run after editing POLICIES or SPOTS in index.html:

    python3 tools/build_share_pages.py
"""
import html
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://ntpc-island.github.io/"
OG_IMAGE = SITE + "og.png"

source = (ROOT / "index.html").read_text(encoding="utf-8")
policies = re.findall(r"short: '([^']+)', title: '([^']+)'.*?summary: '([^']+)'", source, re.S)
spots = re.findall(r"name: '([^']+)', map: '[^']+'.*?desc: '([^']+)'", source, re.S)
assert len(policies) == 14 and len(spots) == 12, (len(policies), len(spots))


def page(slug, kind, name, title, description):
    target = "../#" + quote(f"{kind}/{name}", safe="/")
    e = lambda v: html.escape(v, quote=True)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>{e(name)}｜新北政見島</title>
<meta name="description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="新北政見島">
<meta property="og:title" content="{e(title)}｜新北政見島">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{SITE}share/{slug}.html">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace({target!r});</script>
</head>
<body><a href="{target}">前往「{e(name)}」</a></body>
</html>
"""


out = ROOT / "share"
out.mkdir(exist_ok=True)
for n, (short, title, summary) in enumerate(policies, 1):
    (out / f"policy-{n:02d}.html").write_text(page(f"policy-{n:02d}", "policy", short, title, summary), encoding="utf-8")
for n, (name, desc) in enumerate(spots, 1):
    (out / f"spot-{n:02d}.html").write_text(page(f"spot-{n:02d}", "spot", name, f"新北景點：{name}", desc), encoding="utf-8")
print(f"wrote {len(policies)} policy and {len(spots)} spot pages to {out}")
