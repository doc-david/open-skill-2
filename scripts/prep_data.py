"""
prep_data.py
============
Builds `chart-data.json` — the single source of truth for every number in the
World Happiness slide deck (INFO 4602 "Open Skill" project).

The Figma build never computes or types a value itself. It reads this file.
That way every bar length, line point and quoted number traces back to the CSV.

Input : world-happiness-2019-2025.csv   (one row per country per survey year)
Output: chart-data.json                  (schema defined in claude/working-rules.md)

Run:
    python prep_data.py
    python prep_data.py --csv path/to/world-happiness-2019-2025.csv --out chart-data.json

Key facts about the data (verified in claude/data-verification.md):
  * `Year` is the SURVEY year. The 2025 rows are the ranking published in the
    World Happiness Report 2026, so slides label them "2025 (WHR 2026)".
  * The six factor columns are CONTRIBUTIONS to the score ("Explained by GDP..."),
    not raw measures, and their scale changes every edition. So factor values are
    only ever used within a single year (2025) — never compared across years.
  * Ranks are the OFFICIAL ranks. A few ranked countries are absent from the CSV
    (2025 has 145 rows but ranks run to 147), so we never recompute ranks.
  * Stored values keep the CSV's 3-decimal precision. Display formatting
    (e.g. changes shown as signed 2-decimal "+1.08") is the build's job.
  * Chart 3 (since Oct 6) shows the best-ranked country on each of six
    continents; the continent rule is documented next to CONTINENTS below.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Locked decisions (from claude/working-rules.md). Change them there first.
# ---------------------------------------------------------------------------
CHART_YEAR = 2025            # survey year shown in charts 1 and 3
BASE_YEAR = 2019             # first survey year; "change since 2019" starts here
YEARS = list(range(2019, 2026))
REPORT_EDITION = "WHR 2026"  # the report that published the 2025 survey ranking

FACTORS = [                  # the six "Explained by ..." contribution columns
    "GDP per Capita",
    "Social Support",
    "Life Expectancy",
    "Freedom",
    "Generosity",
    "Corruption",
]
UNEXPLAINED = "Unexplained"  # score minus the six factors (the report's "Dystopia + residual")

CHART1_HIGHLIGHT = ["Costa Rica"]
CHART2_N_HIGHLIGHT = 5       # 5 risers and 5 fallers
# Chart 2 y-axis = the full 0-10 score scale, ticks every 2 points: the same
# ticks as charts 1 and 3 (David, Oct 6, 15:43: "Fix y axis in chart 2, make it
# consistent and 0-10 like the other charts"). Replaces the 1-8 domain that was
# derived from the data range (floor of the lowest point, ceiling of the highest).
CHART2_Y_MIN, CHART2_Y_MAX, CHART2_Y_STEP = 0, 10, 2

# Chart 3 = the best OFFICIAL 2025 rank on each continent (David, Oct 6).
# Every 2025 row gets a continent from its CSV region (the CSV's 14 UN regions).
# Six continents: Antarctica has no data. The continent is a grouping label set
# by this rule (UN regions + David's choices), not a value from the CSV.
CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]
CONTINENT_OF_REGION = {
    "Northern Africa": "Africa",
    "Sub-Saharan Africa": "Africa",
    "Central Asia": "Asia",
    "Eastern Asia": "Asia",
    "South-eastern Asia": "Asia",
    "Southern Asia": "Asia",
    # David: Western Asia counts as Asia. Edge cases follow the CSV's region:
    # Israel, Cyprus, Türkiye and the Caucasus (Armenia, Georgia, Azerbaijan) -> Asia.
    "Western Asia": "Asia",
    "Eastern Europe": "Europe",      # includes the Russian Federation -> Europe
    "Northern Europe": "Europe",
    "Southern Europe": "Europe",
    "Western Europe": "Europe",
    "Northern America": "North America",
    "Australia and New Zealand": "Oceania",
}
# "Latin America and the Caribbean" is split by country. David: Mexico, Central
# America and the Caribbean count as North America (Trinidad and Tobago is a
# Caribbean country, so North America too). Both lists cover every Latin American
# country in the CSV (any year); a country in neither list stops the script.
LATAM_REGION = "Latin America and the Caribbean"
LATAM_NORTH_AMERICA = [
    "Belize", "Costa Rica", "Dominican Republic", "El Salvador", "Guatemala", "Haiti",
    "Honduras", "Jamaica", "Mexico", "Nicaragua", "Panama", "Trinidad and Tobago",
]
LATAM_SOUTH_AMERICA = [
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Ecuador",
    "Paraguay", "Peru", "Uruguay", "Venezuela",
]
# "Nordic" is a fixed list of five countries. It is NOT the CSV's
# "Northern Europe" region, which also includes the UK, Ireland and the Baltics.
NORDIC = ["Denmark", "Finland", "Iceland", "Norway", "Sweden"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def r3(x):
    """Round to 3 decimals and return a plain Python float.

    Subtracting two 3-decimal numbers in floating point leaves tiny noise
    (e.g. 7.764 - 7.809 = -0.04499999...). Rounding to 3 decimals removes it.
    Adding 0.0 turns a possible -0.0 into 0.0 so the JSON never shows "-0.0".
    """
    return float(round(float(x), 3)) + 0.0


def load(csv_path):
    """Read the CSV and run the sanity checks the rest of the script relies on."""
    df = pd.read_csv(csv_path)

    assert df.notna().all().all(), "CSV has missing values"
    assert not df.duplicated(["Year", "Country"]).any(), "duplicate country-year rows"
    assert sorted(df["Year"].unique()) == YEARS, "unexpected set of years"

    # Within each year, sorting by official rank must give non-increasing scores.
    for year, g in df.groupby("Year"):
        scores = g.sort_values("Happiness Rank")["Happiness Score"].tolist()
        assert all(a >= b for a, b in zip(scores, scores[1:])), f"rank/score mismatch in {year}"
        assert g["Happiness Rank"].is_unique, f"duplicate ranks in {year}"
    return df


# ---------------------------------------------------------------------------
# Chart 1 — ranked horizontal bars, 2025: top 10 + bottom 10
# ---------------------------------------------------------------------------
def build_chart1(df):
    year = df[df["Year"] == CHART_YEAR]
    base_scores = df[df["Year"] == BASE_YEAR].set_index("Country")["Happiness Score"]

    def bar(row):
        country = row["Country"]
        # change_since_2019 is null when the country has no 2019 row
        change = r3(row["Happiness Score"] - base_scores[country]) if country in base_scores.index else None
        return {
            "rank": int(row["Happiness Rank"]),
            "country": country,
            "region": row["Region"],
            "score": r3(row["Happiness Score"]),
            "change_since_2019": change,
        }

    # Top 10 = official ranks 1-10. Bottom 10 = the 10 highest rank numbers that
    # exist in the CSV. Both lists are sorted by ascending rank, which is also
    # the top-to-bottom drawing order on the slide.
    top10 = year.nsmallest(10, "Happiness Rank").sort_values("Happiness Rank")
    bottom10 = year.nlargest(10, "Happiness Rank").sort_values("Happiness Rank")

    return {
        "year": CHART_YEAR,
        "total_ranked": int(year["Happiness Rank"].max()),  # official count (147), not the row count (145)
        "highlight": CHART1_HIGHLIGHT,
        "top10": [bar(r) for _, r in top10.iterrows()],
        "bottom10": [bar(r) for _, r in bottom10.iterrows()],
    }


# ---------------------------------------------------------------------------
# Chart 2 — line chart 2019-2025 with a risers/fallers toggle
# ---------------------------------------------------------------------------
def build_chart2(df):
    # One row per country, one column per year. Keep only countries with all 7
    # years, so every line has the same start and end point (133 countries).
    wide = df.pivot(index="Country", columns="Year", values="Happiness Score")[YEARS]
    complete = wide.dropna()

    def series(country):
        return [r3(v) for v in complete.loc[country, YEARS]]

    changes = {c: r3(complete.loc[c, CHART_YEAR] - complete.loc[c, BASE_YEAR]) for c in complete.index}

    # Risers: largest change first. Fallers: most negative change first.
    # Ties are broken alphabetically by country name.
    risers = sorted(changes, key=lambda c: (-changes[c], c))[:CHART2_N_HIGHLIGHT]
    fallers = sorted(changes, key=lambda c: (changes[c], c))[:CHART2_N_HIGHLIGHT]
    highlighted = set(risers) | set(fallers)

    # Fixed y-axis domain (David, Oct 6; see CHART2_Y_* above). Every point must fit.
    assert CHART2_Y_MIN <= complete.min().min() and complete.max().max() <= CHART2_Y_MAX, \
        "a chart 2 point falls outside the y-axis"

    return {
        "years": YEARS,
        "y_axis": {"min": CHART2_Y_MIN, "max": CHART2_Y_MAX,
                   "ticks": list(range(CHART2_Y_MIN, CHART2_Y_MAX + 1, CHART2_Y_STEP))},
        # Faint background lines: every complete country except the 10 highlighted,
        # so no country is drawn twice. Alphabetical order.
        "context_series": [
            {"country": c, "scores": series(c)}
            for c in sorted(complete.index) if c not in highlighted
        ],
        "risers": [{"country": c, "scores": series(c), "change": changes[c]} for c in risers],
        "fallers": [{"country": c, "scores": series(c), "change": changes[c]} for c in fallers],
    }


# ---------------------------------------------------------------------------
# Chart 3 — stacked horizontal bars: what each factor contributes, 2025 only
# ---------------------------------------------------------------------------
def continent_of(country, region):
    """Continent of one CSV row, by the rule above."""
    if region == LATAM_REGION:
        in_north, in_south = country in LATAM_NORTH_AMERICA, country in LATAM_SOUTH_AMERICA
        assert in_north != in_south, f"{country} must be in exactly one Latin America list"
        return "North America" if in_north else "South America"
    assert region in CONTINENT_OF_REGION, f"no continent for region {region!r}"
    return CONTINENT_OF_REGION[region]


def with_continent(df):
    """The CHART_YEAR rows, each with a Continent column."""
    year = df[df["Year"] == CHART_YEAR].copy()
    year["Continent"] = [continent_of(c, r) for c, r in zip(year["Country"], year["Region"])]
    assert sorted(year["Continent"].unique()) == sorted(CONTINENTS), "expected exactly the six continents"
    return year


def build_chart3(df):
    # One row per continent: the country with the best (lowest) official rank.
    # Ranks are unique within a year (checked in load), so there are no ties.
    year = with_continent(df)
    leaders = year.loc[year.groupby("Continent")["Happiness Rank"].idxmin()]
    assert len(leaders) == len(CONTINENTS)
    leaders = leaders.sort_values("Happiness Rank")

    rows = []
    for _, r in leaders.iterrows():
        factors = {f: r3(r[f]) for f in FACTORS}
        unexplained = r3(r["Happiness Score"] - sum(r[f] for f in FACTORS))
        # The stack must add back up to the score, and no segment may be negative.
        assert r3(sum(factors.values()) + unexplained) == r3(r["Happiness Score"]), r["Country"]
        assert unexplained >= 0, f"negative unexplained for {r['Country']}"
        rows.append({
            "country": r["Country"],
            "continent": r["Continent"],
            "rank": int(r["Happiness Rank"]),
            "score": r3(r["Happiness Score"]),
            "factors": factors,
            "unexplained": unexplained,
        })

    return {
        "year": CHART_YEAR,
        "factor_order": FACTORS + [UNEXPLAINED],
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Headline facts — every number the slide copy is allowed to quote
# ---------------------------------------------------------------------------
def signed_2dp(x):
    """Display string for a change: sign + 2 decimals, rounding half away from zero.

    Done with integer arithmetic on thousandths so 1.075 becomes "+1.08"
    (plain float formatting would give "+1.07" because 1.075 is stored as 1.07499...).
    """
    thousandths = int(round(x * 1000))
    hundredths = (abs(thousandths) + 5) // 10          # round half away from zero
    sign = "" if hundredths == 0 else "+" if thousandths > 0 else "-"
    return f"{sign}{hundredths // 100}.{hundredths % 100:02d}"


def score_2dp(x):
    """Display string for a score: 2 decimals, half away from zero, from integer
    thousandths (6.635 -> "6.64"; JavaScript toFixed(2) would give "6.63")."""
    thousandths = int(round(x * 1000))
    assert thousandths >= 0, x
    hundredths = (thousandths + 5) // 10
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def build_headline_facts(df, chart1, chart2, chart3):
    year = df[df["Year"] == CHART_YEAR]
    by_country_year = df.set_index(["Country", "Year"])

    def rank(country, y):
        return int(by_country_year.loc[(country, y), "Happiness Rank"])

    def score(country, y):
        return r3(by_country_year.loc[(country, y), "Happiness Score"])

    # Finland at #1 in every survey year?
    finland_ranks = [rank("Finland", y) for y in YEARS]

    # Nordic countries (fixed list) inside the 2025 top 10, in rank order
    top10_names = [b["country"] for b in chart1["top10"]]
    nordic_top10 = [c for c in top10_names if c in NORDIC]

    # Top riser / faller come straight from chart 2 so the copy can't drift from the chart
    top_riser, top_faller = chart2["risers"][0], chart2["fallers"][0]

    # Chart 3 context: each continent's leader, its runner-up, and how many of the
    # continent's countries are in the CSV's 2025 rows. (Ranks 88 and 109 are
    # missing from the CSV, so their continents are unknown: CSV counts only.)
    c3 = chart3["rows"]
    year_c = with_continent(df)
    leaders = []
    for row in c3:
        members = year_c[year_c["Continent"] == row["continent"]].sort_values("Happiness Rank")
        assert members.iloc[0]["Country"] == row["country"], row["continent"]
        runner_up = members.iloc[1]
        leaders.append({
            "continent": row["continent"],
            "country": row["country"],
            "rank": row["rank"],
            "score_display": score_2dp(row["score"]),
            "runner_up_country": runner_up["Country"],
            "runner_up_rank": int(runner_up["Happiness Rank"]),
            "countries_in_csv_2025": int(len(members)),
        })

    us_change = r3(score("United States", CHART_YEAR) - score("United States", BASE_YEAR))

    return {
        "finland_rank_1_all_years": all(r == 1 for r in finland_ranks),
        "finland_score_2025": score("Finland", CHART_YEAR),

        "costa_rica_rank_by_year": {str(y): rank("Costa Rica", y) for y in YEARS},
        "costa_rica_rank_2025": rank("Costa Rica", CHART_YEAR),
        "costa_rica_score_2025": score("Costa Rica", CHART_YEAR),

        "us_rank_2019": rank("United States", BASE_YEAR),
        "us_rank_2025": rank("United States", CHART_YEAR),
        "us_score_2019": score("United States", BASE_YEAR),
        "us_score_2025": score("United States", CHART_YEAR),
        "us_change_since_2019": us_change,
        "us_change_since_2019_display": signed_2dp(us_change),

        "nordic_in_top10_2025": {"count": len(nordic_top10), "names": nordic_top10},

        "total_ranked_2025": int(year["Happiness Rank"].max()),
        "rows_2025": int(len(year)),
        "missing_ranks_2025": sorted(set(range(1, int(year["Happiness Rank"].max()) + 1))
                                     - set(year["Happiness Rank"].astype(int))),
        "countries_in_trend_chart": len(chart2["context_series"]) + len(chart2["risers"]) + len(chart2["fallers"]),

        "top_riser": {
            "country": top_riser["country"],
            "score_2019": top_riser["scores"][0],
            "score_2025": top_riser["scores"][-1],
            "change": top_riser["change"],
            "change_display": signed_2dp(top_riser["change"]),
        },
        "top_faller": {
            "country": top_faller["country"],
            "score_2019": top_faller["scores"][0],
            "score_2025": top_faller["scores"][-1],
            "change": top_faller["change"],
            "change_display": signed_2dp(top_faller["change"]),
        },

        # Chart 3 (David, Oct 6): the top country of each continent, in row order.
        # Replaces the 8-country keys chart3_us_gdp and chart3_costa_rica_unexplained.
        "chart3_continent_leaders": leaders,

        # Chart 3 factors equal to 0 (= lowest in the world in 2025, not missing).
        # A 0 segment has no width and can't be hovered, so the build adds a small
        # highlighted hover area above that country's name instead (David, Oct 5).
        "chart3_zero_factors": [
            {"country": r["country"], "factors": [f for f in FACTORS if r["factors"][f] == 0]}
            for r in c3 if any(r["factors"][f] == 0 for f in FACTORS)
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build chart-data.json from the World Happiness CSV.")
    parser.add_argument("--csv", default=here / "world-happiness-2019-2025.csv")
    parser.add_argument("--out", default=here / "chart-data.json")
    args = parser.parse_args()

    df = load(args.csv)
    chart1 = build_chart1(df)
    chart2 = build_chart2(df)
    chart3 = build_chart3(df)

    data = {
        "meta": {
            "source": "World Happiness Report (Gallup World Poll)",
            "file": Path(args.csv).name,
            "survey_year": CHART_YEAR,
            "report_edition": REPORT_EDITION,
            "generated_by": "prep_data.py",
        },
        "chart1_ranked_bar": chart1,
        "chart2_lines": chart2,
        "chart3_stacked": chart3,
        "headline_facts": build_headline_facts(df, chart1, chart2, chart3),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
