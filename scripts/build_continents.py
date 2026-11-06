"""
build_continents.py
gives every country on the three charts a continent, so one continent filter
can drive all three charts. it reuses the exact continent rule from
prep_data.py (open skill 1, chart 3), so chart 3's continents can't drift.

run: python scripts/build_continents.py   (writes data/continents.json)
"""
import json
from pathlib import Path

import pandas as pd

from prep_data import continent_of

root = Path(__file__).resolve().parent.parent
df = pd.read_csv(root / "data" / "world-happiness-2019-2025.csv")
data = json.loads((root / "data" / "chart-data.json").read_text(encoding="utf-8"))

# every country that appears on a chart
c1 = data["chart1_ranked_bar"]
c2 = data["chart2_lines"]
names = [r["country"] for r in c1["top10"] + c1["bottom10"]]
names += [s["country"] for s in c2["context_series"] + c2["risers"] + c2["fallers"]]
names += [r["country"] for r in data["chart3_stacked"]["rows"]]

continents = {}
for name in sorted(set(names)):
    regions = df.loc[df["Country"] == name, "Region"].unique()
    # a country must keep one region across all 7 years, or its continent would be ambiguous
    assert len(regions) == 1, f"{name} has regions {list(regions)}"
    continents[name] = continent_of(name, regions[0])

# chart 3's rows already carry a continent from prep_data.py; they must agree
for row in data["chart3_stacked"]["rows"]:
    assert continents[row["country"]] == row["continent"], row["country"]

out = root / "data" / "continents.json"
out.write_text(json.dumps(continents, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
counts = pd.Series(continents).value_counts().to_dict()
print(f"wrote {out.relative_to(root)}: {len(continents)} countries {counts}")
