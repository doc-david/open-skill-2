// the design tokens live in css/tokens.css. d3 needs real color values to animate from one
// color to another, so we read the css variables once here instead of retyping hex codes.
const css = getComputedStyle(document.documentElement);
const token = name => css.getPropertyValue(`--${name}`).trim();

// windows high contrast mode replaces the page's colors, so a mark's accent has to be a system
// color too. d3 needs a real value to animate, so a throwaway element reports what it resolves to
const forcedColors = window.matchMedia("(forced-colors: active)").matches;
function systemColor(name) {
  const probe = document.body.appendChild(document.createElement("span"));
  probe.style.color = name;
  const value = getComputedStyle(probe).color;
  probe.remove();
  return value;
}

const colors = {
  ink: token("color-text-primary"),
  muted: token("color-text-chart-muted"),
  paper: token("color-bg-primary"),
  grid: token("color-line-grid"),
  axis: token("color-line-axis"),
  context: token("color-data-context"),
  focus: forcedColors ? systemColor("Highlight") : token("color-data-focus")
};

// one motion setting for every chart change: d3's quartic ease-in-out is the same curve as the
// animate skill's strong ease-in-out (cubic-bezier(0.77, 0, 0.175, 1)), 300ms keeps it snappy.
// people who ask their system for less motion get instant changes instead, even if they ask
// while the page is open.
const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const motion = {
  get duration() { return reduceMotionQuery.matches ? 0 : 300; },
  ease: d3.easePolyInOut.exponent(4)
};

// entrances: a chart's marks arrive each time its screen opens. the springs come from site.css, so
// css and the charts share one set of curves. bars, segments and lines grow on the strong ease-out
// and never overshoot, because a bar that bounces past its value shows a wrong number for a moment.
// the bounce is for what doesn't encode a value: dots popping in and labels settling.
const rootStyle = getComputedStyle(document.documentElement);
const cssValue = name => rootStyle.getPropertyValue(name).trim();
const easing = {
  out: cssValue("--ease-out"),
  inOut: cssValue("--ease-in-out"),
  bouncy: { easing: cssValue("--spring-bouncy"), duration: parseFloat(cssValue("--spring-bouncy-time")) },
  quick: { easing: cssValue("--spring-quick"), duration: parseFloat(cssValue("--spring-quick-time")) }
};

// plays an entrance on every node of a selection with the web animations api. from is either the
// start state (the node animates from it to wherever it already is) or a full list of keyframes.
// timing(d, i) gives each node its delay, duration and easing. whatever is still running from the
// last entrance stops first. people who ask for less motion get the marks in place at once.
function enter(selection, from, timing) {
  if (reduceMotionQuery.matches) return;
  selection.each(function (d, i) {
    this.getAnimations().forEach(a => a.cancel());
    this.animate(Array.isArray(from) ? from : [{ ...from, offset: 0 }], { fill: "backwards", ...timing(d, i) });
  });
}

// faded = how far a mark steps back when the continent filter leaves it out
const faded = 0.12;

// bars round only their value end (4px), like the figma Mark/Bar component; the zero end stays square
function barPath(x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  return `M${x},${y}h${width - r}a${r},${r} 0 0 1 ${r},${r}v${height - 2 * r}a${r},${r} 0 0 1 ${-r},${r}h${-(width - r)}z`;
}
