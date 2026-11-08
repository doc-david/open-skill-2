"""
stamp_assets.py
tags every stylesheet and script that index.html loads with a version taken from the file's own
content (css/site.css?v=1a2b3c4d). github pages lets browsers keep a file for 10 minutes, so without
this a visitor can get the new page with an old stylesheet. when a file changes, its address changes.
check_page.py fails if a tag doesn't match its file, so run this after editing any css or js.

run: python scripts/stamp_assets.py
"""
import hashlib
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
page = root / "index.html"


def version(path):
    # hash the text with unix line endings, so a windows checkout and the server agree
    text = (root / path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(text).hexdigest()[:8]


def stamp(match):
    attr, path = match.group(1), match.group(2)
    return f'{attr}="{path}?v={version(path)}"'


raw = page.read_bytes().decode("utf-8")
stamped = re.sub(r'(href|src)="((?:css|js)/[^"?]+)(?:\?v=[0-9a-f]+)?"', stamp, raw)
page.write_bytes(stamped.encode("utf-8"))
print("stamped", len(re.findall(r'\?v=[0-9a-f]{8}"', stamped)), "files" + ("" if stamped != raw else " (no change)"))
