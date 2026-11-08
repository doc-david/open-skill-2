"""
package.py
builds the folder to send to people who want to run the site on their own computer, and a zip of it:

  dist/world-happiness/
    World Happiness.html   one file with everything inside: double-click it, no server or internet
                           needed (only the web fonts need a connection; without one, system fonts stand in)
    index.html, css/, js/, data/   the source, exactly as on the live site
    README.md              how to open it and what's inside
  dist/world-happiness.zip

the build and check scripts, the figma stills and the project notes stay out: they're for working on
the site, not using it.

run: python scripts/package.py
"""
import hashlib
import re
import shutil
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / "dist" / "world-happiness"
SOURCE = ["index.html", "css/tokens.css", "css/site.css", "data/chart-data.json", "data/continents.json"] + \
         sorted(str(p.relative_to(root)).replace("\\", "/") for p in (root / "js").rglob("*.js"))

if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

# the source, copied byte for byte; index.html loses its cache version tags, which only matter online
for name in SOURCE:
    target = out / name
    target.parent.mkdir(parents=True, exist_ok=True)
    data = (root / name).read_bytes()
    if name == "index.html":
        data = re.sub(rb'\?v=[0-9a-f]+"', b'"', data)
    target.write_bytes(data)

# the single file: stylesheets, d3, the data and the scripts all inline. main.js reads the data from
# the inline blocks first, so the page never has to fetch a file, which browsers forbid on a file://
page = (root / "index.html").read_text(encoding="utf-8")
page = re.sub(r'\?v=[0-9a-f]+"', '"', page)
page = re.sub(r'<link rel="stylesheet" href="(css/[^"]+)">',
              lambda m: "<style>\n" + (root / m.group(1)).read_text(encoding="utf-8") + "</style>", page)
blocks = "".join(
    f'<script type="application/json" id="data-{name}">'
    + (root / "data" / f"{name}.json").read_text(encoding="utf-8").replace("</", "<\\/") + "</script>\n  "
    for name in ["chart-data", "continents"])
page = page.replace('<script src="js/format.js"></script>', blocks + '<script src="js/format.js"></script>')
page = re.sub(r'<script src="(js/[^"]+)"></script>',
              lambda m: "<script>\n" + (root / m.group(1)).read_text(encoding="utf-8").replace("</script", "<\\/script") + "\n</script>", page)
assert "src=\"js/" not in page and "href=\"css/" not in page, "something was left outside the single file"
(out / "World Happiness.html").write_text(page, encoding="utf-8")

(out / "README.md").write_text("""# World Happiness

Three interactive charts of the World Happiness surveys, 2019 to 2025: the happiest and unhappiest
countries of 2025, how scores changed since 2019, and what makes up each continent's top score.
Pick a chart from the map, hover or tab through the marks, and filter all three by continent.

## Open it

**Double-click `World Happiness.html`.** It's the whole site in one file and works without a server
or an internet connection. Offline, your system's fonts stand in for the site's web fonts.

**Or run the source** in `index.html`, `css/`, `js/` and `data/`. Browsers won't let a page read its
data files straight from your disk, so serve the folder first. With Python installed, open a terminal
in this folder and run:

```
python -m http.server 8000
```

then go to http://localhost:8000.

## What's inside

- `index.html`: the page: a map with three stops, and one screen per chart
- `css/tokens.css`: the colors, type and sizes; `css/site.css`: the layout and the motion
- `js/`: one D3 module per chart (`chart1.js`, `chart2.js`, `chart3.js`), `views.js` (the screens),
  `landscape.js` (the map's moving background and its pause toggle), `tables.js` (a data table per
  chart), `tooltip.js`, `format.js` (number formats), `theme.js` (colors and motion) and `main.js`
  (loads and checks the data, draws the charts, wires the controls). D3 v7.9.0 is in `js/vendor/`
- `data/chart-data.json`: every number on the charts; `data/continents.json`: each country's continent

## Credits

Data: the World Happiness Report (Gallup World Poll), surveys 2019 to 2025. The page checks the
numbers against a fingerprint before it draws anything.

Made by David Doctor. The code was written with Claude (Anthropic), directed by David, who chose
every chart and interaction.
""", encoding="utf-8")

# the zip, one folder inside it
archive = root / "dist" / "world-happiness.zip"
archive.unlink(missing_ok=True)
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(out.rglob("*")):
        if path.is_file():
            z.write(path, Path("world-happiness") / path.relative_to(out))

files = [p for p in out.rglob("*") if p.is_file()]
print(f"wrote {out.relative_to(root)} ({len(files)} files) and {archive.relative_to(root)} "
      f"({archive.stat().st_size // 1024} KB); the single file is {(out / 'World Happiness.html').stat().st_size // 1024} KB")
