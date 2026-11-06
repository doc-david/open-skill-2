// one tooltip for the whole page. in figma a tooltip was a fixed box baked into a hover
// variant, so it couldn't follow the cursor and collided at the ends of chart 2's lines.
// here it's a single html box that follows the pointer and flips to stay on screen.
const tooltip = d3.select("body").append("div").attr("class", "tooltip").attr("aria-hidden", "true");
const tooltipTitle = tooltip.append("div").attr("class", "tooltip-title");
const tooltipLines = tooltip.append("div").attr("class", "tooltip-lines");

// .text() sets textContent, so a country name can never be read as html
function fillTooltip(title, lines) {
  tooltipTitle.text(title);
  tooltipLines.selectAll("div").data(lines).join("div").text(d => d);
}

// show the tooltip next to the pointer
function showTooltip(event, title, lines) {
  fillTooltip(title, lines);
  tooltip.classed("visible", true);
  placeTooltip(event.clientX, event.clientY);
}

function moveTooltip(event) {
  placeTooltip(event.clientX, event.clientY);
}

// keyboard focus has no pointer, so the tooltip sits beside the focused mark instead
function showTooltipAt(element, title, lines) {
  fillTooltip(title, lines);
  tooltip.classed("visible", true);
  const box = element.getBoundingClientRect();
  placeTooltip(box.right, box.top + box.height / 2);
}

function hideTooltip() {
  tooltip.classed("visible", false);
}

// 16px below and right of the pointer, flipped left or up when it would leave the window
function placeTooltip(x, y) {
  const box = tooltip.node().getBoundingClientRect();
  const gap = 16;
  let left = x + gap;
  let top = y + gap;
  if (left + box.width > window.innerWidth - 8) left = x - gap - box.width;
  if (top + box.height > window.innerHeight - 8) top = y - gap - box.height;
  tooltip.style("transform", `translate(${Math.max(8, left)}px, ${Math.max(8, top)}px)`);
}
