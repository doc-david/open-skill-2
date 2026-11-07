# Product

<!-- impeccable:product-schema 1 -->

Written from the Product block in the vault (`toolbox/style-directions.md`, Nov 6, 2026). Nothing here is new; undecided items are marked.

## Platform

web

## Users

Professor Peck and the INFO 4602 class, who grade it; viewers of David's 3-minute video; later, portfolio visitors.

## Product Purpose

Show learning a grader can see: D3.js, used to rebuild Open Skill 1's three Figma dashboards with the interactions Figma couldn't do (cursor-following tooltips, hovering any grey line, one continent filter linking all three charts, an animated risers/decliners toggle). Make it fun to explore: a field guide to the survey's countries, one screen at a time, entered from a trail map, without changing what the charts are.

## Capabilities and Constraints

- Data truth: every number comes from `data/chart-data.json` (SHA-256 `22c8681b...`); never hand-edit it.
- Numbers only through `formatScore` and `formatChange` (2 decimals from whole thousandths, half away from zero, true minus sign). Never `toFixed`.
- Design tokens come from `scripts/figma-variables.json` through `scripts/figma_tokens.py`. Don't hand-edit `css/tokens.css`.
- Geometry parity: each chart's viewBox uses the Figma frame's coordinates.
- Course AI rule: AI may write code but doesn't decide what a chart is. David decides every chart, interaction and piece of copy; propose and ask.
- Scope fence: one page (screens are views, not pages); no React/Svelte, Code Connect, shaders, Runway or phone chart layout.
- Not built, and David's to reopen: Find a country, Surprise me, the passport, the tour, Figma vs D3 as a fourth stop.
- Terminology: plates (the three charts), the map, stops; risers, decliners (the data key stays `fallers`), continent filter, Score (0-10), title-case chart titles, sentence-case deks.

## Brand Commitments

Field Guide (David's pick, Nov 6): forest `#18322A`, map paper `#F2F5EC`, plate `#FAFBF7`, highlighter `#F2C14E`; National Park, Source Serif 4 and IBM Plex Sans Condensed; the validated pigment palette for the factors; light plates on a forest map.

## Evidence on Hand

- The course's World Happiness CSV and the verified chart data: `data/`.
- The Open Skill 1 Figma frames: `assets/figma/`, from file `VeubXsa5vUa3V05UDSWtMa`.
- No testimonials, users or outside reviews exist. Don't invent any.
