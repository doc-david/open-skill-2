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


def open_view(page, name):
    """go to #map or #plate-n the way a link does, and wait for that view to show"""
    target = "#view-map" if name == "map" else f"#chart{name[-1]}"
    page.evaluate(f"location.hash = '#{name}'")
    page.wait_for_selector(f"{target}:not([hidden])")
    page.wait_for_timeout(280)


def to_screen(page, chart, x, y):
    """a point in the chart's figma coordinates, in window pixels. the svg letterboxes its viewbox
    to fit the plate, so the box's width alone doesn't give the scale"""
    return page.evaluate("""([chart, x, y]) => {
        const m = document.querySelector(chart + ' svg').getScreenCTM();
        return [m.a * x + m.e, m.d * y + m.f];
    }""", [chart, x, y])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", default=None)
    args = parser.parse_args()
    server = serve()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    errors = []

    try:
        run_checks(args, url, errors)
    except Exception as crash:
        check("the checks ran to the end", False, str(crash).splitlines()[0])
    server.shutdown()
    passed = sum(ok for _, ok, _ in results)
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))
    print(f"{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


def run_checks(args, url, errors):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        fonts = ("fonts.googleapis.com", "fonts.gstatic.com")
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and not any(f in m.location.get("url", "") for f in fonts) else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#chart3 .segment", state="attached", timeout=10000)
        off = page.eval_on_selector_all("#chart2 svg > g[aria-hidden='true']", "gs => gs.filter(g => g.querySelector('.label')).map(g => g.getAttribute('visibility'))")
        check("the hidden label set is hidden from first paint", off == ["hidden"], off)

        # chart 1: 20 bars, each value label = score at 2 decimals, each bar 128px per point
        open_view(page, "plate-1")
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
        open_view(page, "plate-3")
        rows = data["chart3_stacked"]["rows"]
        seg = page.eval_on_selector_all("#chart3 .segment", "s => s.length")
        check("chart 3 draws 42 segments", seg == 42, seg)
        totals = page.eval_on_selector_all("#chart3 .row text.strong", "t => t.map(x => x.textContent)")
        check("chart 3 totals match chart-data.json", totals == [score2(r["score"]) for r in rows], totals)
        ends = page.eval_on_selector_all("#chart3 .row", "rows => rows.map(r => { const s = r.querySelectorAll('.segment'); const b = s[s.length - 1].getBBox(); return b.x + b.width; })")
        bad = [(r["country"], e) for r, e in zip(rows, ends) if abs(e - (328 + r["score"] * 128)) > 0.5]
        check("chart 3 rows end at score x 128px", not bad, bad)

        # no text anywhere may contain a brace, NaN, undefined or null
        text = page.text_content("main")
        check("no template or NaN text", not any(t in text for t in ["{", "}", "NaN", "undefined", "null"]))

        open_view(page, "map")
        # a site for visitors, not a project submission (david, nov 7): no figma vs d3 section,
        # colophon, eyebrow, project paragraph or meta description, and a plain title
        leftovers = page.evaluate("""(() => {
            const gone = ['#compare', '.colophon', '.eyebrow', '.lede', '.below-fold', 'meta[name=description]'].filter(q => document.querySelector(q));
            const words = ['Figma', 'Open Skill', 'INFO 4602', 'rebuilt', 'D3'].filter(w => document.body.textContent.includes(w));
            return [gone, words, document.querySelector('h1').textContent];
        })()""")
        check("the page carries no project text", leftovers == [[], [], "World Happiness"], leftovers)

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
            page.screenshot(path=f"{args.shots}/map.png")

        # interaction 1: the tooltip follows the pointer on a chart 1 bar
        open_view(page, "plate-1")
        if args.shots:
            page.screenshot(path=f"{args.shots}/plate-1.png")
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
        open_view(page, "plate-2")
        target = next(s for s in lines["context_series"] if s["country"] == "Brazil")
        page.mouse.move(*to_screen(page, "#chart2", 176 + 3 * 212, 910 - target["scores"][3] * 62))
        tip = page.inner_text(".tooltip")
        check("chart 2 hover names a grey line", tip.split("\n")[0] != "" and "2022:" in tip, tip.replace("\n", " | "))
        if args.shots:
            page.screenshot(path=f"{args.shots}/plate-2-hover.png")
        page.mouse.move(5, 5)

        # chart 3's tooltip names the factor the way the legend does (david, nov 7: no "explained by")
        open_view(page, "plate-3")
        page.hover("#chart3 .row .segment")
        tip3 = page.inner_text(".tooltip").split("\n")
        legend = page.eval_on_selector_all("#chart3 .legend li", "l => l.map(x => x.textContent.trim())")
        check("chart 3 tooltip names the factor as the legend does", tip3[0] == "GDP per capita" and tip3[0] in legend and " points · " in tip3[1], (tip3, legend))
        page.mouse.move(5, 5)
        open_view(page, "plate-2")

        # interaction 3: the toggle swaps which five lines are forest
        page.click("#view-decliners")
        page.wait_for_timeout(450)
        forest = page.eval_on_selector_all("#chart2 svg > g[aria-hidden] path", "p => p.filter(x => ['#18322a', 'rgb(24, 50, 42)'].includes(x.getAttribute('stroke'))).map(x => x.__data__.country)")
        check("toggle highlights the decliners", sorted(forest) == sorted(s["country"] for s in lines["fallers"]), forest)
        if args.shots:
            page.screenshot(path=f"{args.shots}/plate-2-decliners.png")

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
            page.screenshot(path=f"{args.shots}/plate-2-africa.png")
            open_view(page, "plate-3")
            page.screenshot(path=f"{args.shots}/plate-3-africa.png")
            open_view(page, "plate-2")
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
        page.evaluate("""() => {
            window.pathWrites = 0;
            window.pathWatcher = new MutationObserver(m => { window.pathWrites += m.filter(x => ['stroke', 'stroke-width', 'opacity'].includes(x.attributeName)).length; });
            for (const p of document.querySelectorAll('#chart2 svg > g[aria-hidden] path')) window.pathWatcher.observe(p, { attributes: true });
        }""")
        for i in range(8):
            page.mouse.move(*to_screen(page, "#chart2", 300 + i * 120, 520 + i * 20))
        page.wait_for_timeout(100)
        writes = page.evaluate("window.pathWatcher.disconnect(), window.pathWrites")
        check("a hover repaints only the lines that changed", 0 < writes <= 8 * 2 * 3, writes)
        page.mouse.move(5, 5)

        # screen readers only get the highlighted set of labels, and rows and labels have a role
        hidden = page.eval_on_selector_all("#chart2 svg > g", "gs => gs.filter(g => g.querySelector('.label')).map(g => [g.getAttribute('aria-hidden'), g.getAttribute('visibility'), g.querySelector('.label').__data__.s.country])")
        check("the hidden set of chart 2 labels is hidden from everyone", sorted(h[:2] for h in hidden if h[0]) == [["true", "hidden"]] and sum(1 for h in hidden if not h[0]) == 1, hidden)
        roles = page.eval_on_selector_all("#chart1 .row, #chart2 .label, #chart3 .row", "e => e.filter(x => x.getAttribute('role') !== 'img' || !x.getAttribute('aria-label')).length")
        check("rows and labels have a role and a name", roles == 0, roles)

        # in a window too short for the map, the scroll keys reach the view from the bare page and
        # from the hud, arrows stay with a chip, and the hud stays put while the view scrolls
        scroller = browser.new_page(viewport={"width": 1280, "height": 400})
        scroller.goto(url, wait_until="networkidle")
        scroller.wait_for_selector("#chart3 .segment", state="attached")
        at = "document.querySelector('.views').scrollTop"
        scroller.keyboard.press("PageDown")
        from_page = scroller.evaluate(at)
        scroller.keyboard.press("Home")
        home = scroller.evaluate(at)
        scroller.keyboard.press("ArrowDown")
        arrow = scroller.evaluate(at)
        scroller.keyboard.press("Home")
        scroller.locator("#continent-asia").focus()
        scroller.keyboard.press("PageDown")
        from_chip = scroller.evaluate(at)
        scroller.keyboard.press("Home")
        scroller.keyboard.press("ArrowDown")
        arrow_chip = scroller.evaluate(at)
        scroller.keyboard.press("End")
        end = scroller.evaluate("(() => { const v = document.querySelector('.views'); return Math.abs(v.scrollTop + v.clientHeight - v.scrollHeight) < 2; })()")
        check("the scroll keys reach the view from the page and the hud", from_page > 50 and home == 0 and arrow > 0 and from_chip > 50 and arrow_chip == 0 and end, (from_page, home, arrow, from_chip, arrow_chip, end))
        held = scroller.evaluate("[document.querySelector('.hud').getBoundingClientRect().top, window.scrollY, document.querySelector('.views').scrollTop > 0]")
        check("the hud stays put while the map scrolls under it", held[0] == 0 and held[1] == 0 and held[2], held)
        scroller.close()

        # the data table's button never covers the source line, even with text spacing turned up
        spacing = browser.new_page(viewport={"width": 1280, "height": 720})
        spacing.goto(f"{url}#plate-1", wait_until="networkidle")
        spacing.wait_for_selector("#chart3 .segment", state="attached")
        spacing.add_style_tag(content="* { line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important; }")
        clear = spacing.evaluate("document.querySelector('#chart1 summary').getBoundingClientRect().right <= document.querySelector('#chart1 .panel-foot span').getBoundingClientRect().left")
        check("the data table button clears the source line at wide text spacing", clear, clear)
        spacing.close()

        # phone width: the page itself never scrolls sideways
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(200)
        wide = page.evaluate("document.documentElement.scrollWidth")
        check("no sideways page scroll at 390px", wide <= 390, wide)
        if args.shots:
            page.screenshot(path=f"{args.shots}/phone.png", full_page=False)

        # the map: three stops with david's titles and deks, in order, and the computed kicker
        nav = browser.new_page(viewport={"width": 1280, "height": 720})
        nav.goto(url, wait_until="networkidle")
        nav.wait_for_selector("#chart3 .segment", state="attached")
        titles = ["Happiest and Unhappiest Countries of 2025", "Score Change from 2019 to 2025", "Factors of Happiness in 2025"]
        deks = ["Top and bottom 10 ranked countries", "Top 5 risers and decliners", "Top-ranked country of each continent"]
        stops = nav.eval_on_selector_all(".stop", """s => s.map(x => [x.getAttribute('href'), x.querySelector('.stop-plate').textContent, x.querySelector('.stop-title').textContent,
            x.querySelector('.stop-dek').textContent, x.querySelector('.stop-icon svg').getAttribute('aria-hidden')])""")
        check("the map has three stops with david's titles and deks, in order", stops == [[f"#plate-{n + 1}", f"Plate {n + 1}", titles[n], deks[n], "true"] for n in range(3)], stops)
        same = nav.evaluate("[1, 2, 3].map(n => [document.querySelector(`#chart${n} h2`).textContent, document.querySelector(`#chart${n} .dek`).textContent])")
        check("each plate's title and dek match its stop", same == [[titles[n], deks[n]] for n in range(3)], same)
        kicker = nav.text_content(".kicker")
        count = len(lines["context_series"]) + len(lines["risers"]) + len(lines["fallers"])
        check("the kicker counts chart 2's countries", kicker == f"A field guide to {count} countries", kicker)
        check("one continent group, in the hud", nav.evaluate("[document.querySelectorAll('#continent').length, !!document.querySelector('.hud #continent')]") == [1, True])
        contours = nav.evaluate("(() => { const c = document.querySelector('.contours'); return [c.getAttribute('aria-hidden'), c.querySelectorAll('path').length]; })()")
        check("the contour lines are decorative and drawn", contours == ["true", 32], contours)

        # which view is showing, what has focus, and what the hud says
        where = """() => {
            const shown = [...document.querySelectorAll('.view')].filter(v => !v.hidden).map(v => v.id);
            const current = [...document.querySelectorAll('.hud-dots a')].filter(a => a.getAttribute('aria-current') === 'page').map(a => a.getAttribute('href'));
            return { shown, focus: document.activeElement.id || document.activeElement.tagName, count: document.getElementById('hud-plates').hidden ? null : document.getElementById('hud-count').textContent, current };
        }"""

        def go(selector):
            try:
                nav.click(selector, timeout=2000)
            except Exception:
                return {"could not click": selector}
            nav.wait_for_timeout(50)
            return nav.evaluate(where)

        at_map = {"shown": ["view-map"], "focus": "H1", "count": None, "current": []}
        at_plate = lambda n: {"shown": [f"chart{n}"], "focus": f"chart{n}-title", "count": f"Plate {n} of 3", "current": [f"#plate-{n}"]}
        first = nav.evaluate(where)
        check("the map shows first, with no plate controls", first["shown"] == ["view-map"] and first["count"] is None, first)
        got = []
        for n in (1, 2, 3):
            got.append(go(f".stop[data-plate='{n}']") == at_plate(n))
            got.append(go("#hud-back") == at_map)
        check("each stop opens its plate and focus lands on its heading; back returns to the map", all(got), got)
        got = [go(".stop[data-plate='1']") == at_plate(1), go(".hud-dots a[aria-label='Plate 3']") == at_plate(3), go(".hud-dots a[aria-label='Plate 2']") == at_plate(2)]
        check("the plate dots land on the right plate and mark it current", all(got), got)
        got = [go("#chart2 .plate-nav a:has-text('Plate 1')") == at_plate(1), go("#chart1 .plate-nav a:has-text('Plate 2')") == at_plate(2),
               go("#chart2 .plate-nav a:has-text('Plate 3')") == at_plate(3), go("#chart3 .plate-nav a:has-text('Plate 2')") == at_plate(2),
               go("#chart2 .plate-nav a:has-text('Plate 3')") == at_plate(3), go("#chart3 .plate-nav a:has-text('Back to the map')") == at_map]
        labels = nav.eval_on_selector_all(".plate-nav a", "a => a.map(x => x.textContent)")
        check("previous and next land on the right view, with the handoff's labels", all(got) and labels == ["Plate 2", "Plate 1", "Plate 3", "Plate 2", "Back to the map"], (got, labels))
        nav.go_back()
        nav.wait_for_timeout(100)
        back = nav.evaluate(where)
        nav.reload(wait_until="networkidle")
        nav.wait_for_selector("#chart3 .segment", state="attached")
        reloaded = nav.evaluate(where)
        check("the back button and a reload keep the view", back["shown"] == ["chart3"] and reloaded["shown"] == ["chart3"] and reloaded["count"] == "Plate 3 of 3" and reloaded["current"] == ["#plate-3"], (back, reloaded))
        nav.evaluate("location.hash = '#nowhere'")
        nav.wait_for_timeout(100)
        unknown = nav.evaluate(where)
        check("an unknown hash shows the map", unknown["shown"] == ["view-map"], unknown)

        # explored stamps: none before a visit, one after, and each lands once
        nav.goto("about:blank")
        nav.goto(url, wait_until="networkidle")
        nav.wait_for_selector("#chart3 .segment", state="attached")
        stamps = """() => [...document.querySelectorAll('.stop')].map(s => {
            const e = s.querySelector('.explored');
            return [!e.hidden, e.classList.contains('fresh'), s.textContent.includes(', explored') && !s.querySelector('.visually-hidden').hidden];
        })"""
        none = nav.evaluate(stamps)
        go(".stop[data-plate='2']")
        go("#hud-back")
        one = nav.evaluate(stamps)
        name = nav.get_by_role("link", name="Plate 2 Score Change from 2019 to 2025 Top 5 risers and decliners , explored").count()
        go(".stop[data-plate='3']")
        go("#hud-back")
        two = nav.evaluate(stamps)
        check("explored appears only after a visit, and lands once", none == [[False, False, False]] * 3 and one == [[False, False, False], [True, True, True], [False, False, False]] and two == [[False, False, False], [True, False, True], [True, True, True]], (none, one, two))
        check("a screen reader hears explored on the stop's link", name == 1, name)

        # the chips drive all three charts from the map and from every plate
        def solid():
            return nav.evaluate("""() => [
                [...document.querySelectorAll('#chart1 .row')].filter(r => r.getAttribute('opacity') === '1').map(r => r.__data__.country),
                [...document.querySelectorAll('#chart2 svg > g[aria-hidden] path')].filter(r => +r.getAttribute('opacity') === 1).map(r => r.__data__.country),
                [...document.querySelectorAll('#chart3 .row')].filter(r => r.getAttribute('opacity') === '1').map(r => r.__data__.country)]""")
        driven = []
        for view, chip, place in [("map", "europe", "Europe"), ("plate-1", "asia", "Asia"), ("plate-2", "africa", "Africa"), ("plate-3", "south-america", "South America")]:
            nav.evaluate(f"location.hash = '#{view}'")
            nav.wait_for_timeout(100)
            nav.click(f"#continent-{chip}")
            nav.wait_for_timeout(450)
            one_, two_, three_ = solid()
            everyone = [s["country"] for s in all_lines]
            ok = (sorted(one_) == sorted(r["country"] for r in c1 if continents[r["country"]] == place)
                  and sorted(two_) == sorted(c for c in everyone if continents[c] == place)
                  and sorted(three_) == sorted(r["country"] for r in rows if continents[r["country"]] == place)
                  and len(three_) == 1 and len(two_) > 0)
            driven.append((view, place, ok))
        check("the chips drive all three charts from the map and every plate", all(d[2] for d in driven), driven)
        nav.click("#continent-all")
        nav.wait_for_timeout(450)
        everything = [len(x) for x in solid()]
        check("the all chip brings every mark back", everything == [20, 133, 6], everything)
        nav.close()

        # keyboard paths, on a short window: tab through each view from the top, forward and back
        keys = browser.new_page(viewport={"width": 1440, "height": 700})
        describe = """() => {
            const e = document.activeElement;
            const b = e.getBoundingClientRect();
            const hud = document.querySelector('.hud').getBoundingClientRect();
            const tip = document.querySelector('.tooltip');
            return {
                name: e.id || (e.tagName === 'SUMMARY' ? 'summary' : e.tagName === 'A' ? e.getAttribute('href') : e.classList.contains('row') ? 'row' : e.classList.contains('label') ? 'label' : e.tagName),
                under: !e.closest('.hud') && e.tagName !== 'BODY' && b.top < hud.bottom - 1,
                tip: tip.classList.contains('visible'),
            };
        }"""

        def walk(key):
            steps = []
            for _ in range(60):
                keys.keyboard.press(key)
                keys.wait_for_timeout(10)
                step = keys.evaluate(describe)
                if step["name"] == "BODY":
                    break
                steps.append(step)
            return steps

        def load(view):
            keys.goto(f"{url}#{view}", wait_until="networkidle")
            keys.reload(wait_until="networkidle")
            keys.wait_for_selector("#chart3 .segment", state="attached")

        chips = [f"continent-{c}" for c in ["all", "africa", "asia", "europe", "north-america", "oceania", "south-america"]]
        hud = ["hud-back", "#plate-1", "#plate-2", "#plate-3"] + chips
        wants = {
            "map": chips + ["#plate-1", "#plate-2", "#plate-3"],
            "plate-1": hud + ["row"] * 20 + ["summary", "#plate-2"],
            "plate-2": hud + ["view-risers", "view-decliners"] + ["label"] * 5 + ["summary", "#plate-1", "#plate-3"],
            "plate-3": hud + ["row"] * 6 + ["summary", "#plate-2", "#map"],
        }
        for view, want in wants.items():
            load(view)
            forward = walk("Tab")
            names = [s["name"] for s in forward]
            check(f"tab reaches every control on {view} in reading order", names == want, names)
            check(f"focused rows and labels on {view} show a tooltip", all(s["tip"] for s in forward if s["name"] in ("row", "label")), [s["name"] for s in forward if s["name"] in ("row", "label") and not s["tip"]])
            check(f"forward focus on {view} never lands under the hud", not any(s["under"] for s in forward), [s["name"] for s in forward if s["under"]])
            backward = walk("Shift+Tab")
            check(f"backward focus on {view} never lands under the hud", len(backward) >= len(want) - 1 and not any(s["under"] for s in backward), [s["name"] for s in backward if s["under"]])
            tip_rows = [s for s in backward if s["name"] in ("row", "label")]
            check(f"tooltips on {view} survive the way back", all(s["tip"] for s in tip_rows), sum(not s["tip"] for s in tip_rows))

        # esc dismisses a focus tooltip and keeps focus
        load("plate-1")
        for _ in range(12):
            keys.keyboard.press("Tab")
        keys.wait_for_timeout(100)
        shown = keys.evaluate(describe)
        keys.keyboard.press("Escape")
        keys.wait_for_timeout(250)
        after = keys.evaluate(describe)
        check("esc dismisses a tooltip and keeps focus", shown["tip"] and not after["tip"] and after["name"] == "row", (shown, after))
        ring = keys.evaluate("""() => {
            const row = document.activeElement, bar = getComputedStyle(row.querySelector('.bar')), name = getComputedStyle(row.querySelectorAll('text')[1]);
            return [bar.stroke !== bar.fill && bar.stroke !== 'none', name.textDecorationLine];
        }""")
        check("a focused bar's ring shows against the bar, and its name is underlined", ring == [True, "underline"], ring)

        # a mouse click on a country's name doesn't leave a tooltip or dimming behind
        keys.evaluate("document.activeElement.blur()")
        keys.wait_for_timeout(100)
        keys.locator("#chart1 .row", has_text="Iceland").locator("text").nth(1).click()
        keys.mouse.move(5, 5)
        keys.wait_for_timeout(300)
        pinned = keys.evaluate("[document.querySelector('.tooltip').classList.contains('visible'), document.querySelector('#chart1 svg').classList.contains('hovering')]")
        check("clicking a name doesn't pin a tooltip", pinned == [False, False], pinned)

        # data tables open from the keyboard, take the chart's row, and the tall one scrolls inside its own box
        load("plate-2")
        keys.locator("#chart2 .data-table summary").focus()
        keys.keyboard.press("Enter")
        keys.wait_for_timeout(100)
        opened = keys.evaluate("""(() => {
            const d = document.querySelector('#chart2 .data-table'), s = d.querySelector('.table-scroll');
            const row = document.querySelector('#chart2 .chart-row').getBoundingClientRect(), box = s.getBoundingClientRect();
            const inRow = Math.abs(box.top - row.top) < 1 && Math.abs(box.bottom - row.bottom) < 1 && Math.abs(box.left - row.left) < 1 && Math.abs(box.right - row.right) < 1;
            return [d.open, s.scrollHeight > s.clientHeight, s.tabIndex, inRow, getComputedStyle(document.querySelector('#chart2 .chart-wrap')).visibility, document.documentElement.scrollWidth <= innerWidth];
        })()""")
        check("a data table opens with the keyboard, takes the chart's row and scrolls in its box", opened == [True, True, 0, True, "hidden", True], opened)
        keys.keyboard.press("Enter")
        keys.wait_for_timeout(100)

        # a mouse parked on a line must not leave stale marks when the keyboard takes over
        afghanistan = next(s for s in lines["fallers"] if s["country"] == "Afghanistan")["scores"][4]
        park = lambda: to_screen(keys, "#chart2", 176 + 4 * 212, 910 - afghanistan * 62)
        marks = """() => [document.querySelector('.tooltip .tooltip-title').textContent, document.querySelector('.tooltip').classList.contains('visible'), document.querySelector('#chart2 svg > line.axisline').getAttribute('visibility')]"""
        keys.mouse.move(*park())
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
        keys.mouse.move(*park())
        keys.wait_for_timeout(100)
        keys.locator("#view-decliners").focus()
        keys.keyboard.press("Tab")
        keys.wait_for_timeout(100)
        tabbed = keys.evaluate(marks)
        check("tabbing to a label clears a parked mouse's crosshair", tabbed[1] and tabbed[0] != "Afghanistan" and tabbed[2] == "hidden", tabbed)
        keys.close()

        # on a window too short for the plate, the view scrolls: a focus tooltip stays with its row,
        # and steps away once the row has scrolled out of the view behind the hud
        short = browser.new_page(viewport={"width": 1440, "height": 420})
        short.goto(f"{url}#plate-1", wait_until="networkidle")
        short.wait_for_selector("#chart3 .segment", state="attached")
        for _ in range(12):
            short.keyboard.press("Tab")
        short.wait_for_timeout(200)
        near = "() => { const r = document.activeElement.getBoundingClientRect(), t = document.querySelector('.tooltip').getBoundingClientRect(); return t.top < r.bottom + 40 && t.bottom > r.top - 40; }"
        visible = "document.querySelector('.tooltip').classList.contains('visible')"
        beside = short.evaluate(near)
        short.evaluate("document.querySelector('.views').scrollBy(0, 20)")
        short.wait_for_timeout(200)
        still = short.evaluate(near) and short.evaluate(visible)
        short.evaluate("document.querySelector('.views').scrollBy(0, 400)")
        short.wait_for_timeout(250)
        away = short.evaluate(visible)
        check("a focus tooltip stays with its row on scroll, and steps away behind the hud", beside and still and not away, (beside, still, away))
        short.close()

        # a tooltip opened on a phone-width window stays fully inside the window
        small = browser.new_page(viewport={"width": 390, "height": 844})
        small.goto(f"{url}#plate-1", wait_until="networkidle")
        small.wait_for_selector("#chart3 .segment", state="attached")
        for _ in range(15):
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
        contrast.goto(f"{url}#plate-1", wait_until="networkidle")
        contrast.wait_for_selector("#chart3 .segment", state="attached")
        painted = contrast.evaluate("""() => {
            const name = getComputedStyle(document.querySelectorAll('#chart1 .row text')[1]).fill;
            const halo = getComputedStyle(document.querySelector('#chart1 .value')).stroke;
            const bar = document.querySelector('#chart1 .bar').getAttribute('fill');
            return [name, halo, bar];
        }""")
        check("high contrast mode recolors chart text and marks", painted[0] != "rgb(24, 50, 42)" and painted[1] != "rgb(250, 251, 247)" and painted[2].lower() != "#18322a", painted)
        contrast.close()

        # one screen from 1280x720 to 1920x1080: nothing scrolls, and each chart keeps its figma viewbox
        boxes = {1: "80 200 1760 760", 2: "80 200 1760 760", 3: "80 280 1760 680"}
        fits = []
        for size in ((1280, 720), (1366, 768), (1920, 1080)):
            fit = browser.new_page(viewport={"width": size[0], "height": size[1]})
            fit.goto(url, wait_until="networkidle")
            fit.wait_for_selector("#chart3 .segment", state="attached")
            ground = fit.evaluate("(() => { const v = document.querySelector('.views'), g = document.querySelector('.map-ground'); return g.offsetHeight <= v.clientHeight + 1 && g.scrollHeight <= g.clientHeight + 1 && g.getBoundingClientRect().bottom <= innerHeight + 1; })()")
            fits.append((size, "map", ground))
            for n in (1, 2, 3):
                open_view(fit, f"plate-{n}")
                state = fit.evaluate(f"""(() => {{
                    const v = document.querySelector('.views'), svg = document.querySelector('#chart{n} .chart svg');
                    const row = document.querySelector('#chart{n} .chart-row').getBoundingClientRect(), box = svg.getBoundingClientRect();
                    return [v.scrollHeight <= v.clientHeight + 1, document.documentElement.scrollHeight <= innerHeight, Math.abs(box.width - row.width) < 1 && Math.abs(box.height - row.height) < 1, svg.getAttribute('viewBox'), row.height > 300];
                }})()""")
                fits.append((size, n, state == [True, True, True, boxes[n], True], state))
            fit.close()
        check("the map and each plate fit one screen from 1280x720 to 1920x1080", all(f[2] for f in fits), [f for f in fits if not f[2]])

        # no sideways scroll at 390px on any view, including with a table open
        narrow = browser.new_page(viewport={"width": 390, "height": 844})
        narrow.goto(url, wait_until="networkidle")
        narrow.wait_for_selector("#chart3 .segment", state="attached")
        widths = []
        for view in ("map", "plate-1", "plate-2", "plate-3"):
            open_view(narrow, view)
            widths.append(narrow.evaluate("document.documentElement.scrollWidth"))
            if view != "map":
                narrow.click(f"#chart{view[-1]} .data-table summary")
                narrow.wait_for_timeout(50)
                widths.append(narrow.evaluate("document.documentElement.scrollWidth"))
        check("no sideways scroll at 390px on any view, tables open or closed", all(w <= 390 for w in widths), widths)
        if args.shots:
            open_view(narrow, "map")
            narrow.screenshot(path=f"{args.shots}/phone-map.png")
        narrow.close()

        # motion: the classes land where the handoff says
        moving = browser.new_page(viewport={"width": 1280, "height": 720})
        moving.goto(url, wait_until="networkidle")
        moving.wait_for_selector("#chart3 .segment", state="attached")
        step = lambda selector, probe: (moving.click(selector), moving.wait_for_timeout(40), moving.evaluate(probe))[2]
        intro = moving.eval_on_selector_all(".stop.intro", "s => s.map(x => getComputedStyle(x).animationName + ' ' + getComputedStyle(x).animationDelay)")
        check("the stops rise in on first load, 60ms apart", intro == ["stop-in 0s", "stop-in 0.06s", "stop-in 0.12s"], intro)
        grown = step(".stop[data-plate='3']", "(() => { const v = document.getElementById('chart3'), c = getComputedStyle(v); return [v.classList.contains('view-in'), c.animationDuration, v.style.transformOrigin, document.getAnimations().some(a => a.animationName === 'view-in')]; })()")
        check("a plate grows from the stop you came from", grown == [True, "0.22s", "82% 64%", True], grown)
        slid = [step(".hud-dots a[href='#plate-1']", "document.getElementById('chart1').className"), step(".hud-dots a[href='#plate-2']", "document.getElementById('chart2').className")]
        check("plate to plate slides the way you moved", "plate-from-left" in slid[0] and "plate-from-right" in slid[1], slid)
        later = step("#hud-back", "[document.querySelectorAll('.stop.intro').length, document.getElementById('view-map').classList.contains('view-in'), document.getElementById('view-map').style.transformOrigin]")
        check("the stops don't rise again on later visits", later == [0, True, "50% 64%"], later)
        moving.wait_for_timeout(300)
        moving.hover(".stop[data-plate='1']")
        moving.wait_for_timeout(250)
        lift = moving.eval_on_selector(".stop[data-plate='1']", "s => getComputedStyle(s).transform")
        check("hovering lifts a stop 3px", lift == "matrix(1, 0, 0, 1, 0, -3)", lift)
        moving.close()

        # someone who asks for less motion gets no moving screens, and no transforms from any of it
        still = browser.new_context(reduced_motion="reduce", viewport={"width": 1280, "height": 720}).new_page()
        still.goto(url, wait_until="networkidle")
        still.wait_for_selector("#chart3 .segment", state="attached")
        probe = """() => [document.getAnimations().filter(a => a.animationName).map(a => a.animationName),
            getComputedStyle(document.querySelector('.view:not([hidden])')).transform,
            [...document.querySelectorAll('.stop')].map(s => getComputedStyle(s).transform)]"""
        seen_ = [still.evaluate(probe)]
        still.click(".stop[data-plate='1']")
        still.wait_for_timeout(40)
        seen_.append(still.evaluate(probe))
        still.click(".hud-dots a[href='#plate-2']")
        still.wait_for_timeout(40)
        seen_.append(still.evaluate(probe))
        still.click("#hud-back")
        still.wait_for_timeout(40)
        seen_.append(still.evaluate(probe))
        still.hover(".stop[data-plate='2']")
        still.wait_for_timeout(250)
        seen_.append(still.evaluate(probe))
        check("reduced motion adds no animations or transforms", all(a == [] and t == "none" and all(x == "none" for x in st) for a, t, st in seen_), seen_)
        still.close()

        # change one score in the data: the page refuses to draw, says so, and stays quiet afterwards
        tampered = browser.new_page(viewport={"width": 1280, "height": 720})
        problems = []
        tampered.on("pageerror", lambda e: problems.append(str(e)))

        def tamper(route):
            changed = json.loads(json.dumps(data))
            changed["chart1_ranked_bar"]["top10"][0]["score"] += 0.01
            route.fulfill(json=changed)

        tampered.route("**/data/chart-data.json", tamper)
        tampered.goto(url, wait_until="networkidle")
        tampered.wait_for_timeout(300)
        refused = tampered.evaluate("[(document.querySelector('.error') || {}).textContent || '', document.querySelectorAll('.row').length, !!document.querySelector('.hud')]")
        tampered.evaluate("location.hash = '#plate-2'")
        tampered.wait_for_timeout(100)
        check("changed data is refused, with a message and no errors after", "doesn’t match" in refused[0] and refused[1:] == [0, False] and not problems, (refused, problems))
        tampered.close()

        # someone who asks for less motion gets no fades and no delays, including the hover grace
        calm = browser.new_context(reduced_motion="reduce").new_page()
        calm.goto(f"{url}#plate-1", wait_until="networkidle")
        calm.wait_for_selector("#chart3 .segment", state="attached")
        reduced = calm.evaluate("""() => ['#chart1 .bar', '#chart3 .segment', '.tooltip', '.empty', '.segmented button', '#continent-all'].map(s => {
            const c = getComputedStyle(document.querySelector(s));
            return [s, c.transitionDuration, c.transitionDelay];
        })""")
        reduced_ok = all(float(t.strip().rstrip("s")) == 0 for _, d, w in reduced for t in (d + "," + w).split(","))
        browser.close()

    check("no console errors", not errors, errors)
    check("reduced motion has no delayed hover fades", reduced_ok, reduced)


if __name__ == "__main__":
    main()
