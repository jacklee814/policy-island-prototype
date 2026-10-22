"""Render og/<item>.png: one 1200x630 link-preview card per policy and landmark.

The cards include a 3D snapshot, so the app draws them itself (index.html?og=policy-12)
and this script screenshots each one with agent-browser. Run it after changing the
data or the look, then run build_static.py so the pages point at the images:

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


def browser(*args):
    return subprocess.run(["agent-browser", "--session", SESSION, *args], capture_output=True, text=True, check=True).stdout


handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
handler.log_message = lambda *a, **k: None
server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()

out = ROOT / "og"
out.mkdir(exist_ok=True)
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
        browser("screenshot", str(out / f"{key}.png"))
        print("rendered", key)
finally:
    subprocess.run(["agent-browser", "--session", SESSION, "close"], capture_output=True)
    server.shutdown()
print(f"wrote {len(items)} images to {out}")
