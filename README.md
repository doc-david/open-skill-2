# World Happiness, rebuilt in D3

INFO 4602 Open Skill 2 · CU Boulder · Fall 2026 · David Doctor

**Live site:** https://doc-david.github.io/open-skill-2/

The three World Happiness dashboards from Open Skill 1 were first built in Figma by directing Claude through the Figma connector. Here they're rebuilt in D3.js with the interactions Figma couldn't do.

| In Figma (Open Skill 1) | In D3 (Open Skill 2) |
|---|---|
| Tooltips were fixed boxes inside hover variants | One tooltip follows the cursor and flips at the window edge |
| Only the 10 highlighted lines on chart 2 could be hovered | All 133 lines can be hovered, with a crosshair that snaps to the survey year |
| One toggle, faked with component variants | An animated risers/decliners toggle (a D3 transition), plus a continent filter that links all three charts |
| Data pasted into every build script | One verified data file, loaded at runtime and fingerprint-checked before anything draws |

## How it's built
- `data/chart-data.json`: regenerated from the course CSV by Open Skill 1's `scripts/prep_data.py`. Its SHA-256 starts with `22c8681b`, byte-identical to Open Skill 1's verified file
- `data/continents.json`: each charted country's continent, using the same rule as chart 3 (`scripts/build_continents.py`)
- `css/tokens.css`: generated from the Figma file's variables (`scripts/figma_tokens.py`), so colors, type and spacing match the Figma dashboards
- `js/`: one D3 module per chart (`chart1.js`, `chart2.js`, `chart3.js`), plus `tooltip.js`, `format.js` (Open Skill 1's rounding rules), `theme.js` and `main.js`
- `scripts/check_page.py`: headless-browser checks that compare every drawn label, bar and interaction with the data

## Run it locally
```
python -m http.server 8000
```
Then open http://localhost:8000. The page fetches its JSON, so it needs a server rather than a double-clicked file.

## AI use
The code was written with Claude (Anthropic) and directed by David Doctor, who chose every chart and interaction. The data and design come from Open Skill 1.
