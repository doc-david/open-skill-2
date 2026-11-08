---
name: World Happiness
description: A field guide to the World Happiness surveys, entered from a trail map, one plate at a time.
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
  stamp-ink: "#8c3b2e"
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
  plate-title:
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
  plate:
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

A printed field guide you can walk through. Home is a trail map on a forest ground; each chart is a numbered plate on map paper, one screen at a time. The theme lives in the chrome. The charts keep their forms and their Figma geometry.

## Colors

- Forest is the one ink: text, bars, highlighted lines, focus on light.
- Highlighter is the one accent, used only for the trail, markers, the selected chip and the current plate dot, and for focus on forest. It never marks data.
- Stamp ink appears only on Explored stamps.
- Context lines stay sage, a grey, because David's note on Plate 2 calls them grey lines. Any tinted context color makes that copy false.
- The seven pigments are for chart 3's factors only (dataviz validator on the plate color: colorblind 14.0, normal 15.7). A new mark that adds a hue goes through the validator against all of them.

## Typography

- National Park for display: the H1, plate titles, stop titles, markers and stamps.
- Source Serif 4 for reading: deks and notes.
- IBM Plex Sans Condensed for UI, tooltips, tables and every chart label, with tabular numerals. The widest country name takes 121.6 of the name column's 168 units at 24px.

## Layout

- One root fills the window: the HUD on top, one view under it. Only the view scrolls.
- A plate's rows are header, `minmax(0, 1fr)` chart, footer. The SVG is 100% by 100% and keeps its viewBox, so it scales without changing geometry.
- The map and each plate fit one screen from 1280x720 to 1920x1080. Below that height the view scrolls.
- The map is the kicker, the title and the three stops, nothing else. It's a site for visitors, not a project submission (David, Nov 7), so the course context lives in the README, not on the page.
- At 640px and under, views stack in normal page flow and wide charts scroll inside their box. A designed phone layout is out of scope.

## Elevation & Depth

Flat. Depth is a hard offset shadow with no blur, like a card laid on a map: plates `4px 4px 0` at 12% forest, stops `4px 4px 0` at 30% black, tooltips `3px 3px 0` at 18% forest.

## Shapes

3px on controls, 4px on plates, stops and tooltips, 1.5px forest borders. Circles only for markers and plate dots. The Explored stamp is rotated -8 degrees.

## Components

- HUD: forest bar with a 1.5px darker edge. Holds the single `#continent` group on every view.
- Stop: a link with a numbered marker overlapping its top edge, an icon band, "Plate n", title and dek. Lifts 3px on hover, presses to 0.98.
- Plate footer: Data table, source, previous and next. An open table takes the chart's row and scrolls inside it.
- Tooltip: note paper with a forest border, values first. Never catches the pointer.

Motion, all inside `prefers-reduced-motion: no-preference`: a view enters in 220ms from the stop you came from (scale 0.985, strong ease-out); plate to plate slides 16px the way you moved; stops rise once on first load, 60ms apart; a stamp lands once in 240ms. Chart changes run 300ms on a strong ease-in-out.

## Do's and Don'ts

- Do keep every number behind `formatScore` and `formatChange`, and every data value out of typed copy.
- Do keep each viewBox, x0, the 128 px-per-point scales and the row pitches.
- Don't use highlighter or a pigment to mean anything new in a chart without running the validator.
- Don't add blur shadows, gradients, rounded pills or a second accent.
- Don't change a chart, interaction or piece of copy without David's OK.
