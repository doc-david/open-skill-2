// the figma tokens live in css/tokens.css. d3 needs real color values to animate from one
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
// people who ask their system for less motion get instant changes instead.
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const motion = {
  duration: reduceMotion ? 0 : 300,
  ease: d3.easePolyInOut.exponent(4)
};

// faded = how far a mark steps back when the continent filter leaves it out
const faded = 0.12;

// bars round only their value end (4px), like the figma Mark/Bar component; the zero end stays square
function barPath(x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  return `M${x},${y}h${width - r}a${r},${r} 0 0 1 ${r},${r}v${height - 2 * r}a${r},${r} 0 0 1 ${-r},${r}h${-(width - r)}z`;
}
