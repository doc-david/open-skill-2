---
name: World Happiness
description: A field guide to the World Happiness surveys, entered from a trail map, one chart at a time.
colors:
  forest: "#18322a"
  forest-edge: "#0b1a14"
  map-paper: "#f2f5ec"
  plate: "#fafbf7"
  field-grey: "#4f6157"
  chart-muted: "#55645a"
  highlighter: "#f2c14e"
  on-forest: "#f2f5ec"
  on-forest-secondary: "#b9c8b0"
  contour: "#2c4d40"
  chip-border: "#5f7a6a"
  icon-band: "#eef2e6"
  note-paper: "#fffdf6"
  context-sage: "#c4cebb"
  gridline: "#d3dbc9"
  zero-axis: "#7d8a7a"
  control-track: "#e3e9da"
  factor-gdp: "#4b4fb8"
  factor-social: "#946400"
  factor-life: "#007598"
  factor-freedom: "#c0294b"
  factor-generosity: "#94369e"
  factor-corruption: "#2f7a2a"
  factor-unexplained: "#8a9184"
typography:
  display:
    fontFamily: "National Park, Trebuchet MS, sans-serif"
    fontSize: "clamp(40px, 5vw, 64px)"
    fontWeight: 800
    lineHeight: 1
  chart-title:
    fontFamily: "National Park, Trebuchet MS, sans-serif"
    fontSize: "clamp(22px, 2.4vw, 30px)"
    fontWeight: 800
    lineHeight: 1.1
  reading:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "clamp(15px, 1.3vw, 17px)"
    fontWeight: 400
    lineHeight: 1.35
  ui:
    fontFamily: "IBM Plex Sans Condensed, Arial Narrow, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1
rounded:
  control: "3px"
  plate: "4px"
spacing:
  gutter: "20px"
  control-height: "44px"
components:
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.on-forest}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
    height: "44px"
  chip-pressed:
    backgroundColor: "{colors.highlighter}"
    textColor: "{colors.forest}"
    rounded: "{rounded.control}"
  button:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.forest}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
    height: "44px"
  chart-screen:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.forest}"
    rounded: "{rounded.plate}"
  stop:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.forest}"
    rounded: "{rounded.plate}"
  tooltip:
    backgroundColor: "{colors.note-paper}"
    textColor: "{colors.forest}"
    rounded: "{rounded.plate}"
    padding: "12px 14px"
---

# Design

Records what the code does as of the Field Guide build. Source of truth for values: `scripts/figma-variables.json`, generated into `css/tokens.css`. The full brief is in the vault (`toolbox/style-directions.md`).

## Overview

A printed field guide you can walk through. Home is a trail map on a forest ground; each chart is a numbered sheet of map paper, one screen at a time. On the page they're called charts (David, Nov 7); `plate` survives only as the name of the paper color and the 4px radius. The theme lives in the chrome. The charts keep their forms and their Figma geometry.

## Colors

- Forest is the one ink: text, bars, highlighted lines, focus on light.
- Highlighter is the one accent, used only for the markers, the selected chip and the current chart dot, and for focus on forest. It never marks data.
- Context lines stay sage, a grey, because David's note on chart 2 calls them grey lines. Any tinted context color makes that copy false.
- The seven pigments are for chart 3's factors only (dataviz validator on the paper color: colorblind 14.0, normal 15.7). A new mark that adds a hue goes through the validator against all of them.

## Typography

- National Park for display: the H1, chart titles, stop titles and markers.
- Source Serif 4 for reading: deks and notes.
- IBM Plex Sans Condensed for UI, tooltips, tables and every chart label, with tabular numerals. The widest country name takes 121.6 of the name column's 168 units at 24px.

## Layout

- One root fills the window: the HUD on top of a chart, one view under it. The map has no HUD (David, Nov 7). Only the view scrolls.
- A chart screen's rows are header, `minmax(0, 1fr)` chart, footer. The SVG is 100% by 100% and keeps its viewBox, so it scales without changing geometry.
- The map and each chart fit one screen, with nothing to scroll, on a 1080p screen at 100%, 125% and 150% scaling (windows about 1920x945, 1536x730 and 1280x585) and from 1280x720 up (David, Nov 7: no scrolling at 1920x1080). A chart screen keeps a 440px floor, so only a window under about 533px tall scrolls.
- The map is the kicker, the title and the three stops on moving contours, nothing else: no HUD and no continent filter. It's a site for visitors, not a project submission (David, Nov 7), so the course context lives in the README, not on the page.
- At 640px and under, views stack in normal page flow and wide charts scroll inside their box. A designed phone layout is out of scope.

## Elevation & Depth

Flat. Depth is a hard offset shadow with no blur, like a card laid on a map: chart screens `4px 4px 0` at 12% forest, stops `4px 4px 0` at 30% black, tooltips `3px 3px 0` at 18% forest.

## Shapes

3px on controls, 4px on chart screens, stops and tooltips, 1.5px forest borders. Circles only for markers and chart dots.

## Components

- HUD: forest bar with a 1.5px darker edge, on the charts only. Holds the single `#continent` group, which keeps its setting while you're on the map.
- Stop: a link with a numbered marker overlapping its top edge, an icon band, "Chart n", title and dek. Lifts 6px on a spring on hover while its marker swells to 1.12 and its shadow deepens (two shadow layers trading opacity, so nothing repaints), presses to 0.97. No trail line between the stops (David, Nov 7).
- Chart footer: Data table and source; no previous and next (David, Nov 7), since the HUD's dots and Back to the map move between views. An open table takes the chart's row and scrolls inside it.
- Tooltip: note paper with a forest border, values first. Never catches the pointer. Chart 2's is a small table (David, Nov 7: more readable): Change since 2019 first, then the scores for 2019, the year you're on (marked) and 2025, values right-aligned. Chart 2's five end labels show it on hover as well as focus.

Motion (David, Nov 7: bouncy, after a title screen he gave as a reference), all inside `prefers-reduced-motion: no-preference`. Springs are CSS `linear()` curves from `scripts/springs.py` (Apple-style duration and bounce), with the strong ease-out as the fallback:
- `--spring-quick` (0.35s, bounce 0.3) for controls: a press squashes to 0.95 in 100ms and springs back; the toggle's thumb, the table chevron and a stop's hover lift.
- `--spring-view` (0.45s, bounce 0.2) for screens: from the map a chart grows out of its stop (scale 0.92), and back on the map only its content grows from the stop while the forest ground and its lines are whole from the first frame (David, Nov 7: the background is always filled in); chart to chart slides 56px the way you moved. The view scroller hides overflow only while a screen overshoots.
- `--spring-bouncy` (0.5s, bounce 0.3) for the current chart's dot, the stops rising on first load, and chart 2's dots and end labels.
- `--spring-pop` (0.5s, bounce 0.45, about 12% overshoot) only for the map's first load: the title's letters pop in one at a time, then each stop's marker and icon. It goes past the animate skill's 0.3 on purpose, to match the reference.
- The map's background is the contour lines of a whole landscape, so it covers every part of the map (David, Nov 7): six broad hills drift slowly and the lines flow outward from their peaks forever, one line's step every 7s (linear, constant motion), traced each frame by marching squares on a canvas. Its lines have no top or bottom and the map has a gentle tilt, so every part of the background has lines at every moment. About 1.6ms a frame; it stops when a chart shows, the tab is hidden, reduced motion is on or the visitor pauses it with the small round toggle in the top right corner (WCAG 2.2.2; named Pause motion, pressed while paused, remembered in the browser, hidden with reduced motion).
- Chart marks arrive each time a chart opens: bars and stacked segments grow out of the zero line on the strong ease-out, and chart 2's five lines draw from 2019 to 2025 on the strong ease-in-out. Data marks never use a spring, because a bar that bounces past its value shows a wrong number. Keyboard focus finishes an entrance at once.
- Chart changes (filter, toggle) still run 300ms on the strong ease-in-out.

Keeping lag down (David, Nov 7): the charts are drawn after the map's intro, in idle time, or the moment one opens; each chart screen is then laid out once, invisibly, in idle time, which halves the cost of its first opening; the charts' font weights load while the map shows. Only transforms and opacity animate on HTML; SVG marks animate only while a chart opens.

## Do's and Don'ts

- Do keep every number behind `formatScore` and `formatChange`, and every data value out of typed copy.
- Do keep each viewBox, x0, the 128 px-per-point scales and the row pitches.
- Don't use highlighter or a pigment to mean anything new in a chart without running the validator.
- Don't add blur shadows, gradients, rounded pills or a second accent.
- Don't change a chart, interaction or piece of copy without David's OK.
