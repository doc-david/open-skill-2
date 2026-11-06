"""
check_page.py
the playbook's script checks: open the site in a headless browser, then compare what it
actually drew with chart-data.json, using a separate python rounding (not the page's code).

run: python scripts/check_page.py [--shots folder]
"""
import argparse
import functools
import http.server
import json
import threading
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent.parent
data = json.loads((root / "data" / "chart-data.json").read_text(encoding="utf-8"))
continents = json.loads((root / "data" / "continents.json").read_text(encoding="utf-8"))
MINUS = "−"


# python's own 2-decimal rounding, half away from zero, done with decimals instead of floats
def score2(v):
    d = Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return str(d).replace("-", MINUS)


def change2(v):
    d = Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if d == 0:
        return "0.00"
    return ("+" if d > 0 else MINUS) + str(abs(d))


results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", default=None)
    args = parser.parse_args()
    server = serve()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "ERR_TUNNEL_CONNECTION_FAILED" not in m.text else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#chart3 .segment", timeout=10000)

        # chart 1: 20 bars, each value label = score at 2 decimals, each bar 128px per point
        c1 = data["chart1_ranked_bar"]["top10"] + data["chart1_ranked_bar"]["bottom10"]
        drawn = page.eval_on_selector_all("#chart1 .row", """rows => rows.map(r => ({
            value: r.querySelector('.value').textContent,
            width: r.querySelector('.bar').getBBox().width,
            name: r.querySelectorAll('text')[1].textContent }))""")
        check("chart 1 has 20 rows", len(drawn) == 20, len(drawn))
        bad = [(d["name"], d["value"], score2(r["score"])) for d, r in zip(drawn, c1) if d["value"] != score2(r["score"]) or d["name"] != r["country"]]
        check("chart 1 labels match chart-data.json", not bad, bad)
        bad = [(r["country"], round(d["width"], 2)) for d, r in zip(drawn, c1) if abs(d["width"] - r["score"] * 128) > 0.5]
        check("chart 1 bars are score x 128px", not bad, bad)

        # chart 2: 133 lines, end labels = country + change
        lines = data["chart2_lines"]
        count = page.eval_on_selector_all("#chart2 svg > g[aria-hidden] path", "p => p.length")
        check("chart 2 draws 133 lines", count == 133, count)
        labels = page.eval_on_selector_all("#chart2 .label text", "t => t.map(x => x.textContent)")
        expected = [s["country"] + change2(s["change"]) for s in lines["risers"] + lines["fallers"]]
        check("chart 2 end labels match chart-data.json", sorted(labels) == sorted(expected), set(labels) ^ set(expected))
        others = page.text_content("#chart2-others")
        check("chart 2 note counts the other lines", others == str(len(lines["context_series"]) + len(lines["fallers"])), others)

        # chart 3: 42 segments, totals at 2 decimals, each row ends at score x 128px
        rows = data["chart3_stacked"]["rows"]
        seg = page.eval_on_selector_all("#chart3 .segment", "s => s.length")
        check("chart 3 draws 42 segments", seg == 42, seg)
        totals = page.eval_on_selector_all("#chart3 .row text.strong", "t => t.map(x => x.textContent)")
        check("chart 3 totals match chart-data.json", totals == [score2(r["score"]) for r in rows], totals)
        ends = page.eval_on_selector_all("#chart3 .row", "rows => rows.map(r => { const s = r.querySelectorAll('.segment'); const b = s[s.length - 1].getBBox(); return b.x + b.width; })")
        bad = [(r["country"], e) for r, e in zip(rows, ends) if abs(e - (328 + r["score"] * 128)) > 0.5]
        check("chart 3 rows end at score x 128px", not bad, bad)

        # no text anywhere may contain a brace, NaN, undefined or null
        text = page.inner_text("main")
        check("no template or NaN text", not any(t in text for t in ["{", "}", "NaN", "undefined", "null"]))

        # figma vs d3: every still loads, has alt text, and each pair shows the same chart region
        page.eval_on_selector_all(".compare img", "imgs => imgs.forEach(i => { i.loading = 'eager'; })")
        page.wait_for_function("[...document.querySelectorAll('.compare img')].every(i => i.complete)")
        stills = page.eval_on_selector_all(".compare img", "imgs => imgs.map(i => ({ src: i.getAttribute('src'), w: i.naturalWidth, alt: i.alt }))")
        figma = [s for s in stills if "/figma/" in s["src"]]
        d3s = [s for s in stills if "/d3/" in s["src"]]
        check("figma frames load at 1920px", len(figma) == 3 and all(s["w"] == 1920 for s in figma), figma)
        check("d3 stills load at figma's scale", len(d3s) == 3 and all(s["w"] == 1760 for s in d3s), d3s)
        check("every comparison image has alt text", all(s["alt"] for s in stills), stills)
        sizes = page.eval_on_selector_all(".pair", "pairs => pairs.map(p => [...p.querySelectorAll('.shot')].map(s => { const b = s.getBoundingClientRect(); return [Math.round(b.width), Math.round(b.height)]; }))")
        check("each figma and d3 pair is the same size", len(sizes) == 3 and all(a == b for a, b in sizes), sizes)

        if args.shots:
            Path(args.shots).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=f"{args.shots}/full.png", full_page=True)

        # interaction 1: the tooltip follows the pointer on a chart 1 bar
        bar = page.locator("#chart1 .bar").first
        box = bar.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        tip = page.inner_text(".tooltip")
        check("chart 1 tooltip shows on hover", "Finland" in tip and "Rank 1 of 147" in tip, tip.replace("\n", " | "))
        page.mouse.move(box["x"] + box["width"] / 3, box["y"] + box["height"] / 2)
        first = page.eval_on_selector(".tooltip", "t => t.style.transform")
        page.mouse.move(box["x"] + box["width"] / 3 + 60, box["y"] + box["height"] / 2)
        second = page.eval_on_selector(".tooltip", "t => t.style.transform")
        check("tooltip follows the cursor", first != second, f"{first} -> {second}")

        # interaction 2: hovering a grey line in chart 2 names it
        page.mouse.move(5, 5)
        page.locator("#chart2 svg").scroll_into_view_if_needed()
        svg = page.locator("#chart2 svg").bounding_box()
        scale = svg["width"] / 1760
        target = next(s for s in lines["context_series"] if s["country"] == "Brazil")
        px = svg["x"] + (176 + 3 * 212 - 80) * scale
        py = svg["y"] + (910 - target["scores"][3] * 62 - 200) * scale
        page.mouse.move(px, py)
        tip = page.inner_text(".tooltip")
        check("chart 2 hover names a grey line", tip.split("\n")[0] != "" and "2022:" in tip, tip.replace("\n", " | "))
        if args.shots:
            page.locator("#chart2").screenshot(path=f"{args.shots}/chart2-hover.png")
        page.mouse.move(5, 5)

        # interaction 3: the toggle swaps which five lines are navy
        page.click("#view-decliners")
        page.wait_for_timeout(450)
        navy = page.eval_on_selector_all("#chart2 svg > g[aria-hidden] path", "p => p.filter(x => ['#00376e', 'rgb(0, 55, 110)'].includes(x.getAttribute('stroke'))).map(x => x.__data__.country)")
        check("toggle highlights the decliners", sorted(navy) == sorted(s["country"] for s in lines["fallers"]), navy)
        if args.shots:
            page.locator("#chart2").screenshot(path=f"{args.shots}/chart2-decliners.png")

        # interaction 4: the continent filter fades the other continents on every chart.
        # rows must start with opacity 1, or the first transition starts from 0 and every row blinks
        start = page.eval_on_selector_all("#chart1 .row, #chart3 .row", "r => r.map(x => x.getAttribute('opacity'))")
        check("rows start at opacity 1 (no first-click blink)", all(o == "1" for o in start), start)
        page.click("#continent-africa")
        page.wait_for_timeout(450)
        faded = page.eval_on_selector_all("#chart1 .row", "r => r.map(x => [x.__data__.country, +x.getAttribute('opacity')])")
        bad = [(c, o) for c, o in faded if (continents[c] == "Africa") != (o == 1)]
        check("filter fades non-African bars on chart 1", not bad, bad)
        rows3 = page.eval_on_selector_all("#chart3 .row", "r => r.map(x => [x.__data__.country, +x.getAttribute('opacity')])")
        check("filter keeps only Mauritius solid on chart 3", [c for c, o in rows3 if o == 1] == ["Mauritius"], rows3)
        if args.shots:
            page.screenshot(path=f"{args.shots}/africa.png", full_page=True)
        page.click("#continent-oceania")
        page.wait_for_timeout(450)
        shown = page.eval_on_selector("#chart1 .empty", "e => ({ on: e.classList.contains('on'), text: e.textContent, opacity: +getComputedStyle(e).opacity, role: e.getAttribute('role'), pointer: getComputedStyle(e).pointerEvents })")
        check("chart 1 says when a continent has no countries", shown["on"] and "Oceania" in shown["text"] and shown["opacity"] == 1 and shown["role"] == "status", shown)
        check("the empty message never blocks the chart", shown["pointer"] == "none", shown)
        leaders = page.eval_on_selector_all("#chart2 svg > g:not([aria-hidden]) line", "l => l.map(x => x.getAttribute('opacity'))")
        check("chart 2 leader lines fade with their labels", leaders and "0.24" in leaders, leaders)
        page.click("#continent-all")
        page.wait_for_timeout(450)
        cleared = page.eval_on_selector("#chart1 .empty", "e => e.textContent")
        check("the empty message clears", cleared == "", cleared)

        # controls don't move when pressed: the toggle and the chips keep their size in both states
        size = "e => e.getBoundingClientRect().width"
        one = page.eval_on_selector("#view", size)
        page.click("#view-risers")
        page.wait_for_timeout(350)
        two = page.eval_on_selector("#view", size)
        check("the toggle keeps its width on click", abs(one - two) < 0.1, (one, two))
        before = page.eval_on_selector("#continent-north-america", size)
        page.click("#continent-north-america")
        after = page.eval_on_selector("#continent-north-america", size)
        check("a chip keeps its width when pressed", abs(before - after) < 0.1, (before, after))
        page.click("#continent-all")
        page.wait_for_timeout(350)

        # hovering chart 2 repaints only the lines that changed, not all of them
        page.locator("#chart2 svg").scroll_into_view_if_needed()
        svg = page.locator("#chart2 svg").bounding_box()
        scale = svg["width"] / 1760
        page.evaluate("""() => {
            window.pathWrites = 0;
            window.pathWatcher = new MutationObserver(m => { window.pathWrites += m.filter(x => ['stroke', 'stroke-width', 'opacity'].includes(x.attributeName)).length; });
            for (const p of document.querySelectorAll('#chart2 svg > g[aria-hidden] path')) window.pathWatcher.observe(p, { attributes: true });
        }""")
        for i in range(8):
            page.mouse.move(svg["x"] + (300 + i * 120 - 80) * scale, svg["y"] + (520 + i * 20 - 200) * scale)
        page.wait_for_timeout(100)
        writes = page.evaluate("window.pathWatcher.disconnect(), window.pathWrites")
        check("a hover repaints only the lines that changed", 0 < writes <= 8 * 2 * 3, writes)
        page.mouse.move(5, 5)

        # the filter bar has an edge once it sticks, and none before
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(100)
        flat = page.eval_on_selector(".filter-bar", "b => b.classList.contains('is-stuck')")
        page.evaluate("window.scrollTo(0, 1200)")
        page.wait_for_timeout(300)
        stuck = page.eval_on_selector(".filter-bar", "b => [b.classList.contains('is-stuck'), getComputedStyle(b).boxShadow]")
        check("the filter bar becomes a layer only when stuck", not flat and stuck[0] and stuck[1] != "none", (flat, stuck))
        page.evaluate("window.scrollTo(0, 0)")

        # phone width: the page itself never scrolls sideways
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(200)
        wide = page.evaluate("document.documentElement.scrollWidth")
        check("no sideways page scroll at 390px", wide <= 390, wide)
        if args.shots:
            page.screenshot(path=f"{args.shots}/phone.png", full_page=False)

        # someone who asks for less motion gets no fades and no delays, including the hover grace
        calm = browser.new_context(reduced_motion="reduce").new_page()
        calm.goto(url, wait_until="networkidle")
        calm.wait_for_selector("#chart3 .segment")
        reduced = calm.evaluate("""() => ['#chart1 .bar', '#chart3 .segment', '.tooltip', '.filter-bar', '.empty', '.segmented button'].map(s => {
            const c = getComputedStyle(document.querySelector(s));
            return [s, c.transitionDuration, c.transitionDelay];
        })""")
        reduced_ok = all(float(t.strip().rstrip("s")) == 0 for _, d, w in reduced for t in (d + "," + w).split(","))
        browser.close()

    check("no console errors", not errors, errors)
    check("reduced motion has no delayed hover fades", reduced_ok, reduced)
    server.shutdown()
    passed = sum(ok for _, ok, _ in results)
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))
    print(f"{passed}/{len(results)} checks passed")


if __name__ == "__main__":
    main()
