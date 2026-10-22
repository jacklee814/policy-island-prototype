"""Generate the static parts derived from POLICIES and SPOTS in index.html.

- share/*.html: one link-preview page per policy and landmark. Social crawlers
  never see the part of a URL after '#', so each item gets a real page with its
  own Open Graph tags that redirects to the hash URL inside the app (keeping
  any utm_* query so analytics can attribute the visit).
- index.html SEO blocks: JSON-LD structured data and a <noscript> text version
  of every policy, so search engines can read content that the 3D app only
  renders on interaction.
- sitemap.xml with today's date.

Re-run after editing POLICIES or SPOTS:

    python3 tools/build_static.py
"""
import datetime
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://ntpc-island.github.io/"
OG_IMAGE = SITE + "og.png"
SOURCE_URL = "https://chiao.tw/policies"

index_path = ROOT / "index.html"
source = index_path.read_text(encoding="utf-8")


def strings(block):
    return re.findall(r"'([^']+)'", block)


policies = [
    {"short": m[0], "title": m[1], "slug": m[2], "summary": m[3], "items": strings(m[4])}
    for m in re.findall(
        r"short: '([^']+)', title: '([^']+)', slug: '([^']+)'.*?summary: '([^']+)',\s*items: \[(.*?)\]",
        source,
        re.S,
    )
]
spots = [{"name": m[0], "desc": m[1]} for m in re.findall(r"name: '([^']+)', map: '[^']+'.*?desc: '([^']+)'", source, re.S)]
assert len(policies) == 14 and len(spots) == 12, (len(policies), len(spots))
e = lambda v: html.escape(v, quote=True)


# ---------- share pages ----------
def share_page(slug, kind, name, title, description):
    target = "../#" + quote(f"{kind}/{name}", safe="/")
    base, frag = target.split("#")
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>{e(name)}｜新北政見島</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{SITE}">
<meta property="og:type" content="website">
<meta property="og:locale" content="zh_TW">
<meta property="og:site_name" content="新北政見島">
<meta property="og:title" content="{e(title)}｜新北政見島">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{SITE}share/{slug}.html">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace({base!r} + location.search + {("#" + frag)!r});</script>
</head>
<body><a href="{target}">前往「{e(name)}」</a></body>
</html>
"""


out = ROOT / "share"
out.mkdir(exist_ok=True)
for n, p in enumerate(policies, 1):
    (out / f"policy-{n:02d}.html").write_text(share_page(f"policy-{n:02d}", "policy", p["short"], p["title"], p["summary"]), encoding="utf-8")
for n, s in enumerate(spots, 1):
    (out / f"spot-{n:02d}.html").write_text(share_page(f"spot-{n:02d}", "spot", s["name"], f"新北景點：{s['name']}", s["desc"]), encoding="utf-8")


# ---------- index.html SEO blocks ----------
def app_url(kind, name):
    return SITE + "#" + quote(f"{kind}/{name}", safe="/")


jsonld = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "WebSite",
            "@id": SITE + "#website",
            "url": SITE,
            "name": "新北政見島",
            "inLanguage": "zh-TW",
            "description": "蘇巧慧 2026 新北市長 14 項政見的 3D 互動地圖（非官方整理）",
        },
        {
            "@type": "ItemList",
            "name": "蘇巧慧 2026 新北市長政見",
            "numberOfItems": len(policies),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": n,
                    "item": {
                        "@type": "CreativeWork",
                        "name": p["title"],
                        "description": p["summary"],
                        "url": app_url("policy", p["short"]),
                        "isBasedOn": f"{SOURCE_URL}/{quote(p['slug'])}",
                    },
                }
                for n, p in enumerate(policies, 1)
            ],
        },
    ],
}
jsonld_block = '<script type="application/ld+json">\n' + json.dumps(jsonld, ensure_ascii=False, indent=1) + "\n</script>"

noscript_lines = [
    "<noscript>",
    '<div class="noscript">',
    "<p>這個網站需要 JavaScript 才能顯示 3D 地圖。以下是文字版內容。</p>",
    "<h2>蘇巧慧 2026 新北市長政見（非官方整理）</h2>",
]
for p in policies:
    noscript_lines += [
        f"<h3>{e(p['title'])}</h3>",
        f"<p>{e(p['summary'])}</p>",
        "<ul>" + "".join(f"<li>{e(i)}</li>" for i in p["items"]) + "</ul>",
        f'<p><a href="{SOURCE_URL}/{quote(p["slug"])}">閱讀官方完整政見</a></p>',
    ]
noscript_lines.append("<h2>新北景點</h2>")
noscript_lines.append("<ul>" + "".join(f"<li><strong>{e(s['name'])}</strong>：{e(s['desc'])}</li>" for s in spots) + "</ul>")
noscript_lines.append(f'<p>內容摘錄自 <a href="{SOURCE_URL}">{SOURCE_URL}</a>，以官方網站為準。</p>')
noscript_lines += ["</div>", "</noscript>"]
noscript_block = "\n".join(noscript_lines)


def fill(text, name, block):
    pattern = re.compile(rf"(<!-- seo:{name}:start -->\n).*?(<!-- seo:{name}:end -->)", re.S)
    assert pattern.search(text), name
    return pattern.sub(lambda m: m.group(1) + block + "\n" + m.group(2), text)


source = fill(source, "jsonld", jsonld_block)
source = fill(source, "noscript", noscript_block)
index_path.write_text(source, encoding="utf-8")


# ---------- sitemap ----------
today = datetime.date.today().isoformat()
(ROOT / "sitemap.xml").write_text(
    f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE}</loc><lastmod>{today}</lastmod></url>
</urlset>
""",
    encoding="utf-8",
)
print(f"wrote {len(policies)} policy and {len(spots)} spot share pages, SEO blocks in index.html, sitemap.xml")
