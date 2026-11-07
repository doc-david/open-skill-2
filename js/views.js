// the screens: one view shows at a time, and the address bar's hash says which one.
// #map (the default), #plate-1, #plate-2 or #plate-3. because the view lives in the address,
// the back button and a reload keep your place, and each plate has a link you can share.
const hudPlates = document.getElementById("hud-plates");
const hudCount = document.getElementById("hud-count");
const hudDots = document.querySelectorAll(".hud-dots a");
const views = document.querySelector(".views");

// "#plate-2" gives 2. anything else, including an unknown hash, gives 0: the map
function routeOf(hash) {
  const match = /^#plate-([123])$/.exec(hash);
  return match ? Number(match[1]) : 0;
}

function viewOf(route) {
  return document.getElementById(route === 0 ? "view-map" : `chart${route}`);
}

function showView(route) {
  document.querySelectorAll(".view").forEach(view => { view.hidden = view !== viewOf(route); });
  hudPlates.hidden = route === 0;
  hudCount.textContent = `Plate ${route} of 3`;
  hudDots.forEach((dot, i) => {
    if (i + 1 === route) dot.setAttribute("aria-current", "page");
    else dot.removeAttribute("aria-current");
  });
  views.scrollTop = 0;
  if (route === 0) stampExplored();
  else seen.add(route);
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

// a plate you've opened gets an "Explored" stamp on its stop, the first time you come back to the map.
// stamped is what's showing on the map; seen is everything opened since this page loaded
const seen = new Set();
const stamped = new Set();

function stampExplored() {
  for (const plate of seen) {
    if (stamped.has(plate)) continue;
    stamped.add(plate);
    const stop = document.querySelector(`.stop[data-plate="${plate}"]`);
    stop.querySelector(".explored").hidden = false;
    stop.querySelector(".explored").classList.add("fresh");
    stop.querySelector(".visually-hidden").hidden = false;
  }
}

// how a view arrives. the rules are in css, inside prefers-reduced-motion: no-preference, so people
// who ask for less motion get none. a hidden element replays its animation when it shows again,
// so every motion class comes off before the next view opens.
//   plate to plate: slide in from the side you moved toward
//   map to plate, or back: grow from the stop you came from
const stopOrigin = { 1: "18% 64%", 2: "50% 64%", 3: "82% 64%" };
const motionClasses = ["view-in", "plate-from-right", "plate-from-left", "intro", "fresh"];

function animateView(from, to) {
  motionClasses.forEach(name => document.querySelectorAll(`.${name}`).forEach(e => e.classList.remove(name)));
  const view = viewOf(to);
  if (from !== 0 && to !== 0) {
    view.classList.add(to > from ? "plate-from-right" : "plate-from-left");
  } else {
    view.style.transformOrigin = stopOrigin[from || to];
    view.classList.add("view-in");
  }
}

drawContours();
let route = routeOf(location.hash);
showView(route);
// the stops rise in once, only when the map is the first thing you see
if (route === 0) document.querySelectorAll(".stop").forEach(stop => stop.classList.add("intro"));

// a new view is a new page to a keyboard or a screen reader, so focus moves to its heading
window.addEventListener("hashchange", () => {
  const next = routeOf(location.hash);
  if (!viewOf(next)) return; // the page refused its data, so there are no views left to show
  if (next !== route) animateView(route, next);
  route = next;
  showView(route);
  viewOf(route).querySelector("h1, h2").focus();
});
