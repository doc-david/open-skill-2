// the screens: one view shows at a time, and the address bar's hash says which one.
// #map (the default), #chart-1, #chart-2 or #chart-3. because the view lives in the address,
// the back button and a reload keep your place, and each chart has a link you can share.
const hud = document.querySelector(".hud");
const hudCharts = document.getElementById("hud-charts");
const hudCount = document.getElementById("hud-count");
const hudDots = document.querySelectorAll(".hud-dots a");
const views = document.querySelector(".views");

// "#chart-2" gives 2, and so does "#plate-2", the address it had before. anything else,
// including an unknown hash, gives 0: the map
function routeOf(hash) {
  const match = /^#(?:chart|plate)-([123])$/.exec(hash);
  return match ? Number(match[1]) : 0;
}

function viewOf(route) {
  return document.getElementById(route === 0 ? "view-map" : `chart${route}`);
}

function showView(route) {
  document.querySelectorAll(".view").forEach(view => { view.hidden = view !== viewOf(route); });
  // the map has no hud: its filter only matters on a chart (david, nov 7). it keeps its setting
  hud.hidden = route === 0;
  hudCharts.hidden = route === 0;
  hudCount.textContent = `Chart ${route} of 3`;
  hudDots.forEach((dot, i) => {
    if (i + 1 === route) dot.setAttribute("aria-current", "page");
    else dot.removeAttribute("aria-current");
  });
  views.scrollTop = 0;
  updateContours();
}

// a screen's arrival class comes off when it lands, and so does the scroll guard
views.addEventListener("animationend", event => {
  if (event.target.matches(".view") && event.animationName !== "fade-in") {
    event.target.classList.remove("view-in", "chart-from-right", "chart-from-left");
    views.classList.remove("settling");
  }
});

// the map's ground: the contour lines of a whole landscape, so they cover every part of the map
// (david, nov 7). a few broad hills drift slowly, and the lines flow outward from their peaks
// forever: a new ring keeps rising at each peak while the lowest line slides away. the lines are
// traced through a grid of heights like an elevation map (marching squares), so they never cross.
// drawn on a canvas, one fresh frame at a time, so every line stays 1.5px; animating 32 svg rings
// had made the browser repaint the window every frame, about 13 frames a second on an intel laptop.
// it only runs while the map shows, the tab is in front and motion is welcome. decoration, no data
const contours = document.querySelector(".contours");
const contourColor = getComputedStyle(contours).color;
// hills in the map's 1280 by 800 design: center x and y, width, height, and where in its drift it starts
const hills = [
  [1080, 170, 230, 1.0, 0.0], [190, 640, 260, 1.0, 1.3], [640, 420, 200, 0.75, 2.1],
  [1180, 720, 220, 0.85, 3.4], [330, 120, 240, 0.7, 4.2], [820, 760, 250, 0.65, 5.0]
];
const cell = 10;            // design units per grid cell
const cols = 1280 / cell + 1, rows = 800 / cell + 1;
const step = 0.075;         // height between contour lines
const levels = 16;
const ringPeriod = 7000;    // ms for a line to flow out to the next one's place
const driftPeriod = 80000;  // ms for the hills and the map to drift there and back
const heights = new Float64Array(cols * rows);
const across = new Float64Array(cols), down = new Float64Array(rows);
contours.frames = 0;        // frames drawn, for the checks

// the heights: each hill a soft bump that wanders slowly around its home, plus a gentle ripple so
// the lines wobble like real terrain. a bump's height splits into a row part times a column part,
// so each hill costs one pass over the grid with no exponentials inside it
function fillHeights(phase) {
  for (let i = 0; i < cols; i++) across[i] = 0.04 * Math.sin(i * cell / 97 + phase);
  for (let j = 0; j < rows; j++) down[j] = Math.cos(j * cell / 83 - phase);
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) heights[j * cols + i] = across[i] * down[j];
  for (const [hx, hy, spread, height, offset] of hills) {
    const cx = hx + 40 * Math.sin(phase + offset), cy = hy + 30 * Math.cos(phase * 0.8 + offset);
    const k = 1 / (2 * spread * spread);
    for (let i = 0; i < cols; i++) across[i] = height * Math.exp(-((i * cell - cx) ** 2) * k);
    for (let j = 0; j < rows; j++) down[j] = Math.exp(-((j * cell - cy) ** 2) * k);
    for (let j = 0; j < rows; j++) {
      const dj = down[j], row = j * cols;
      if (dj < 1e-4) continue;
      for (let i = 0; i < cols; i++) heights[row + i] += across[i] * dj;
    }
  }
}

// marching squares: for every grid cell, each line whose height falls between the cell's corners
// crosses two of its edges (four at a saddle), found by interpolating along them
function traceLevels(flow) {
  // three paths: the lowest line (fading out), every line in between, and the newest (fading in)
  const paths = [new Path2D(), new Path2D(), new Path2D()];
  const crossings = [];
  for (let j = 0; j < rows - 1; j++) {
    for (let i = 0; i < cols - 1; i++) {
      const a = heights[j * cols + i], b = heights[j * cols + i + 1];
      const c = heights[(j + 1) * cols + i + 1], d = heights[(j + 1) * cols + i];
      const lo = Math.min(a, b, c, d), hi = Math.max(a, b, c, d);
      const first = Math.max(0, Math.ceil(lo / step - 1 + flow));
      const last = Math.min(levels - 1, Math.floor(hi / step - 1 + flow));
      for (let level = first; level <= last; level++) {
        const t = (level + 1 - flow) * step;
        crossings.length = 0;
        if ((a < t) !== (b < t)) crossings.push(i + (t - a) / (b - a), j);
        if ((b < t) !== (c < t)) crossings.push(i + 1, j + (t - b) / (c - b));
        if ((d < t) !== (c < t)) crossings.push(i + (t - d) / (c - d), j + 1);
        if ((a < t) !== (d < t)) crossings.push(i, j + (t - a) / (d - a));
        const path = paths[level === 0 ? 0 : level === levels - 1 ? 2 : 1];
        for (let n = 0; n + 3 < crossings.length; n += 4) {
          path.moveTo(crossings[n], crossings[n + 1]);
          path.lineTo(crossings[n + 2], crossings[n + 3]);
        }
      }
    }
  }
  return paths;
}

function drawContours(time) {
  const w = contours.clientWidth, h = contours.clientHeight;
  if (!w || !h) return;
  const dpr = window.devicePixelRatio || 1;
  if (contours.width !== Math.round(w * dpr)) contours.width = Math.round(w * dpr);
  if (contours.height !== Math.round(h * dpr)) contours.height = Math.round(h * dpr);
  const phase = 2 * Math.PI * time / driftPeriod;
  fillHeights(phase);
  // flow runs 0 to 1 over each period, lowering every line one step, so each moves out to the next
  // one's place. the newest line at the top fades in and the lowest fades out, so the loop has no seam
  const flow = (time / ringPeriod) % 1;
  const paths = traceLevels(flow);
  const ctx = contours.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  // the design scaled to cover the window and 8% past it, so neither the drift nor the grid's own
  // edge ever shows
  const k = Math.max(w / 1280, h / 800) * 1.08;
  const drift = Math.sin(phase);
  ctx.translate(w / 2 + drift * 0.015 * w, h / 2 + drift * 0.01 * h);
  ctx.scale(k * cell, k * cell);
  ctx.translate(-640 / cell, -400 / cell);
  ctx.lineWidth = 1.5 / (k * cell);
  ctx.strokeStyle = contourColor;
  [1 - flow, 1, flow].forEach((alpha, n) => {
    ctx.globalAlpha = alpha;
    ctx.stroke(paths[n]);
  });
  contours.frames++;
}

let contourFrame = null;
function flowContours(time) {
  drawContours(time);
  contourFrame = requestAnimationFrame(flowContours);
}

// starts or stops the flow to match what's on screen; a still map is drawn once, half a flow in
function updateContours() {
  const onMap = !viewOf(0).hidden;
  const moving = onMap && !document.hidden && !reduceMotionQuery.matches;
  if (moving && contourFrame === null) contourFrame = requestAnimationFrame(flowContours);
  if (!moving && contourFrame !== null) {
    cancelAnimationFrame(contourFrame);
    contourFrame = null;
  }
  if (onMap && !moving) drawContours(ringPeriod / 2);
}
document.addEventListener("visibilitychange", updateContours);
reduceMotionQuery.addEventListener("change", updateContours);
window.addEventListener("resize", () => { if (contourFrame === null) updateContours(); });

// the title's letters each get a box of their own, so the intro can pop them one at a time. the
// heading keeps its words as its name, so a screen reader reads "World Happiness", not letters
function splitTitle() {
  const h1 = document.querySelector(".masthead h1");
  const text = h1.textContent;
  h1.setAttribute("aria-label", text);
  h1.textContent = "";
  let n = 0;
  text.split(" ").forEach((word, w) => {
    if (w) h1.append(" ");
    const box = document.createElement("span");
    box.className = "word";
    box.setAttribute("aria-hidden", "true");
    for (const ch of word) {
      const letter = document.createElement("span");
      letter.className = "letter";
      letter.style.setProperty("--letter", n++);
      letter.textContent = ch;
      box.append(letter);
    }
    h1.append(box);
  });
}

// how a view arrives. the rules are in css, inside prefers-reduced-motion: no-preference, so people
// who ask for less motion get none. a hidden element replays its animation when it shows again,
// so every motion class comes off before the next view opens.
//   chart to chart: slide in from the side you moved toward
//   map to chart, or back: grow from the stop you came from
const stopOrigin = { 1: "18% 64%", 2: "50% 64%", 3: "82% 64%" };
const motionClasses = ["view-in", "chart-from-right", "chart-from-left", "intro"];

function animateView(from, to) {
  motionClasses.forEach(name => document.querySelectorAll(`.${name}`).forEach(e => e.classList.remove(name)));
  // a screen that fits can overshoot past the edge for a moment, so the view hides its overflow until
  // it lands; one that already scrolls keeps its scrollbar, or the whole screen would jump 15px
  views.classList.toggle("settling", views.scrollHeight <= views.clientHeight + 1);
  const view = viewOf(to);
  if (from !== 0 && to !== 0) {
    view.classList.add(to > from ? "chart-from-right" : "chart-from-left");
  } else {
    view.style.transformOrigin = stopOrigin[from || to];
    view.classList.add("view-in");
  }
}

// only the view scrolls, and it can't take focus itself, so the scroll keys do nothing until focus
// is inside it. this passes them along from the hud and the bare page. arrows and space stay with
// a focused chip or link, where they already mean something
function passScrollKeys(event) {
  if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest(".views")) return;
  const bare = event.target === document.body;
  const jump = views.clientHeight * 0.9;
  const moves = { PageDown: jump, PageUp: -jump, Home: -views.scrollTop, End: views.scrollHeight };
  if (bare) Object.assign(moves, { ArrowDown: 40, ArrowUp: -40, " ": event.shiftKey ? -jump : jump });
  if (!(event.key in moves)) return;
  event.preventDefault();
  views.scrollBy(0, moves[event.key]);
}
document.addEventListener("keydown", passScrollKeys);

// an old #plate-n link swaps itself for #chart-n, without adding a step to the back button
function renameOldHash() {
  if (/^#plate-[123]$/.test(location.hash)) history.replaceState(null, "", location.hash.replace("plate", "chart"));
}

// the charts' fonts load now, while the map shows. nothing on the map uses these weights, so the
// download costs no frames, and the first chart you open doesn't wait for them or redraw when they land
if (document.fonts) {
  for (const weight of [400, 500, 600, 700]) document.fonts.load(`${weight} 16px "IBM Plex Sans Condensed"`);
}
splitTitle();
renameOldHash();
let route = routeOf(location.hash);
showView(route);
// lays a hidden view out once without showing it: off the page's flow, invisible, out of the
// accessibility tree and the tab order, and still hidden to everything that asks. the browser keeps
// what it learned about the view's text and shapes, so its first real showing is quick
function prewarm(view) {
  if (!view.hidden) return;
  view.classList.add("prewarm");
  void view.offsetHeight;
  view.classList.remove("prewarm");
}

// the map's intro plays once, only when the map is the first thing you see
if (route === 0) viewOf(0).classList.add("intro");

// a new view is a new page to a keyboard or a screen reader, so focus moves to its heading
window.addEventListener("hashchange", () => {
  renameOldHash();
  const next = routeOf(location.hash);
  if (!viewOf(next)) return; // the page refused its data, so there are no views left to show
  const from = route;
  route = next;
  showView(route);
  // after showView, so the guard measures the new screen as it will sit
  if (next !== from) animateView(from, next);
  viewOf(route).querySelector("h1, h2").focus();
});
