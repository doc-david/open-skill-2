// the screens: one view shows at a time, and the address bar's hash says which one.
// (the map's moving background and its pause toggle are in landscape.js)
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

// a screen's arrival class comes off when it lands, and so does the scroll guard. on the map it's the
// content that arrives, never the ground under it
views.addEventListener("animationend", event => {
  if (event.target.matches(".view, .map-inner") && event.animationName !== "fade-in") {
    event.target.closest(".view").classList.remove("view-in", "chart-from-right", "chart-from-left");
    views.classList.remove("settling");
  }
});

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
    // on the map, the content grows from the stop and the ground stays put, so it's never half there
    (to === 0 ? view.querySelector(".map-inner") : view).style.transformOrigin = stopOrigin[from || to];
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
