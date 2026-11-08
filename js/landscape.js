// landscape: the map's moving background and its pause toggle. views.js starts and stops it as the
// map shows and hides (updateContours), and it asks views.js which view is showing (viewOf).

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
const step = 0.06;          // height between contour lines, with no top or bottom: every height gets its line
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
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) heights[j * cols + i] = across[i] * down[j] + 0.5 * i / (cols - 1) + 0.3 * j / (rows - 1);
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
  // one path for every line: the heights have no top or bottom, so each step of height has a line,
  // and lowering them all by one step brings back the same set, so the loop has no seam
  const path = new Path2D();
  const crossings = [];
  for (let j = 0; j < rows - 1; j++) {
    for (let i = 0; i < cols - 1; i++) {
      const a = heights[j * cols + i], b = heights[j * cols + i + 1];
      const c = heights[(j + 1) * cols + i + 1], d = heights[(j + 1) * cols + i];
      const lo = Math.min(a, b, c, d), hi = Math.max(a, b, c, d);
      for (let k = Math.ceil(lo / step + flow); k <= hi / step + flow; k++) {
        const t = (k - flow) * step;
        crossings.length = 0;
        if ((a < t) !== (b < t)) crossings.push(i + (t - a) / (b - a), j);
        if ((b < t) !== (c < t)) crossings.push(i + 1, j + (t - b) / (c - b));
        if ((d < t) !== (c < t)) crossings.push(i + (t - d) / (c - d), j + 1);
        if ((a < t) !== (d < t)) crossings.push(i, j + (t - a) / (d - a));
        for (let n = 0; n + 3 < crossings.length; n += 4) {
          path.moveTo(crossings[n], crossings[n + 1]);
          path.lineTo(crossings[n + 2], crossings[n + 3]);
        }
      }
    }
  }
  return path;
}

function drawContours(time) {
  const w = contours.clientWidth, h = contours.clientHeight;
  if (!w || !h) return;
  const dpr = window.devicePixelRatio || 1;
  if (contours.width !== Math.round(w * dpr)) contours.width = Math.round(w * dpr);
  if (contours.height !== Math.round(h * dpr)) contours.height = Math.round(h * dpr);
  const phase = 2 * Math.PI * time / driftPeriod;
  fillHeights(phase);
  // flow runs 0 to 1 over each period, lowering every line one step, so each moves out and down to
  // the next one's place
  const flow = (time / ringPeriod) % 1;
  const lines = traceLevels(flow);
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
  ctx.stroke(lines);
  contours.frames++;
}

// the landscape keeps its own clock, which only runs while it moves, so after a pause, a chart or a
// hidden tab it carries on from exactly where it stopped
let contourFrame = null;
let contourClock = ringPeriod / 2;
let lastFrame = null;
function flowContours(time) {
  if (lastFrame !== null) contourClock += Math.min(time - lastFrame, 100);
  lastFrame = time;
  drawContours(contourClock);
  contourFrame = requestAnimationFrame(flowContours);
}

// the map's pause button (david, nov 7). a paused map stays paused when you come back, in this browser
const motionToggle = document.getElementById("motion-toggle");
let contoursPaused = false;
try { contoursPaused = localStorage.getItem("map-motion") === "paused"; } catch (error) { /* storage blocked: start moving */ }

// a toggle: its name stays "Pause motion" and its pressed state says whether the motion is paused;
// the icon shows what a press will do next
function labelMotionToggle() {
  motionToggle.setAttribute("aria-pressed", String(contoursPaused));
  motionToggle.title = contoursPaused ? "Play motion" : "Pause motion";
  motionToggle.querySelector(".pause-icon").hidden = contoursPaused;
  motionToggle.querySelector(".play-icon").hidden = !contoursPaused;
}
motionToggle.addEventListener("click", () => {
  contoursPaused = !contoursPaused;
  try { localStorage.setItem("map-motion", contoursPaused ? "paused" : "playing"); } catch (error) { /* not remembered */ }
  labelMotionToggle();
  updateContours();
});
labelMotionToggle();

// starts or stops the flow to match what's on screen; a still map is drawn once, where it stopped
function updateContours() {
  const onMap = !viewOf(0).hidden;
  const moving = onMap && !document.hidden && !reduceMotionQuery.matches && !contoursPaused;
  if (moving && contourFrame === null) {
    lastFrame = null;
    drawContours(contourClock);
    contourFrame = requestAnimationFrame(flowContours);
  }
  if (!moving && contourFrame !== null) {
    cancelAnimationFrame(contourFrame);
    contourFrame = null;
  }
  if (onMap && !moving) drawContours(contourClock);
}
document.addEventListener("visibilitychange", updateContours);
reduceMotionQuery.addEventListener("change", updateContours);
window.addEventListener("resize", () => { if (contourFrame === null) updateContours(); });
