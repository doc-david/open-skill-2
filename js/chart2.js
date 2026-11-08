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
  svg.append("g").attr("aria-hidden", "true").selectAll("line").data(lines.y_axis.ticks).join("line")
    .attr("class", d => d === 0 ? "axisline" : "gridline")
    .attr("x1", 176).attr("x2", 1448)
    .attr("y1", d => y(d)).attr("y2", d => y(d));

  // tick labels sit right-aligned in a box from x 80 to 160, centered on each gridline
  svg.append("g").attr("aria-hidden", "true").selectAll("text").data(lines.y_axis.ticks).join("text")
    .attr("class", "t-footnote muted")
    .attr("x", 160).attr("y", d => y(d))
    .attr("text-anchor", "end").attr("dominant-baseline", "central")
    .text(d => d);

  svg.append("g").attr("aria-hidden", "true").selectAll("text").data(lines.years).join("text")
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
    .attr("pathLength", 1) // lets the entrance draw any line with the same dash, whatever its length
    .attr("d", s => line(s.scores));
  const nodeOf = new Map();
  paths.each(function (s) { nodeOf.set(s, this); });

  // waypoints: a dot at every survey year for the ten countries the toggle can highlight
  const waypoints = series.filter(s => risers.has(s.country) || decliners.has(s.country))
    .flatMap(s => lines.years.map((year, i) => ({ s, year, score: s.scores[i] })));
  const dots = svg.append("g").attr("aria-hidden", "true")
    .selectAll("circle").data(waypoints).join("circle")
    .attr("cx", d => x(d.year)).attr("cy", d => y(d.score))
    .attr("fill", colors.focus).attr("stroke", colors.paper).attr("stroke-width", 3)
    .style("paint-order", "stroke")
    .style("transform-box", "fill-box").style("transform-origin", "center");

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
      .attr("role", "img")
      .attr("aria-label", d => `${d.s.country}: 2019 ${formatScore(d.s.scores[0])}, 2025 ${formatScore(d.s.scores[6])}, change ${formatChange(d.s.change)}`);
    // an invisible box behind each label, so the gap between its words still counts as hovering it.
    // it's sized to the text when the chart first shows, since hidden text can't be measured
    label.append("rect").attr("class", "hit")
      .attr("x", 1468).attr("y", d => d.y - 16).attr("height", 32).attr("width", 0)
      .attr("fill", "transparent");
    const text = label.append("text").attr("class", "t-footnote")
      .attr("x", 1472).attr("y", d => d.y).attr("dominant-baseline", "central");
    text.append("tspan").attr("class", "strong ink").text(d => d.s.country);
    text.append("tspan").attr("class", "muted").attr("dx", 12).text(d => formatChange(d.s.change));
    // keyboard: tab to a label to light up its line, with the same tooltip as hovering
    label.on("focus", function (event, d) {
      if (focusedByMouse(this)) return;
      crosshair.attr("visibility", "hidden");
      marker.attr("visibility", "hidden");
      paintHover(d.s);
      showTooltipAt(this, d.s.country, tip(d.s, 2025));
    }).on("blur", () => {
      if (focusTooltipOpen()) leave();
    });
    // hovering a label does what hovering its line does (david, nov 7): the line lights up, the
    // crosshair and marker sit on 2025, where the label is, and the tooltip follows the cursor.
    // a label the continent filter has faded out stays quiet, like its line
    label.on("pointerenter", function (event, d) {
      if (!included(d.s)) return;
      crosshair.attr("x1", x(2025)).attr("x2", x(2025)).attr("visibility", "visible");
      marker.attr("cx", x(2025)).attr("cy", y(d.s.scores[6])).attr("fill", colors.focus).attr("visibility", "visible");
      paintHover(d.s);
      showTooltip(event, d.s.country, tip(d.s, 2025));
    }).on("pointermove", function (event, d) {
      if (included(d.s)) moveTooltip(event);
    }).on("pointerleave", () => { leave(); returnToFocus(svg.node()); });
    labelSets[view] = group;
  }

  // an invisible rectangle over the plot catches the pointer, so nobody has to land on a 1.5px line
  svg.append("rect")
    .attr("x", 176).attr("y", 290).attr("width", 1272).attr("height", 620)
    .attr("fill", "transparent")
    .on("pointermove", hover)
    .on("pointerleave", () => { leave(); returnToFocus(svg.node()); });

  // the table lists every country on the chart, biggest rise first, so all 133 lines have a
  // way in that doesn't need a pointer. the five the toggle highlights are marked in paint()
  const tableRows = dataTable("#chart2", [
    { label: "Country", value: s => s.country, header: true },
    ...lines.years.map((year, i) => ({ label: year, value: s => formatScore(s.scores[i]), numeric: true })),
    { label: "Change", value: s => formatChange(s.change), numeric: true }
  ], [...series].sort((a, b) => d3.descending(a.change, b.change)));

  // the tooltip, set out like a small table (david, nov 7: easier to read): the change first, since
  // it's what this chart is about, then the scores in time order, with the year you're on marked
  function tip(s, year) {
    const years = [...new Set([2019, year, 2025])].sort();
    return [
      { label: "Change since 2019", value: formatChange(s.change) },
      ...years.map(y => ({ label: String(y), value: formatScore(s.scores[y - 2019]), current: y === year }))
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
    tableRows.classed("highlighted", highlighted).attr("aria-current", s => highlighted(s) ? "true" : null);

    (animate ? dots.transition(t) : dots)
      // 10 units across at the ends of a highlighted line, 7 between
      .attr("r", d => !highlighted(d.s) ? 2.5 : d.year === 2019 || d.year === 2025 ? 5 : 3.5)
      .attr("opacity", d => highlighted(d.s) ? (included(d.s) ? 1 : faded) : 0);

    // the outgoing labels slide up and fade, the incoming ones slide in from below
    for (const [view, group] of Object.entries(labelSets)) {
      const on = view === state.view;
      // the outgoing set is hidden from screen readers now, and from everything once it has faded.
      // an interrupted fade never reaches "end", but then the next paint decides again
      group.attr("aria-hidden", on ? null : "true");
      if (on) group.attr("visibility", null);
      const fade = (animate ? group.transition(t) : group)
        .attr("opacity", on ? 1 : 0)
        .attr("transform", on ? "translate(0,0)" : `translate(0,${view === "risers" ? -10 : 10})`);
      if (!on && animate) fade.on("end", () => { if (state.view !== view) group.attr("visibility", "hidden"); });
      if (!on && !animate) group.attr("visibility", "hidden");
      group.attr("pointer-events", on ? null : "none");
      // labels and their leader lines fade on the same clock as the lines they name
      const named = group.selectAll(".label, line");
      (animate ? named.transition(t) : named).attr("opacity", d => included(d.s) ? 1 : faded * 2);
      // only labels you can read are tab stops, the same rule as the rows on charts 1 and 3
      group.selectAll(".label")
        .attr("tabindex", d => on && included(d.s) ? 0 : -1)
        .attr("aria-hidden", d => included(d.s) ? null : "true");
    }
  }

  paint(false);

  return {
    // the five highlighted lines draw themselves from 2019 to 2025, then their waypoint dots pop in
    // from left to right and the end labels settle in, top to bottom. the 128 grey lines simply arrive
    // with the screen: fading each on its own made every frame restyle them all
    enter() {
      svg.selectAll(".label").each(function () {
        d3.select(this).select(".hit").attr("width", this.querySelector("text").getComputedTextLength() + 8);
      });
      enter(paths.filter(highlighted), [{ strokeDasharray: "1 1", strokeDashoffset: 1 }, { strokeDasharray: "1 1", strokeDashoffset: 0 }],
        () => ({ duration: 750, easing: easing.inOut, delay: 150 }));
      enter(dots.filter(d => highlighted(d.s)), { scale: 0.2, opacity: 0 }, d => ({ ...easing.bouncy, delay: 760 + 45 * lines.years.indexOf(d.year) }));
      const current = labelSets[state.view];
      enter(current.selectAll(".label"), { opacity: 0, translate: "-12px 0" }, (d, i) => ({ ...easing.bouncy, delay: 900 + 50 * i }));
      enter(current.selectAll("line"), { opacity: 0 }, () => ({ duration: 300, easing: easing.out, delay: 900 }));
    },
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
      if (state.hover && !included(state.hover)) leave();
      paint(true);
      tableRows.attr("hidden", s => included(s) ? null : "");
      return series.filter(included).length;
    },
    clear: leave
  };
}
