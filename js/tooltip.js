// one tooltip for the whole page. in figma a tooltip was a fixed box baked into a hover
// variant, so it couldn't follow the cursor and collided at the ends of chart 2's lines.
// here it's a single html box that follows the pointer and flips to stay on screen.
const tooltip = d3.select("body").append("div").attr("class", "tooltip").attr("aria-hidden", "true");
const tooltipTitle = tooltip.append("div").attr("class", "tooltip-title");
const tooltipLines = tooltip.append("div").attr("class", "tooltip-lines");

// the mark a keyboard-opened tooltip belongs to. null when the pointer owns the tooltip
let tooltipAnchor = null;

// .text() sets textContent, so a country name can never be read as html
function fillTooltip(title, lines) {
  tooltipTitle.text(title);
  // a line is plain text, or a row of label and value, set out like a small table
  const rows = lines.some(d => typeof d === "object");
  tooltipLines.classed("rows", rows);
  tooltipLines.selectAll("div").data(lines).join("div")
    .attr("class", d => d.current ? "current" : null)
    .each(function (d) {
      const line = d3.select(this).text(rows ? null : d);
      if (rows) {
        line.append("span").text(d.label);
        line.append("span").attr("class", "value").text(d.value);
      }
    });
}

// show the tooltip next to the pointer
function showTooltip(event, title, lines) {
  tooltipAnchor = null;
  fillTooltip(title, lines);
  tooltip.classed("visible", true);
  placeTooltip(event.clientX, event.clientY);
}

function moveTooltip(event) {
  placeTooltip(event.clientX, event.clientY);
}

// keyboard focus has no pointer, so the tooltip sits beside the focused mark instead
function showTooltipAt(element, title, lines) {
  // keyboard focus finishes whatever is still arriving on its screen, so the tooltip sits beside the
  // mark where it ends up, not where it is halfway through growing
  element.closest(".view")?.getAnimations({ subtree: true })
    .filter(a => a.effect.getTiming().iterations !== Infinity).forEach(a => a.finish());
  tooltipAnchor = element;
  fillTooltip(title, lines);
  placeAtAnchor();
}

function hideTooltip() {
  tooltipAnchor = null;
  tooltip.classed("visible", false);
}

function focusTooltipOpen() {
  return tooltipAnchor !== null;
}

// beside the anchor, using only the part of it that's visible inside its chart.
// the tooltip stays with its mark while the view scrolls, and steps away while the mark is
// scrolled out of the view (behind the hud at the top, or past the window at the bottom)
function placeAtAnchor() {
  const box = tooltipAnchor.getBoundingClientRect();
  const chart = tooltipAnchor.closest(".chart").getBoundingClientRect();
  const view = tooltipAnchor.closest(".views").getBoundingClientRect();
  tooltip.classed("visible", box.bottom > Math.max(0, view.top) && box.top < Math.min(window.innerHeight, view.bottom));
  placeTooltip(Math.min(box.right, chart.right), box.top + box.height / 2);
}

let tooltipQueued = false;
window.addEventListener("scroll", () => {
  if (tooltipQueued || !tooltipAnchor) return;
  tooltipQueued = true;
  requestAnimationFrame(() => {
    tooltipQueued = false;
    if (tooltipAnchor) placeAtAnchor();
  });
}, { capture: true, passive: true });

// a mouse click also moves focus to a row. that shouldn't open a tooltip that outlives the hover,
// but a keyboard or a tap should, since focus is their only way to open one
let lastPointer = "";
document.addEventListener("pointerdown", event => { lastPointer = event.pointerType; }, { capture: true, passive: true });
document.addEventListener("keydown", () => { lastPointer = ""; }, { capture: true, passive: true });

function focusedByMouse(element) {
  return lastPointer === "mouse" && !element.matches(":focus-visible");
}

// when the pointer leaves, a mark that still has keyboard focus gets its tooltip back
function returnToFocus(svgNode) {
  const focused = document.activeElement;
  if (svgNode.contains(focused) && focused.matches(":focus-visible")) d3.select(focused).dispatch("focus");
}

// 16px below and right of the pointer, flipped left or up when it would leave the window,
// and always kept fully inside it
function placeTooltip(x, y) {
  const box = tooltip.node().getBoundingClientRect();
  const gap = 16;
  const edge = 8;
  let left = x + gap;
  let top = y + gap;
  if (left + box.width > window.innerWidth - edge) left = x - gap - box.width;
  if (top + box.height > window.innerHeight - edge) top = y - gap - box.height;
  left = Math.max(edge, Math.min(left, window.innerWidth - box.width - edge));
  top = Math.max(edge, Math.min(top, window.innerHeight - box.height - edge));
  tooltip.style("transform", `translate(${left}px, ${top}px)`);
}
