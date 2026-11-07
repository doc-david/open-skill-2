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
import sys
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
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", default=None)
    args = parser.parse_args()
    server = serve()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        fonts = ("fonts.googleapis.com", "fonts.gstatic.com")
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and not any(f in m.location.get("url", "") for f in fonts) else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#chart3 .segment", timeout=10000)
        off = page.eval_on_selector_all("#chart2 svg > g[aria-hidden='true']", "gs => gs.filter(g => g.querySelector('.label')).map(g => g.getAttribute('visibility'))")
        check("the hidden label set is hidden from first paint", off == ["hidden"], off)

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
        crops = page.eval_on_selector_all(".shot-figma", """shots => shots.map((s, i) => {
            const [vx, vy, vw] = document.querySelector(`#chart${i + 1} svg`).getAttribute('viewBox').split(' ').map(Number);
            const box = s.getBoundingClientRect(), im = s.querySelector('img'), img = im.getBoundingClientRect(), k = box.width / vw;
            return [img.left - box.left + vx * k, img.top - box.top + vy * k, im.getAttribute('src').includes(`chart${i + 1}-`)];
        })""")
        check("each figma crop shows its chart's viewbox", len(crops) == 3 and all(abs(x) < 0.5 and abs(y) < 0.5 and own for x, y, own in crops), crops)

        # data tables: every cell equals this script's own rounding of chart-data.json
        def table(chart):
            return page.eval_on_selector_all(f"{chart} .data-table tbody tr", "rows => rows.map(r => [...r.children].map(c => c.textContent))")

        expected = [[str(r["rank"]), r["country"], r["region"], score2(r["score"]), "n/a" if r["change_since_2019"] is None else change2(r["change_since_2019"])] for r in c1]
        got = table("#chart1")
        check("chart 1 table matches chart-data.json", got == expected, [(a, b) for a, b in zip(got, expected) if a != b])

        all_lines = lines["context_series"] + lines["risers"] + lines["fallers"]
        difference = lambda s: Decimal(str(s["scores"][6])) - Decimal(str(s["scores"][0]))
        expected = {s["country"]: [s["country"]] + [score2(v) for v in s["scores"]] + [change2(difference(s))] for s in all_lines}
        got = table("#chart2")
        bad = [g for g in got if expected.get(g[0]) != g]
        check("chart 2 table lists all 133 countries, matching chart-data.json", len(got) == 133 and not bad, (len(got), bad[:3]))

        order = data["chart3_stacked"]["factor_order"]
        expected = [[str(r["rank"]), r["country"], continents[r["country"]], score2(r["score"])] + [score2(r["unexplained"] if f == "Unexplained" else r["factors"][f]) for f in order] for r in rows]
        got = table("#chart3")
        check("chart 3 table matches chart-data.json", got == expected, [(a, b) for a, b in zip(got, expected) if a != b])

        heads = page.eval_on_selector_all(".data-table", "ts => ts.map(t => [t.querySelectorAll('thead th[scope=col]').length, t.querySelectorAll('tbody th[scope=row]').length, !!t.querySelector('table').getAttribute('aria-labelledby')])")
        check("tables have column and row headers and a name", heads == [[5, 20, True], [9, 133, True], [11, 6, True]], heads)
        closed = page.eval_on_selector_all(".data-table", "ts => ts.map(t => t.open)")
        check("tables start closed", closed == [False, False, False], closed)

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
        visible = lambda chart: page.eval_on_selector_all(f"{chart} .data-table tbody tr", "rows => rows.filter(r => !r.hidden).map(r => r.__data__.country)")
        african = lambda names: all(continents[n] == "Africa" for n in names)
        one, two, three = visible("#chart1"), visible("#chart2"), visible("#chart3")
        check("the filter also filters the tables", three == ["Mauritius"] and african(one) and african(two) and len(two) == sum(continents[s["country"]] == "Africa" for s in all_lines), (len(one), len(two), three))
        exposed = page.eval_on_selector_all("#chart1 .row, #chart3 .row, #chart2 g:not([aria-hidden]) > .label", "e => e.filter(x => x.getAttribute('aria-hidden') !== 'true').map(x => x.__data__.s ? x.__data__.s.country : x.__data__.country)")
        check("filtered-out marks leave the accessibility tree", african(exposed), exposed)
        page.click("#continent-oceania")
        page.wait_for_timeout(450)
        stops = page.eval_on_selector_all("#chart2 .label", "l => l.filter(x => x.getAttribute('tabindex') === '0').map(x => x.__data__.s.country)")
        check("faded chart 2 labels aren't tab stops", stops == [], stops)
        shown = page.eval_on_selector("#chart1 .empty", "e => ({ on: e.classList.contains('on'), text: e.textContent, opacity: +getComputedStyle(e).opacity, role: e.getAttribute('role'), pointer: getComputedStyle(e).pointerEvents })")
        check("chart 1 says when a continent has no countries", shown["on"] and "Oceania" in shown["text"] and shown["opacity"] == 1 and shown["role"] == "status", shown)
        check("the empty message never blocks the chart", shown["pointer"] == "none", shown)
        leaders = page.eval_on_selector_all("#chart2 svg > g:not([aria-hidden]) line", "l => l.map(x => x.getAttribute('opacity'))")
        check("chart 2 leader lines fade with their labels", leaders and "0.24" in leaders, leaders)
        page.click("#continent-all")
        page.wait_for_timeout(450)
        cleared = page.eval_on_selector("#chart1 .empty", "e => [e.textContent, e.classList.contains('on')]")
        check("the empty message clears", cleared == ["", False], cleared)

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

        # screen readers only get the highlighted set of labels, and rows and labels have a role
        page.evaluate("window.scrollTo(0, 0)")
        hidden = page.eval_on_selector_all("#chart2 svg > g", "gs => gs.filter(g => g.querySelector('.label')).map(g => [g.getAttribute('aria-hidden'), g.getAttribute('visibility'), g.querySelector('.label').__data__.s.country])")
        check("the hidden set of chart 2 labels is hidden from everyone", sorted(h[:2] for h in hidden if h[0]) == [["true", "hidden"]] and sum(1 for h in hidden if not h[0]) == 1, hidden)
        roles = page.eval_on_selector_all("#chart1 .row, #chart2 .label, #chart3 .row", "e => e.filter(x => x.getAttribute('role') !== 'img' || !x.getAttribute('aria-label')).length")
        check("rows and labels have a role and a name", roles == 0, roles)

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

        # keyboard paths, on a fresh page and a short window: tab through everything, forward and back
        keys = browser.new_page(viewport={"width": 1440, "height": 700})
        keys.goto(url, wait_until="networkidle")
        keys.wait_for_selector("#chart3 .segment")
        describe = """() => {
            const e = document.activeElement;
            const b = e.getBoundingClientRect();
            const bar = document.querySelector('.filter-bar').getBoundingClientRect();
            const tip = document.querySelector('.tooltip');
            return {
                name: e.id || (e.tagName === 'SUMMARY' ? 'summary' : e.classList.contains('row') ? 'row' : e.classList.contains('label') ? 'label' : e.tagName),
                under: !e.closest('.filter-bar') && b.top < bar.bottom - 1 && bar.top <= 8.5,
                tip: tip.classList.contains('visible'),
            };
        }"""
        forward = []
        for _ in range(60):
            keys.keyboard.press("Tab")
            keys.wait_for_timeout(10)
            step = keys.evaluate(describe)
            if step["name"] == "BODY":
                break
            forward.append(step)
        names = [s["name"] for s in forward]
        chips = [f"continent-{c}" for c in ["all", "africa", "asia", "europe", "north-america", "oceania", "south-america"]]
        want = chips + ["row"] * 20 + ["summary", "view-risers", "view-decliners"] + ["label"] * 5 + ["summary"] + ["row"] * 6 + ["summary"]
        check("tab reaches every control in reading order", names == want, names)
        check("focused rows and labels show a tooltip", all(s["tip"] for s in forward if s["name"] in ("row", "label")), [s["name"] for s in forward if s["name"] in ("row", "label") and not s["tip"]])
        check("forward focus never lands under the sticky bar", not any(s["under"] for s in forward), [s["name"] for s in forward if s["under"]])
        backward = []
        for _ in range(60):
            keys.keyboard.press("Shift+Tab")
            keys.wait_for_timeout(10)
            step = keys.evaluate(describe)
            if step["name"] == "BODY":
                break
            backward.append(step)
        check("backward focus never lands under the sticky bar", len(backward) >= len(want) - 1 and not any(s["under"] for s in backward), [s["name"] for s in backward if s["under"]])
        tip_rows = [s for s in backward if s["name"] in ("row", "label")]
        check("tooltips survive the scroll focus causes", all(s["tip"] for s in tip_rows), sum(not s["tip"] for s in tip_rows))

        # esc dismisses a focus tooltip and keeps focus
        keys.evaluate("window.scrollTo(0, 0)")
        for _ in range(8):
            keys.keyboard.press("Tab")
        keys.wait_for_timeout(100)
        shown = keys.evaluate(describe)
        keys.keyboard.press("Escape")
        keys.wait_for_timeout(250)
        after = keys.evaluate(describe)
        check("esc dismisses a tooltip and keeps focus", shown["tip"] and not after["tip"] and after["name"] == "row", (shown, after))

        # the tooltip stays with a focused row on scroll, and steps away when the row is off screen
        keys.keyboard.press("Tab")
        keys.wait_for_timeout(200)
        beside = keys.evaluate("() => { const r = document.activeElement.getBoundingClientRect(), t = document.querySelector('.tooltip').getBoundingClientRect(); return t.top < r.bottom + 40 && t.bottom > r.top - 40; }")
        keys.evaluate("window.scrollBy(0, 60)")
        keys.wait_for_timeout(200)
        still = keys.evaluate("() => { const r = document.activeElement.getBoundingClientRect(), t = document.querySelector('.tooltip').getBoundingClientRect(); return t.top < r.bottom + 40 && t.bottom > r.top - 40; }")
        keys.evaluate("window.scrollBy(0, 1600)")
        keys.wait_for_timeout(250)
        gone = keys.evaluate(describe)
        check("a focus tooltip stays with its row on scroll", beside and still and not gone["tip"], (beside, still, gone))

        # a mouse click on a country's name doesn't leave a tooltip or dimming behind
        keys.evaluate("document.activeElement.blur(); window.scrollTo(0, 0)")
        keys.wait_for_timeout(100)
        keys.locator("#chart1 .row", has_text="Iceland").locator("text").nth(1).click()
        keys.mouse.move(5, 5)
        keys.wait_for_timeout(300)
        pinned = keys.evaluate("[document.querySelector('.tooltip').classList.contains('visible'), document.querySelector('#chart1 svg').classList.contains('hovering')]")
        check("clicking a name doesn't pin a tooltip", pinned == [False, False], pinned)

        # data tables open from the keyboard, and the tall one scrolls inside its own box
        keys.evaluate("document.activeElement.blur(); window.scrollTo(0, 0)")
        keys.locator("#chart2 .data-table summary").focus()
        keys.keyboard.press("Enter")
        keys.wait_for_timeout(100)
        opened = keys.evaluate("(() => { const d = document.querySelector('#chart2 .data-table'), s = d.querySelector('.table-scroll'); return [d.open, s.scrollHeight > s.clientHeight, s.tabIndex]; })()")
        check("a data table opens with the keyboard and scrolls in its box", opened == [True, True, 0], opened)
        keys.keyboard.press("Enter")

        # a mouse parked on a line must not leave stale marks when the keyboard takes over
        park = """() => {
            document.querySelector('#chart2 svg').scrollIntoView({ block: 'center' });
            const b = document.querySelector('#chart2 svg').getBoundingClientRect();
            const s = b.width / 1760;
            return [b.x + (176 + 4 * 212 - 80) * s, b.y + (910 - %s * 62 - 200) * s];
        }""" % next(s for s in lines["fallers"] if s["country"] == "Afghanistan")["scores"][4]
        marks = """() => [document.querySelector('.tooltip .tooltip-title').textContent, document.querySelector('.tooltip').classList.contains('visible'), document.querySelector('#chart2 svg > line.axisline').getAttribute('visibility')]"""
        at = keys.evaluate(park)
        keys.wait_for_timeout(100)
        at = keys.evaluate(park)
        keys.mouse.move(at[0], at[1])
        keys.wait_for_timeout(100)
        hovering = keys.evaluate(marks)
        keys.locator("#continent-africa").focus()
        keys.keyboard.press("Enter")
        keys.wait_for_timeout(450)
        gone = keys.evaluate(marks)
        check("a filter that removes the hovered line removes its tooltip", hovering[0] == "Afghanistan" and hovering[1] and not gone[1] and gone[2] == "hidden", (hovering, gone))
        keys.locator("#continent-all").focus()
        keys.keyboard.press("Enter")
        keys.mouse.move(5, 5)
        keys.wait_for_timeout(450)
        at = keys.evaluate(park)
        keys.wait_for_timeout(100)
        keys.mouse.move(at[0], at[1])
        keys.wait_for_timeout(100)
        keys.locator("#view-decliners").focus()
        keys.keyboard.press("Tab")
        keys.wait_for_timeout(100)
        tabbed = keys.evaluate(marks)
        check("tabbing to a label clears a parked mouse's crosshair", tabbed[1] and tabbed[0] != "Afghanistan" and tabbed[2] == "hidden", tabbed)
        keys.close()

        # a tooltip opened on a phone-width window stays fully inside the window
        small = browser.new_page(viewport={"width": 390, "height": 844})
        small.goto(url, wait_until="networkidle")
        small.wait_for_selector("#chart3 .segment")
        for _ in range(11):
            small.keyboard.press("Tab")
        small.wait_for_timeout(250)
        edge = small.evaluate("(() => { const t = document.querySelector('.tooltip').getBoundingClientRect(); return [t.left, t.right, innerWidth]; })()")
        check("tooltips stay inside a narrow window", edge[0] >= 0 and edge[1] <= edge[2], edge)
        rect = "t => { const b = t.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom, innerWidth, innerHeight]; }"
        small.evaluate("fillTooltip('x', ['y']); placeTooltip(innerWidth + 200, innerHeight + 200)")
        high = small.eval_on_selector(".tooltip", rect)
        small.evaluate("placeTooltip(-200, -200)")
        low = small.eval_on_selector(".tooltip", rect)
        check("a tooltip is clamped on all four sides", high[2] <= high[4] and high[3] <= high[5] and low[0] >= 0 and low[1] >= 0, (high, low))
        small.close()

        # high contrast mode: chart text and marks use system colors, so they stay readable on black
        contrast = browser.new_context(forced_colors="active", color_scheme="dark").new_page()
        contrast.goto(url, wait_until="networkidle")
        contrast.wait_for_selector("#chart3 .segment")
        painted = contrast.evaluate("""() => {
            const name = getComputedStyle(document.querySelectorAll('#chart1 .row text')[1]).fill;
            const halo = getComputedStyle(document.querySelector('#chart1 .value')).stroke;
            const bar = document.querySelector('#chart1 .bar').getAttribute('fill');
            return [name, halo, bar];
        }""")
        check("high contrast mode recolors chart text and marks", painted[0] != "rgb(29, 29, 31)" and painted[1] != "rgb(255, 255, 255)" and painted[2].lower() != "#00376e", painted)
        contrast.close()

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
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
