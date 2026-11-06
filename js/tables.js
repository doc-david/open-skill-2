// a data table for one chart: the same numbers as the marks, in a form a screen reader can walk
// and anyone can read exactly. it's the same d3 idea as the charts, one data join nested in another:
// the outer join makes one <tr> per country, the inner join makes one cell per column.
//   columns: [{ label, value: row => text, header: true if it names the row, numeric: true to right-align }]
function dataTable(panel, columns, rows) {
  const table = d3.select(`${panel} .data-table table`);

  table.append("thead").append("tr")
    .selectAll("th").data(columns).join("th")
    .attr("scope", "col")
    .attr("class", c => c.numeric ? "num" : null)
    .text(c => c.label);

  const row = table.append("tbody")
    .selectAll("tr").data(rows, d => d.country).join("tr");

  row.selectAll("th, td")
    .data(d => columns.map(column => ({ column, text: column.value(d) })))
    .join(enter => enter.append(cell => document.createElement(cell.column.header ? "th" : "td")))
    .attr("scope", cell => cell.column.header ? "row" : null)
    .attr("class", cell => cell.column.numeric ? "num" : null)
    .text(cell => cell.text);

  return row;
}
