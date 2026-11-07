// main: load the data, prove it's open skill 1's verified data, draw the charts, wire the controls.
// ai use: the code on this site was written with claude (anthropic), directed by david doctor,
// who chose every chart and interaction (course rule: say where ai was used).

// the git site fetches the json files; the single-file preview carries them inline
function load(name) {
  const inline = document.getElementById(`data-${name}`);
  return inline ? Promise.resolve(JSON.parse(inline.textContent)) : d3.json(`data/${name}.json`);
}

// fingerprints from the open skill 1 prd (section 3.2): counts, and sums of the values in
// thousandths. change one number in chart-data.json and a sum changes, so the page won't draw.
const verified = "20 1480 106841 -4502 123 4895677 189973 140166 6 128 41959 33040 8919";

function fingerprint(data) {
  const milli = v => Math.round(v * 1000);
  const c1 = [...data.chart1_ranked_bar.top10, ...data.chart1_ranked_bar.bottom10];
  const c2 = data.chart2_lines;
  const c3 = data.chart3_stacked.rows;
  return [
    c1.length, d3.sum(c1, d => d.rank), d3.sum(c1, d => milli(d.score)), d3.sum(c1, d => milli(d.change_since_2019)),
    c2.context_series.length, d3.sum(c2.context_series.flatMap(d => d.scores), milli),
    d3.sum(c2.risers.flatMap(d => d.scores), milli), d3.sum(c2.fallers.flatMap(d => d.scores), milli),
    c3.length, d3.sum(c3, d => d.rank), d3.sum(c3, d => milli(d.score)),
    d3.sum(c3.flatMap(d => Object.values(d.factors)), milli), d3.sum(c3, d => milli(d.unexplained))
  ].join(" ");
}

Promise.all([load("chart-data"), load("continents")]).then(([data, continents]) => {
  if (fingerprint(data) !== verified) {
    d3.select(".hud").remove();
    d3.select(".views").html("").append("p").attr("class", "error")
      .text("This chart data doesn’t match Open Skill 1’s verified numbers, so the charts aren’t drawn.");
    return;
  }

  // the map's kicker counts chart 2's countries, so the typed copy holds no number
  const lines = data.chart2_lines;
  d3.select("#country-count").text(lines.context_series.length + lines.risers.length + lines.fallers.length);

  const charts = {
    chart1: chart1(data, continents),
    chart2: chart2(data, continents),
    chart3: chart3(data, continents)
  };

  // one continent filter drives all three charts: the linked-views idea from class
  const chips = d3.selectAll("#continent button");
  chips.on("click", function () {
    const continent = this.dataset.continent;
    chips.attr("aria-pressed", function () { return String(this.dataset.continent === continent); });
    for (const [id, chart] of Object.entries(charts)) {
      const shown = chart.filter(continent);
      // role="status" announces the text when it changes, so it's only set when there's something to say
      d3.select(`#${id} .empty`)
        .classed("on", !shown)
        .text(shown ? "" : `No countries from ${continent} on this chart.`);
    }
  });

  // chart 2's switch between the biggest risers and the biggest decliners
  const toggle = d3.select("#view");
  toggle.selectAll("button").on("click", function () {
    const view = this.dataset.view;
    toggle.attr("data-view", view);
    toggle.selectAll("button").attr("aria-pressed", function () { return String(this.dataset.view === view); });
    charts.chart2.view(view);
  });

  // esc always dismisses a tooltip and its emphasis. focus stays where it is
  function clearMarks() {
    hideTooltip();
    Object.values(charts).forEach(chart => chart.clear());
  }
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") clearMarks();
  });

  // leaving a plate takes its tooltip and emphasis with it
  window.addEventListener("hashchange", clearMarks);
});
