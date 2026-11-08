// chart 3: what each factor adds to the score, for the top-ranked country of each continent.
// figma geometry again (open skill 1 prd, section 7, f3); the viewbox starts just above the first row
// because the legend is html above the chart, so it can wrap on small screens.
function chart3(data, continents) {
  const stack = data.chart3_stacked;
  const svg = d3.select("#chart3 svg").attr("viewBox", "80 280 1760 680");

  // as built in figma: the plot starts at x 328, 128px per point like chart 1
  const x = d3.scaleLinear().domain([0, 10]).range([328, 1608]);
  const ticks = [0, 2, 4, 6, 8, 10];

  // label (the legend's and the tooltip's) and pigment for each factor, in the stack's left-to-right order
  const factors = {
    "GDP per Capita": { label: "GDP per capita", color: token("color-factor-gdp") },
    "Social Support": { label: "Social support", color: token("color-factor-social") },
    "Life Expectancy": { label: "Life expectancy", color: token("color-factor-life") },
    "Freedom": { label: "Freedom", color: token("color-factor-freedom") },
    "Generosity": { label: "Generosity", color: token("color-factor-generosity") },
    "Corruption": { label: "Perceptions of corruption", color: token("color-factor-corruption") },
    "Unexplained": { label: "Unexplained remainder", color: token("color-factor-unexplained") }
  };

  const legend = d3.select("#chart3 .legend").selectAll("li").data(stack.factor_order).join("li");
  legend.append("span").attr("class", "swatch").style("background", d => factors[d].color);
  legend.append("span").text(d => factors[d].label);

  // each row's segments start where the previous one ended (a running total, which is what
  // d3.stack computes for many rows at once)
  const rows = stack.rows.map((d, i) => {
    const top = 296 + 100 * i;
    let start = 0;
    const segments = stack.factor_order.map((name, j) => {
      const value = name === "Unexplained" ? d.unexplained : d.factors[name];
      const segment = { name, value, start, top, country: d.country, score: d.score, last: j === stack.factor_order.length - 1 };
      start += value;
      return segment;
    });
    return { ...d, top, segments, continent: continents[d.country] };
  });

  svg.append("g").attr("aria-hidden", "true").selectAll("line").data(ticks).join("line")
    .attr("class", d => d === 0 ? "axisline" : "gridline")
    .attr("x1", d => x(d)).attr("x2", d => x(d))
    .attr("y1", 296).attr("y2", 884);

  svg.append("g").attr("aria-hidden", "true").selectAll("text").data(ticks).join("text")
    .attr("class", "t-footnote muted")
    .attr("x", d => x(d)).attr("y", 915)
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .text(d => d);

  svg.append("text").attr("class", "t-footnote muted")
    .attr("x", 152).attr("y", 915).attr("dominant-baseline", "central")
    .text("Score (0–10)");

  // opacity starts at 1 so the filter's transition has a value to start from
  const row = svg.append("g").selectAll("g").data(rows).join("g")
    .attr("class", "row")
    .attr("opacity", 1)
    .attr("tabindex", 0)
    .attr("role", "img")
    .attr("aria-label", d => `${d.country}, ${d.continent}, rank ${d.rank}, score ${formatScore(d.score)}: ` +
      d.segments.map(s => `${factors[s.name].label} ${formatScore(s.value)}`).join(", "));

  row.append("text").attr("class", "t-footnote muted")
    .attr("x", 136).attr("y", d => d.top + 36)
    .attr("text-anchor", "end").attr("dominant-baseline", "central")
    .text(d => d.rank);

  row.append("text").attr("class", "t-footnote ink")
    .attr("x", 152).attr("y", d => d.top + 23)
    .attr("dominant-baseline", "central")
    .text(d => d.country);

  row.append("text").attr("class", "t-caption muted")
    .attr("x", 152).attr("y", d => d.top + 51)
    .attr("dominant-baseline", "central")
    .text(d => d.continent);

  // a nested data join: each row's data is its 7 segments. the plate-colored stroke draws the 2px gaps
  const segments = row.selectAll(".segment").data(d => d.segments).join("path")
    .attr("class", "segment")
    .attr("fill", s => factors[s.name].color)
    .attr("stroke", colors.paper).attr("stroke-width", 2)
    .attr("d", s => barPath(x(s.start), s.top + 12, x(s.start + s.value) - x(s.start), 48, s.last ? 4 : 0));

  row.append("text").attr("class", "t-footnote strong ink halo")
    .attr("x", d => x(d.score) + 12).attr("y", d => d.top + 36)
    .attr("dominant-baseline", "central")
    .text(d => formatScore(d.score));

  function activate(node) {
    svg.classed("hovering", node !== null);
    segments.classed("active", function () { return this === node; });
  }

  segments
    .on("pointerenter", function (event, s) {
      activate(this);
      showTooltip(event, factors[s.name].label, [`${formatScore(s.value)} of ${formatScore(s.score)} points · ${s.country}`]);
    })
    .on("pointermove", moveTooltip)
    .on("pointerleave", () => { activate(null); hideTooltip(); returnToFocus(svg.node()); });

  // keyboard: a focused row shows its whole breakdown at once
  row.on("focus", function (event, d) {
    if (focusedByMouse(this)) return;
    showTooltipAt(this.querySelector(".segment:last-of-type"), `${d.country} · ${formatScore(d.score)}`,
      d.segments.map(s => `${factors[s.name].label}: ${formatScore(s.value)}`));
  }).on("blur", () => {
    if (focusTooltipOpen()) hideTooltip();
  });

  const tableRows = dataTable("#chart3", [
    { label: "Rank", value: d => d.rank, numeric: true },
    { label: "Country", value: d => d.country, header: true },
    { label: "Continent", value: d => d.continent },
    { label: "Score", value: d => formatScore(d.score), numeric: true },
    ...stack.factor_order.map((name, j) => ({ label: factors[name].label, value: d => formatScore(d.segments[j].value), numeric: true }))
  ], rows);

  return {
    filter(continent) {
      const included = d => continent === "All" || d.continent === continent;
      row.transition().duration(motion.duration).ease(motion.ease)
        .attr("opacity", d => included(d) ? 1 : faded);
      row.attr("tabindex", d => included(d) ? 0 : -1).attr("aria-hidden", d => included(d) ? null : "true");
      tableRows.attr("hidden", d => included(d) ? null : "");
      return rows.filter(included).length;
    },
    clear() { activate(null); }
  };
}
