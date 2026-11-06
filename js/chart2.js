// chart 2: score change from 2019 to 2025.
// the svg's viewbox uses the figma slide's own coordinates (open skill 1 prd, section 7, f2),
// so every x and y below can be checked against the prd and the figma frame.
function chart2(data, continents) {
  const lines = data.chart2_lines;
  const svg = d3.select("#chart2 svg").attr("viewBox", "80 200 1760 760");

  // scales: in altair this is alt.X("year:O") and alt.Y("score:Q", scale=alt.Scale(domain=[0, 10])).
  // in d3 we build the mapping ourselves: a data value goes in, a pixel position comes out
  const x = d3.scaleLinear().domain([2019, 2025]).range([176, 1448]);
  const y = d3.scaleLinear().domain([lines.y_axis.min, lines.y_axis.max]).range([910, 290]);

  // change since 2019 in whole thousandths, so floating point can't nudge a rounding
  const change = s => (Math.round(s.scores[6] * 1000) - Math.round(s.scores[0] * 1000)) / 1000;

  // every country surveyed in all seven years: 123 grey + 5 risers + 5 decliners = 133 lines
  const series = [...lines.context_series, ...lines.risers, ...lines.fallers]
    .map(s => ({ country: s.country, scores: s.scores, change: change(s), continent: continents[s.country] }));
  const byCountry = new Map(series.map(s => [s.country, s]));
  const risers = new Set(lines.risers.map(s => s.country));
  const decliners = new Set(lines.fallers.map(s => s.country));
  d3.select("#chart2-others").text(series.length - risers.size);

  // what the chart is showing right now: the toggle, the continent filter and the hovered line
  const state = { view: "risers", continent: "All", hover: null };
  const highlighted = s => (state.view === "risers" ? risers : decliners).has(s.country);
  const included = s => state.continent === "All" || s.continent === state.continent;

  // gridlines at 0, 2, 4, 6, 8, 10; the 0 line is darker, like the bar charts' zero line
  svg.append("g").selectAll("line").data(lines.y_axis.ticks).join("line")
    .attr("class", d => d === 0 ? "axisline" : "gridline")
    .attr("x1", 176).attr("x2", 1448)
    .attr("y1", d => y(d)).attr("y2", d => y(d));

  // tick labels sit right-aligned in a box from x 80 to 160, centered on each gridline
  svg.append("g").selectAll("text").data(lines.y_axis.ticks).join("text")
    .attr("class", "t-footnote muted")
    .attr("x", 160).attr("y", d => y(d))
    .attr("text-anchor", "end").attr("dominant-baseline", "central")
    .text(d => d);

  svg.append("g").selectAll("text").data(lines.years).join("text")
    .attr("class", "t-footnote muted")
    .attr("x", d => x(d)).attr("y", 943)
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .text(d => d);

  svg.append("text").attr("class", "t-footnote muted")
    .attr("x", 80).attr("y", 228).attr("dominant-baseline", "central")
    .text("Score (0–10)");

  // the crosshair goes under the lines so it never covers them
  const crosshair = svg.append("line").attr("class", "axisline")
    .attr("y1", 290).attr("y2", 910).attr("visibility", "hidden");

  // d3.line turns one country's seven scores into one svg path.
  // the data join (.data(...).join("path")) makes one path per country; the key is the country name
  const line = d3.line().x((d, i) => x(lines.years[i])).y(d => y(d));
  const paths = svg.append("g").attr("aria-hidden", "true")
    .selectAll("path").data(series, s => s.country).join("path")
    .attr("fill", "none")
    .attr("stroke-linejoin", "round").attr("stroke-linecap", "round")
    .attr("d", s => line(s.scores));
  const nodeOf = new Map();
  paths.each(function (s) { nodeOf.set(s, this); });

  // dots at 2019 and 2025 for the ten countries the toggle can highlight
  const ends = series.filter(s => risers.has(s.country) || decliners.has(s.country))
    .flatMap(s => [{ s, year: 2019, score: s.scores[0] }, { s, year: 2025, score: s.scores[6] }]);
  const dots = svg.append("g").attr("aria-hidden", "true")
    .selectAll("circle").data(ends).join("circle")
    .attr("cx", d => x(d.year)).attr("cy", d => y(d.score))
    .attr("fill", colors.focus).attr("stroke", colors.paper).attr("stroke-width", 4)
    .style("paint-order", "stroke");

  // the dot that rides along the hovered line
  const marker = svg.append("circle").attr("r", 6)
    .attr("stroke", colors.paper).attr("stroke-width", 4).style("paint-order", "stroke")
    .attr("visibility", "hidden").attr("pointer-events", "none");

  // end labels use open skill 1's collision rule: sort top to bottom, keep labels 36px apart,
  // shift them all up if the last one would fall below the plot, and draw a leader to any moved label
  function layout(set) {
    const items = set.map(s => ({ s: byCountry.get(s.country), y0: y(s.scores[6]) })).sort((a, b) => a.y0 - b.y0);
    let previous = -Infinity;
    for (const item of items) {
      item.y = Math.max(item.y0, previous + 36);
      previous = item.y;
    }
    const overflow = items[items.length - 1].y + 18 - 910;
    if (overflow > 0) items.forEach(item => { item.y -= overflow; });
    return items;
  }

  const labelSets = {};
  for (const [view, set] of [["risers", lines.risers], ["decliners", lines.fallers]]) {
    const group = svg.append("g");
    const items = layout(set);
    group.selectAll("line").data(items.filter(d => Math.abs(d.y - d.y0) > 4)).join("line")
      .attr("x1", 1456).attr("y1", d => d.y0).attr("x2", 1468).attr("y2", d => d.y)
      .attr("stroke", colors.muted).attr("stroke-width", 1);
    const label = group.selectAll("g").data(items).join("g")
      .attr("class", "label")
      .attr("aria-label", d => `${d.s.country}: 2019 ${formatScore(d.s.scores[0])}, 2025 ${formatScore(d.s.scores[6])}, change ${formatChange(d.s.change)}`);
    const text = label.append("text").attr("class", "t-footnote")
      .attr("x", 1472).attr("y", d => d.y).attr("dominant-baseline", "central");
    text.append("tspan").attr("class", "strong ink").text(d => d.s.country);
    text.append("tspan").attr("class", "muted").attr("dx", 12).text(d => formatChange(d.s.change));
    // keyboard: tab to a label to light up its line, with the same tooltip as hovering
    label.on("focus", function (event, d) {
      paintHover(d.s);
      showTooltipAt(this, d.s.country, tip(d.s, 2025));
    }).on("blur", leave);
    labelSets[view] = group;
  }

  // an invisible rectangle over the plot catches the pointer, so nobody has to land on a 1.5px line
  svg.append("rect")
    .attr("x", 176).attr("y", 290).attr("width", 1272).attr("height", 620)
    .attr("fill", "transparent")
    .on("pointermove", hover)
    .on("pointerleave", leave);

  function tip(s, year) {
    return [
      `${year}: ${formatScore(s.scores[year - 2019])}`,
      `2019 → 2025: ${formatScore(s.scores[0])} → ${formatScore(s.scores[6])}`,
      `Change since 2019: ${formatChange(s.change)}`
    ];
  }

  function hover(event) {
    // d3.pointer gives the pointer in the svg's own coordinates, so the scales work in reverse
    const [px, py] = d3.pointer(event, svg.node());
    const year = Math.round(x.invert(px));
    // which line is closest? read every line's height at the pointer's x and keep the nearest
    const t = Math.max(0, Math.min(6, x.invert(px) - 2019));
    const i = Math.min(5, Math.floor(t));
    const f = t - i;
    let nearest = null;
    let distance = Infinity;
    for (const s of series) {
      if (!included(s)) continue;
      const score = s.scores[i] + (s.scores[i + 1] - s.scores[i]) * f;
      const gap = Math.abs(y(score) - py);
      if (gap < distance) { distance = gap; nearest = s; }
    }
    // only a hover within 28 units of a line (about 18 screen pixels on a laptop)
    if (distance > 28) return leave();
    paintHover(nearest);
    crosshair.attr("x1", x(year)).attr("x2", x(year)).attr("visibility", "visible");
    marker.attr("cx", x(year)).attr("cy", y(nearest.scores[year - 2019]))
      .attr("fill", highlighted(nearest) ? colors.focus : colors.muted)
      .attr("visibility", "visible");
    showTooltip(event, nearest.country, tip(nearest, year));
  }

  function leave() {
    crosshair.attr("visibility", "hidden");
    marker.attr("visibility", "hidden");
    hideTooltip();
    paintHover(null);
  }

  // how one line should look right now, from the state
  const strokeOf = s => highlighted(s) ? colors.focus
    : s === state.hover ? colors.muted
    : state.continent !== "All" && included(s) ? colors.axis
    : colors.context;
  const widthOf = s => highlighted(s) ? (s === state.hover ? 4 : 3) : s === state.hover ? 2.5 : 1.5;
  const opacityOf = s => included(s) ? 1 : faded;

  // hovering happens dozens of times a minute, so it repaints only the two lines that changed.
  // that also leaves a running toggle or filter animation alone on the other lines
  function paintHover(next) {
    const previous = state.hover;
    if (previous === next) return;
    state.hover = next;
    for (const s of [previous, next]) {
      if (!s) continue;
      d3.select(nodeOf.get(s)).interrupt()
        .attr("stroke", strokeOf(s)).attr("stroke-width", widthOf(s)).attr("opacity", opacityOf(s));
    }
    // highlighted lines draw on top of the grey ones, and the hovered line on top of everything
    if (previous) paths.filter(highlighted).raise();
    if (next) d3.select(nodeOf.get(next)).raise();
  }

  // paint sets every line, dot and label from the state. the toggle and the filter animate it
  // with a d3 transition
  function paint(animate) {
    const t = animate ? svg.transition().duration(motion.duration).ease(motion.ease) : null;
    if (!animate) { paths.interrupt(); dots.interrupt(); }

    (animate ? paths.transition(t) : paths)
      .attr("stroke", strokeOf)
      .attr("stroke-width", widthOf)
      .attr("opacity", opacityOf);

    paths.filter(highlighted).raise();
    if (state.hover) paths.filter(s => s === state.hover).raise();

    (animate ? dots.transition(t) : dots)
      .attr("r", d => highlighted(d.s) ? 5 : 3)
      .attr("opacity", d => highlighted(d.s) ? (included(d.s) ? 1 : faded) : 0);

    // the outgoing labels slide up and fade, the incoming ones slide in from below
    for (const [view, group] of Object.entries(labelSets)) {
      const on = view === state.view;
      (animate ? group.transition(t) : group)
        .attr("opacity", on ? 1 : 0)
        .attr("transform", on ? "translate(0,0)" : `translate(0,${view === "risers" ? -10 : 10})`);
      group.attr("pointer-events", on ? null : "none");
      // labels and their leader lines fade on the same clock as the lines they name
      const named = group.selectAll(".label, line");
      (animate ? named.transition(t) : named).attr("opacity", d => included(d.s) ? 1 : faded * 2);
      group.selectAll(".label").attr("tabindex", on ? 0 : -1);
    }
  }

  paint(false);

  return {
    view(next) {
      state.view = next;
      state.hover = null;
      hideTooltip();
      crosshair.attr("visibility", "hidden");
      marker.attr("visibility", "hidden");
      paint(true);
    },
    filter(continent) {
      state.continent = continent;
      paint(true);
      return series.filter(included).length;
    }
  };
}
