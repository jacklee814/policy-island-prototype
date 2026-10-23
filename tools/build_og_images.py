"""Render og/<item>.png: one 1200x630 link-preview card per policy and landmark,
og/line/<item>.png: the card's 3D snapshot alone, for the LINE Flex card's hero,
hero.jpg: a still panorama the page shows while the 3D scene loads, and og.png:
the site cover shown when the home page is shared.

The cards include a 3D snapshot, so the app draws them itself (index.html?og=policy-12)
and this script screenshots each one with agent-browser. Run it after changing the
data or the look, then run build_static.py so the pages point at the images.
Needs agent-browser and macOS `sips` (for the crop):

    python3 tools/build_og_images.py && python3 tools/build_static.py
"""
import functools
import http.server
import re
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8742
SESSION = "og-build"

source = (ROOT / "index.html").read_text(encoding="utf-8")
n_policies = len(re.findall(r"short: '[^']+', title: '", source))
n_spots = len(re.findall(r"name: '[^']+', map: '", source))
items = [f"policy-{n:02d}" for n in range(1, n_policies + 1)] + [f"spot-{n:02d}" for n in range(1, n_spots + 1)]
# "cover" is the site cover; it is saved as og.png at the root instead of og/cover.png
items.append("cover")


def browser(*args):
    return subprocess.run(["agent-browser", "--session", SESSION, *args], capture_output=True, text=True, check=True).stdout


handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
handler.log_message = lambda *a, **k: None
server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()

out = ROOT / "og"
line_out = out / "line"
line_out.mkdir(parents=True, exist_ok=True)

# The snapshot sits at (56, 56), 518 px square, in makeOgCanvas; keep its middle 3:2 band.
# Flex shows the title and points as text, so the hero carries only the picture.
CROP_W, CROP_H, CROP_X, CROP_Y = 518, 345, 56, 56 + (518 - 345) // 2
try:
    browser("open", "about:blank")
    browser("set", "viewport", "1200", "630")
    for key in items:
        browser("open", f"http://127.0.0.1:{PORT}/?og={key}")
        for _ in range(60):
            if "true" in browser("eval", "window.ogReady === true"):
                break
            time.sleep(0.5)
        else:
            raise SystemExit(f"timed out rendering {key}")
        if key == "cover":
            browser("screenshot", str(ROOT / "og.png"))
            print("rendered og.png")
            continue
        browser("screenshot", str(out / f"{key}.png"))
        subprocess.run(
            ["sips", "-c", str(CROP_H), str(CROP_W), "--cropOffset", str(CROP_Y), str(CROP_X), str(out / f"{key}.png"), "--out", str(line_out / f"{key}.png")],
            capture_output=True,
            check=True,
        )
        print("rendered", key)
    # Still panorama without any UI, shown by index.html while the 3D scene loads
    browser("set", "viewport", "1600", "1000")
    browser("open", f"http://127.0.0.1:{PORT}/")
    browser("eval", "localStorage.setItem('islandHintSeen', '1'); localStorage.setItem('releaseSeen', '9999-12-31')")
    browser("open", f"http://127.0.0.1:{PORT}/")
    for _ in range(60):
        if "true" in browser("eval", "document.getElementById('loading').classList.contains('done')"):
            break
        time.sleep(0.5)
    time.sleep(1.5)
    browser("eval", "['header', 'footer', '#labels', '.scrim', '#toast', '#loading'].forEach((q) => { const el = document.querySelector(q); if (el) el.style.display = 'none'; })")
    browser("screenshot", str(out / "hero.png"))
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "72", str(out / "hero.png"), "--out", str(ROOT / "hero.jpg")], capture_output=True, check=True)
    (out / "hero.png").unlink()
    print("rendered hero.jpg")
finally:
    subprocess.run(["agent-browser", "--session", SESSION, "close"], capture_output=True)
    server.shutdown()
print(f"wrote {len(items)} images to {out}")
