# CLAUDE.md: Open Skill 2 (World Happiness in D3)

Handoff from the claude.ai "Open Skill" project chat (Nov 6, 2026) to Claude Code, for refining the first draft. David directs; Claude builds.

## Start here
1. `git pull --ff-only` in this repo
2. Read the vault first (David's standing rule): `C:\David Projects\Github\ultimate-brain\school\info-4602\open-skill-2\` (on the PC it's under `D:\`). Read `open-skill-2.md` (status and decisions), `open-skill-2-playbook.md` (rules, Done means, Checks) and `toolbox/`. Pull the vault with `git pull --ff-only` before reading
3. Say in one line which playbook version you're working from

## What this is
- INFO 4602 Open Skill 2. The skill is **D3.js**: rebuilding the Open Skill 1 Figma dashboards with the interactions Figma couldn't do. The direction was picked by an LLM council on Nov 6
- Live site: https://doc-david.github.io/open-skill-2/ (GitHub Pages, from `main`, root folder). A push to `main` redeploys in about a minute
- Preview of the first draft: https://claude.ai/artifact/17ABKq4ZAuwVF7jBNLYMF5 (single-file build from `scripts/bundle.py`)
- Original: Figma file `VeubXsa5vUa3V05UDSWtMa` (World Happiness — Open Skill (INFO 4602)). Frames: `2:4` chart 1, `2:6` chart 2, `2:8` chart 3
- Deadline: tonight, Nov 6, with an extension possible. Still to come: the ~3-minute video and the ~1-page reflection (David's), and source files (this repo)

## Hard rules (don't break these while refining)
- **Data truth.** Never edit `data/chart-data.json` by hand. Regenerate it with `python scripts/prep_data.py --csv data/world-happiness-2019-2025.csv --out data/chart-data.json`, and its SHA-256 must still start with `22c8681b`. `js/main.js` refuses to draw if the fingerprint string changes
- **Numbers.** Use only `formatScore` and `formatChange` (`js/format.js`): 2 decimals from whole thousandths, half away from zero, with a true minus sign. Never `toFixed`
- **Course AI rule.** AI may write code but doesn't decide what a chart should be. David decides every chart, interaction and piece of copy, so propose and ask before changing them. Keep the AI-use comment in `js/main.js`
- **Design tokens** come from Figma: edit `scripts/figma-variables.json` (or re-pull with the Figma MCP `get_variable_defs`) and run `python scripts/figma_tokens.py`. Don't hand-edit `css/tokens.css`
- **Geometry parity.** Each chart's viewBox uses the Figma slide's coordinates (PRD §7), so the D3 charts line up with the Figma frames side by side. Keep x0, the 128 px-per-point scales and the row pitches unless David approves a change
- **David's Open Skill 1 decisions stand:** descriptive title-case titles, chart 1's hover target is the bar itself, "decliners" not "fallers" (the data key stays `fallers`), one navy accent `#00376E`, the factor palette as validated
- Scope fence: no React/Svelte, multi-page sites, Code Connect, shaders or Runway tonight

## How to run and check
- Serve: `python -m http.server 8000`, then open http://localhost:8000
- Checks (the playbook's script checks, run them before every push): `pip install playwright pandas` and `python -m playwright install chromium`, then `python scripts/check_page.py --shots shots`. The first draft passes 20/20
- Preview bundle for claude.ai: `python scripts/bundle.py` writes `dist/world-happiness.html` (git-ignored)

## Refinement brief (what David wants from this session)
Polish the first draft with Impeccable and the other design skills (apple-design fits the HIG system; frontend-design, emil-design-eng, design-critique, accessibility-review), within the rules above. Good targets:
- Typography and spacing rhythm on the masthead, panels and filter bar; the look stays Apple HIG, light, Inter
- The Figma-vs-D3 story on the page: download the three frame screenshots with the Figma MCP (`get_screenshot`, frames above) into `assets/figma/` and add a side-by-side or before/after per chart. That shot is the video's closing beat
- Accessibility: run the accessibility-review skill, add a data-table view per chart, and confirm keyboard paths (rows and labels are focusable, with tooltips on focus)
- Phone layout: charts currently keep a 760 px minimum and scroll sideways inside their own box
- Copy is David's call: chart 2's grey-lines note was drafted by Claude, so ask him to confirm or reword it

## Known issues
- Checker agent (clean context, Nov 6): all six Done means lines pass. It found three issues, all fixed: rows blinked on the first filter click, the sticky bar's grey label lost contrast over scrolling text, and hover fades ignored reduced motion
- The tooltip's secondary text color `#c7c7cc` is a literal (Figma's `text/on-dark-secondary` wasn't in the pulled variables)
- No data tables yet. No Figma screenshots in the repo yet
- Interactions were picked by David on Nov 6: cursor-following tooltips, hovering any grey line, a continent filter linking all three charts, and an animated risers/decliners toggle

## When you finish
Run the checks, commit with an `ai:` message, push, then write lessons and decisions back to the vault playbook and project note (bump `version`, add a Changelog line), and end with "Vault: read X, updated Y".
