"""
bundle.py
makes one self-contained html file for the claude artifact preview: styles, scripts and data
inline, d3 from cdnjs. the git site itself serves the separate files, so edit those, not dist/.

run: python scripts/bundle.py   (writes dist/world-happiness.html)
"""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
html = (root / "index.html").read_text(encoding="utf-8")

# stylesheets inline
html = re.sub(r'<link rel="stylesheet" href="(css/[^"]+)">',
              lambda m: "<style>\n" + (root / m.group(1)).read_text(encoding="utf-8") + "</style>", html)

# d3 from the cdn the artifact allows, pinned to the same version as the vendored copy
html = html.replace('<script src="js/vendor/d3.v7.9.0.min.js"></script>',
                    '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>')

# the two json files inline, where main.js's load() looks for them first
blocks = ""
for name in ["chart-data", "continents"]:
    text = (root / "data" / f"{name}.json").read_text(encoding="utf-8").replace("</", "<\\/")
    blocks += f'<script type="application/json" id="data-{name}">{text}</script>\n  '
html = html.replace('<script src="js/format.js"></script>', blocks + '<script src="js/format.js"></script>')

# our own scripts inline
html = re.sub(r'<script src="(js/[^"]+)"></script>',
              lambda m: "<script>\n" + (root / m.group(1)).read_text(encoding="utf-8") + "</script>", html)

# the artifact wraps the page in its own doctype, html, head, body, charset and viewport
for pattern in [r"<!doctype html>\s*", r"<html[^>]*>\s*", r"</html>\s*", r"<head>\s*", r"</head>\s*",
                r"<body>\s*", r"</body>\s*", r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*']:
    html = re.sub(pattern, "", html, flags=re.IGNORECASE)

out = root / "dist" / "world-happiness.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding="utf-8")
print(f"wrote {out.relative_to(root)} ({len(html.encode()) // 1024} KB)")
