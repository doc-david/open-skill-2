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
}

showView(routeOf(location.hash));

// a new view is a new page to a keyboard or a screen reader, so focus moves to its heading
window.addEventListener("hashchange", () => {
  const route = routeOf(location.hash);
  showView(route);
  viewOf(route).querySelector("h1, h2").focus();
});
