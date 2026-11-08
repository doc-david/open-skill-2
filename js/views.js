// the screens: one view shows at a time, and the address bar's hash says which one.
// #map (the default), #chart-1, #chart-2 or #chart-3. because the view lives in the address,
// the back button and a reload keep your place, and each chart has a link you can share.
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
  hudCharts.hidden = route === 0;
  hudCount.textContent = `Chart ${route} of 3`;
  hudDots.forEach((dot, i) => {
    if (i + 1 === route) dot.setAttribute("aria-current", "page");
    else dot.removeAttribute("aria-current");
  });
  views.scrollTop = 0;
}

// the map's contour lines: four clusters of wobbly rings, generated once. decoration, no data
function drawContours() {
  const clusters = [[1080, 170, 26, 10], [190, 640, 30, 9], [640, 420, 18, 7], [1180, 720, 22, 6]];
  const rings = [];
  clusters.forEach(([cx, cy, base, n], c) => {
    const p = [c * 1.7 + 0.4, c * 2.3 + 1.1, c * 0.9 + 2.0];
    for (let k = 0; k < n; k++) {
      const r = base + k * 28;
      let d = "";
      for (let i = 0; i < 72; i++) {
        const a = (i / 72) * 2 * Math.PI;
        const rr = r * (1 + 0.12 * Math.sin(3 * a + p[0]) + 0.07 * Math.sin(5 * a + p[1] + k * 0.2) + 0.05 * Math.sin(2 * a + p[2]));
        d += (i ? "L" : "M") + Math.round(cx + rr * Math.cos(a) * 1.45) + "," + Math.round(cy + rr * Math.sin(a));
      }
      rings.push(d + "Z");
    }
  });
  d3.select(".contours").selectAll("path").data(rings).join("path").attr("d", d => d);
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

drawContours();
renameOldHash();
let route = routeOf(location.hash);
showView(route);
// the stops rise in once, only when the map is the first thing you see
if (route === 0) document.querySelectorAll(".stop").forEach(stop => stop.classList.add("intro"));

// a new view is a new page to a keyboard or a screen reader, so focus moves to its heading
window.addEventListener("hashchange", () => {
  renameOldHash();
  const next = routeOf(location.hash);
  if (!viewOf(next)) return; // the page refused its data, so there are no views left to show
  if (next !== route) animateView(route, next);
  route = next;
  showView(route);
  viewOf(route).querySelector("h1, h2").focus();
});
