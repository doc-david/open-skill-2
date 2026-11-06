"""
capture_d3.py
takes the d3 stills for the "what figma couldn't do" section, from the real page in the state
that answers each figma limit. the svg is forced to 880 css px at 2x, so one viewbox unit is one
image pixel, the same scale as the figma frame screenshots in assets/figma/.

run after any change to the charts: python scripts/capture_d3.py
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from check_page import serve

root = Path(__file__).resolve().parent.parent
out = root / "assets" / "d3"
data = json.loads((root / "data" / "chart-data.json").read_text(encoding="utf-8"))

# the same width for every chart, and no sticky bar over the charts
CSS = """
.chart svg { width: 880px !important; min-width: 0 !important; }
.chart { overflow: visible !important; }
.filter-bar { position: static !important; }
"""


def clip_of(page, chart, block="center"):
    page.evaluate(f"document.querySelector('{chart} svg').scrollIntoView({{ block: '{block}' }})")
    return page.locator(f"{chart} svg").bounding_box()


def main():
    out.mkdir(parents=True, exist_ok=True)
    server = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 1000}, device_scale_factor=2)
        page.goto(f"http://127.0.0.1:{server.server_port}/index.html", wait_until="networkidle")
        page.wait_for_selector("#chart3 .segment")
        page.add_style_tag(content=CSS)
        page.evaluate("document.fonts.ready")

        # chart 1: the tooltip on a hovered bar, the other bars stepped back
        box = clip_of(page, "#chart1")
        bar = page.locator("#chart1 .row", has_text="Denmark").locator(".bar").bounding_box()
        page.mouse.move(bar["x"] + bar["width"] * 0.62, bar["y"] + bar["height"] / 2)
        page.wait_for_timeout(300)
        page.screenshot(path=str(out / "chart1-d3.png"), clip=box)
        page.mouse.move(2, 2)

        # chart 2: a grey line figma couldn't name. the chart sits at the window's bottom edge,
        # so the tooltip flips up instead of being cut off by the crop
        box = clip_of(page, "#chart2", block="end")
        scale = box["width"] / 1760
        grey = next(s for s in data["chart2_lines"]["fallers"] if s["country"] == "Afghanistan")
        px = box["x"] + (176 + 4 * 212 - 80) * scale
        py = box["y"] + (910 - grey["scores"][4] * 62 - 200) * scale
        page.mouse.move(px, py)
        page.wait_for_timeout(300)
        page.screenshot(path=str(out / "chart2-d3.png"), clip=box)
        page.mouse.move(2, 2)

        # chart 3: the continent filter that links all three charts
        page.click("#continent-europe")
        page.wait_for_timeout(500)
        page.mouse.move(2, 2)
        box = clip_of(page, "#chart3")
        page.wait_for_timeout(200)
        page.screenshot(path=str(out / "chart3-d3.png"), clip=box)
        browser.close()
    server.shutdown()
    for f in sorted(out.glob("*.png")):
        print(f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
