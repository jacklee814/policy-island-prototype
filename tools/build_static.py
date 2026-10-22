"""Generate the static parts derived from GROUPS, POLICIES and SPOTS in index.html.

- policy/, spot/, about/: crawlable text pages. The 3D app keeps everything on
  one URL behind '#', which search engines treat as a single page, so each
  policy and landmark also gets its own page with the full text.
- share/*.html: one link-preview page per policy and landmark. Social crawlers
  never see the part of a URL after '#', so each item gets a page with its own
  Open Graph tags that redirects into the app (keeping any utm_* query so
  analytics can attribute the visit). Their canonical is the text page.
- index.html SEO blocks: JSON-LD structured data and a <noscript> text version.
- sitemap.xml listing every indexable page.

Re-run after editing the data in index.html:

    python3 tools/build_static.py
"""
import datetime
import html
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://ntpc-island.github.io/"
OG_IMAGE = SITE + "og.png"
SOURCE_URL = "https://chiao.tw/policies"
SOURCE_DATE = "2026-10-22"
GA_ID = "G-5H13CQWF3X"
TODAY = datetime.date.today().isoformat()

index_path = ROOT / "index.html"
source = index_path.read_text(encoding="utf-8")
e = lambda v: html.escape(v, quote=True)


def strings(block):
    return re.findall(r"'([^']+)'", block)


groups = {k: {"name": n, "color": c} for k, n, c in re.findall(r"(\w+): \{ name: '([^']+)', color: '(#[0-9a-fA-F]+)' \}", source)}
policies = [
    {"short": m[0], "title": m[1], "slug": m[2], "group": m[3], "summary": m[4], "items": strings(m[5])}
    for m in re.findall(
        r"short: '([^']+)', title: '([^']+)', slug: '([^']+)', group: '(\w+)'.*?summary: '([^']+)',\s*items: \[(.*?)\]",
        source,
        re.S,
    )
]
spots = [
    {"name": m[0], "map": m[1], "desc": m[2]}
    for m in re.findall(r"name: '([^']+)', map: '([^']+)'.*?desc: '([^']+)'", source, re.S)
]
assert len(groups) == 5 and len(policies) == 14 and len(spots) == 12, (len(groups), len(policies), len(spots))


def page_path(kind, name):
    return f"{kind}/{quote(name)}/"


def official_url(p):
    return f"{SOURCE_URL}/{quote(p['slug'])}"


def maps_url(s):
    return f"https://www.google.com/maps/search/?api=1&query={quote(s['map'])}"


def app_link(kind, name):
    return "/#" + quote(f"{kind}/{name}", safe="/")


# ---------- text pages ----------
GA_SNIPPET = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag() {{ dataLayer.push(arguments); }}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>"""

HEADER = """<header class="site-header">
  <a class="brand" href="/">新北政見島</a>
  <nav><a href="/">3D 地圖</a><a href="/policy/">政見一覽</a><a href="/about/">關於本站</a></nav>
</header>"""

FOOTER = f"""<footer class="site-footer">
  非官方整理 · 政見內容摘錄自 <a href="{SOURCE_URL}">{SOURCE_URL}</a>（{SOURCE_DATE}），以官方網站為準 · 本站使用 Google Analytics 統計瀏覽情形
</footer>"""


def text_page(path, title, description, body, crumbs, og_title=None):
    """crumbs: [(name, path or None)] after 首頁; the last one is the current page."""
    url = SITE + path
    breadcrumb_ld = {
        "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": 1, "name": "新北政見島", "item": SITE}]
        + [
            {"@type": "ListItem", "position": n, "name": name, "item": SITE + (p if p is not None else path)}
            for n, (name, p) in enumerate(crumbs, 2)
        ],
    }
    page_ld = {
        "@type": "WebPage",
        "url": url,
        "name": title,
        "description": description,
        "inLanguage": "zh-TW",
        "dateModified": TODAY,
        "isPartOf": {"@type": "WebSite", "name": "新北政見島", "url": SITE},
    }
    ld = json.dumps({"@context": "https://schema.org", "@graph": [page_ld, breadcrumb_ld]}, ensure_ascii=False)
    crumb_html = " › ".join(
        ['<a href="/">首頁</a>']
        + [f'<a href="/{p}">{e(name)}</a>' if p is not None else e(name) for name, p in crumbs]
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#f7f4ee">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath fill='%23e0663d' d='M16 1l13 7.5v15L16 31 3 23.5v-15z'/%3E%3C/svg%3E">
<link rel="stylesheet" href="/pages.css">
<meta property="og:type" content="article">
<meta property="og:locale" content="zh_TW">
<meta property="og:site_name" content="新北政見島">
<meta property="og:title" content="{e(og_title or title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld}</script>
{GA_SNIPPET}
</head>
<body>
{HEADER}
<main>
<p class="breadcrumb">{crumb_html}</p>
{body}
</main>
{FOOTER}
</body>
</html>
"""


def summarize(text, limit=150):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def write(path, content):
    # URLs carry percent-encoded names; the folders on disk use the plain names the server decodes them to
    target = ROOT / unquote(path) / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


written = []
for n, p in enumerate(policies):
    grp = groups[p["group"]]
    prev_p, next_p = policies[n - 1], policies[(n + 1) % len(policies)]
    path = page_path("policy", p["short"])
    body = f"""<span class="tag" style="background:{grp['color']}">{e(grp['name'])}</span>
<h1>{e(p['title'])}</h1>
<p class="lead">{e(p['summary'])}</p>
<h2>政見重點</h2>
<ul class="points">
{''.join(f'<li>{e(i)}</li>' for i in p['items'])}
</ul>
<div class="actions">
  <a class="button primary" href="{app_link('policy', p['short'])}">在 3D 政見島查看</a>
  <a class="button" href="{official_url(p)}" rel="noopener">閱讀官方完整政見 ↗</a>
</div>
<nav class="pager" aria-label="上一項與下一項">
  <a href="/{page_path('policy', prev_p['short'])}">← {e(prev_p['short'])}</a>
  <a href="/{page_path('policy', next_p['short'])}">{e(next_p['short'])} →</a>
</nav>
<p class="note">本頁為非官方整理，內容節錄自蘇巧慧 2026 新北市長競選網站（擷取日期 {SOURCE_DATE}），若有出入請以<a href="{official_url(p)}">官方原文</a>為準。</p>"""
    description = summarize(f"{p['summary']}重點：{'；'.join(p['items'])}")
    write(path, text_page(path, f"{p['title']}｜蘇巧慧 2026 新北市長政見｜新北政見島", description, body, [("政見一覽", "policy/"), (p["short"], None)], og_title=f"{p['title']}｜新北政見島"))
    written.append(path)

for n, s in enumerate(spots):
    prev_s, next_s = spots[n - 1], spots[(n + 1) % len(spots)]
    path = page_path("spot", s["name"])
    body = f"""<span class="tag" style="background:#0f766e">新北景點</span>
<h1>{e(s['name'])}</h1>
<p class="lead">{e(s['desc'])}</p>
<div class="actions">
  <a class="button primary" href="{app_link('spot', s['name'])}">在 3D 地圖查看</a>
  <a class="button" href="{maps_url(s)}" rel="noopener">在 Google 地圖開啟 ↗</a>
</div>
<nav class="pager" aria-label="上一個與下一個景點">
  <a href="/{page_path('spot', prev_s['name'])}">← {e(prev_s['name'])}</a>
  <a href="/{page_path('spot', next_s['name'])}">{e(next_s['name'])} →</a>
</nav>"""
    write(path, text_page(path, f"{s['name']}｜新北景點｜新北政見島", s["desc"], body, [("政見一覽", "policy/"), (s["name"], None)]))
    written.append(path)

# Overview of every policy and landmark
policy_items = "\n".join(
    f'<li><a href="/{page_path("policy", p["short"])}"><span class="t">{e(p["title"])}</span><span class="s">{e(groups[p["group"]]["name"])} · {e(p["summary"])}</span></a></li>'
    for p in policies
)
spot_items = "\n".join(
    f'<li><a href="/{page_path("spot", s["name"])}"><span class="t">{e(s["name"])}</span><span class="s">{e(s["desc"])}</span></a></li>'
    for s in spots
)
overview_body = f"""<h1>蘇巧慧 2026 新北市長政見一覽</h1>
<p class="lead">{len(policies)} 項政見的重點整理，每一項都附官方原文連結。想用地圖瀏覽，可以到 <a href="/">3D 政見島</a>。</p>
<h2>政見</h2>
<ul class="list">
{policy_items}
</ul>
<h2>新北景點</h2>
<ul class="list">
{spot_items}
</ul>"""
write("policy/", text_page("policy/", "蘇巧慧 2026 新北市長 14 項政見一覽｜新北政見島", f"蘇巧慧 2026 新北市長 {len(policies)} 項政見重點整理：{'、'.join(p['short'] for p in policies)}。非官方整理，附官方原文連結。", overview_body, [("政見一覽", None)]))
written.append("policy/")

about_body = f"""<h1>關於新北政見島</h1>
<p class="lead">新北政見島把蘇巧慧 2026 新北市長競選網站公布的 {len(policies)} 項政見，整理成一張 3D 互動地圖和文字頁，讓大家更容易瀏覽、搜尋和分享。</p>
<h2>非官方網站</h2>
<p>本站並非蘇巧慧競選團隊的官方網站。政見內容以<a href="{SOURCE_URL}">官方網站</a>為準。</p>
<h2>資料來源</h2>
<ul class="points">
  <li>政見的標題、摘要與重點條列，節錄自 <a href="{SOURCE_URL}">{SOURCE_URL}</a>，擷取日期 {SOURCE_DATE}。</li>
  <li>每一項政見都附上官方原文連結，本站不加入評論或立場說明。</li>
  <li>新北景點的介紹由本站撰寫，地點連結到 Google 地圖。</li>
</ul>
<h2>隱私與統計</h2>
<ul class="points">
  <li>本站使用 Google Analytics 統計瀏覽、分享與搜尋的次數，用來了解哪些內容較受關注。</li>
  <li>使用 LINE 分享卡片時，會經過 LINE 的登入與授權，授權只用來傳送你選擇的卡片，本站不儲存你的 LINE 帳號資料。</li>
</ul>
<p class="note">最後更新：{TODAY}</p>"""
write("about/", text_page("about/", "關於新北政見島｜資料來源與非官方聲明", "新北政見島是非官方整理的蘇巧慧 2026 新北市長政見 3D 地圖。說明資料來源、擷取日期、隱私與統計方式。", about_body, [("關於本站", None)]))
written.append("about/")


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
<link rel="canonical" href="{SITE}{page_path(kind, name)}">
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
                        "url": SITE + page_path("policy", p["short"]),
                        "isBasedOn": official_url(p),
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
    '<p>這個網站需要 JavaScript 才能顯示 3D 地圖。也可以看<a href="policy/">文字版政見一覽</a>。</p>',
    "<h2>蘇巧慧 2026 新北市長政見（非官方整理）</h2>",
]
for p in policies:
    noscript_lines += [
        f'<h3><a href="{page_path("policy", p["short"])}">{e(p["title"])}</a></h3>',
        f"<p>{e(p['summary'])}</p>",
        "<ul>" + "".join(f"<li>{e(i)}</li>" for i in p["items"]) + "</ul>",
        f'<p><a href="{official_url(p)}">閱讀官方完整政見</a></p>',
    ]
noscript_lines.append("<h2>新北景點</h2>")
noscript_lines.append(
    "<ul>" + "".join(f'<li><a href="{page_path("spot", s["name"])}"><strong>{e(s["name"])}</strong></a>：{e(s["desc"])}</li>' for s in spots) + "</ul>"
)
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
urls = [SITE] + [SITE + p for p in ["policy/", "about/"] + [w for w in written if w not in ("policy/", "about/")]]
(ROOT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls)
    + "</urlset>\n",
    encoding="utf-8",
)
print(f"wrote {len(written)} text pages, {len(policies) + len(spots)} share pages, SEO blocks, sitemap ({len(urls)} urls)")
