// number formats copied from the open skill 1 prd (section 4.3), so the web page shows
// exactly the same numbers as the figma dashboards.
// javascript's toFixed(2) rounds 1.075 down to "1.07" (1.075 is stored as 1.07499...),
// so we round from whole thousandths instead: 1.075 -> 1075 -> 108 hundredths -> "1.08"
const minus = "−";

// scores and factor values: 2 decimals, e.g. 7.76
function formatScore(value) {
  const thousandths = Math.round(value * 1000);
  const hundredths = Math.floor((Math.abs(thousandths) + 5) / 10);
  const sign = thousandths < 0 ? minus : "";
  return sign + Math.floor(hundredths / 100) + "." + String(hundredths % 100).padStart(2, "0");
}

// changes are always signed, e.g. +1.08 or −1.12 (a real minus sign, not a hyphen)
function formatChange(value) {
  const thousandths = Math.round(value * 1000);
  const hundredths = Math.floor((Math.abs(thousandths) + 5) / 10);
  if (hundredths === 0) return "0.00";
  const sign = thousandths > 0 ? "+" : minus;
  return sign + Math.floor(hundredths / 100) + "." + String(hundredths % 100).padStart(2, "0");
}
