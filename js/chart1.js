// chart 1: the happiest and unhappiest countries of 2025.
// same geometry as the figma frame (open skill 1 prd, section 7, f1): the viewbox is the
// slide's chart region, so x 320 here is x 320 on the figma frame.
function chart1(data, continents) {
  const bars = data.chart1_ranked_bar;
  const svg = d3.select("#chart1 svg").attr("viewBox", "80 200 1760 760");

  // as built in figma: the plot starts at x 320 and one point of score is 128px wide
  const x = d3.scaleLinear().domain([0, 10]).range([320, 1600]);
  const ticks = [0, 2, 4, 6, 8, 10];

  // rows: the top 10 start at y 238 and the bottom 10 at y 616, 33px apart, with a gap between
  const rows = [
    ...bars.top10.map((d, i) => ({ ...d, top: 238 + 33 * i })),
    ...bars.bottom10.map((d, i) => ({ ...d, top: 616 + 33 * i }))
  ].map(d => ({ ...d, continent: continents[d.country] }));

  svg.append("g").selectAll("line").data(ticks).join("line")
    .attr("class", d => d === 0 ? "axisline" : "gridline")
    .attr("x1", d => x(d)).attr("x2", d => x(d))
    .attr("y1", 238).attr("y2", 946);

  svg.append("g").selectAll("text").data(ticks).join("text")
    .attr("class", "t-footnote muted")
    .attr("x", d => x(d)).attr("y", 215)
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .text(d => d);

  svg.append("text").attr("class", "t-footnote muted")
    .attr("x", 152).attr("y", 215).attr("dominant-baseline", "central")
    .text("Score (0–10)");

  // the hidden middle of the ranking gets named instead of silently skipped
  svg.append("text").attr("class", "t-footnote muted halo")
    .attr("x", x(5)).attr("y", 592)
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .text(`Ranks ${bars.top10[9].rank + 1}–${bars.bottom10[0].rank - 1} not shown`);

  // one group per country: rank, name, bar and value. the data join makes 20 of them
  const row = svg.append("g").selectAll("g").data(rows).join("g")
    .attr("class", "row")
    .attr("tabindex", 0)
    .attr("aria-label", d => `${d.country}: rank ${d.rank} of ${bars.total_ranked}, score ${formatScore(d.score)}, change since 2019 ${formatChange(d.change_since_2019)}`);

  row.append("text").attr("class", "t-footnote muted")
    .attr("x", 136).attr("y", d => d.top + 15)
    .attr("text-anchor", "end").attr("dominant-baseline", "central")
    .text(d => d.rank);

  row.append("text").attr("class", "t-footnote ink")
    .attr("x", 152).attr("y", d => d.top + 15)
    .attr("dominant-baseline", "central")
    .text(d => d.country);

  // bar length = score x 128px, starting from zero (honest marks)
  row.append("path").attr("class", "bar")
    .attr("fill", colors.focus)
    .attr("d", d => barPath(x(0), d.top + 4, x(d.score) - x(0), 22, 4));

  row.append("text").attr("class", "value t-footnote ink halo")
    .attr("x", d => x(d.score) + 12).attr("y", d => d.top + 15)
    .attr("dominant-baseline", "central")
    .text(d => formatScore(d.score));

  const tip = d => [
    `Rank ${d.rank} of ${bars.total_ranked} · score ${formatScore(d.score)}`,
    `Region: ${d.region}`,
    `Change since 2019: ${d.change_since_2019 === null ? "n/a" : formatChange(d.change_since_2019)}`
  ];

  // the hovered bar stays solid and the rest step back. in figma the hover tint was invisible on navy
  function activate(active) {
    svg.classed("hovering", active !== null);
    row.selectAll(".bar, .value").classed("active", d => d === active);
  }

  // the bar itself is the hover target (david's call in open skill 1), not the whole row
  row.select(".bar")
    .on("pointerenter", (event, d) => { activate(d); showTooltip(event, d.country, tip(d)); })
    .on("pointermove", moveTooltip)
    .on("pointerleave", () => { activate(null); hideTooltip(); });

  row.on("focus", function (event, d) {
    activate(d);
    showTooltipAt(this.querySelector(".bar"), d.country, tip(d));
  }).on("blur", () => { activate(null); hideTooltip(); });

  return {
    filter(continent) {
      const included = d => continent === "All" || d.continent === continent;
      row.transition().duration(motion.duration).ease(motion.ease)
        .attr("opacity", d => included(d) ? 1 : faded);
      row.attr("tabindex", d => included(d) ? 0 : -1);
      return rows.filter(included).length;
    }
  };
}
