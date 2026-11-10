"""Cell-size audit for the per-venue trend chart (issue #4). Run standalone:

    uv run python report_cell_sizes.py

Prints how many papers back each venue x year x category cell, so the minimum-n
threshold can be chosen from measured numbers (003: measure first, set the bar second).
Deliberately picks NO threshold: it reports the fraction of cells under 10 and under 30.
Shares the counting code with build_analytics_data.py via paper_atlas.venue_trends.
"""
import pandas as pd

from paper_atlas.manifest import NOT_HELD
from paper_atlas.venue_trends import (
    LAST_COMPLETE_YEAR, OTHER, category_columns, collapse_to_top, load_labeled_papers,
    top_categories, venue_vs_pooled, venue_year_table,
)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
YEARS = range(2018, LAST_COMPLETE_YEAR + 1)


def bin_two_years(table: pd.DataFrame) -> pd.DataFrame:
    """Sum counts inside 2-year windows (shares are taken AFTER summing, not averaged).

    n_years_present marks windows built from one year (NAACL's biennial gaps), so they
    cannot be read as a real dip. Judgment call: windows start at 2018 -> 2018-19, ...
    """
    t = table.assign(window=(table["year"] - 2018) // 2)
    cats = [c for c in t.columns if c not in ("venue", "year", "window", "noise_rate", "n_noise")]
    g = t.groupby(["venue", "window"])
    out = g[cats].sum()
    out["n_years_present"] = g["year"].nunique()
    out = out.reset_index()
    out.insert(1, "year", 2018 + 2 * out.pop("window"))  # first year of the window
    return out


def cells(table: pd.DataFrame) -> pd.Series:
    """Long form: one count per present venue-period x category (zeros included)."""
    cats = category_columns(table)
    return table.set_index(["venue", "year"])[cats].stack()


def summarize(name: str, table: pd.DataFrame) -> None:
    c = cells(table)
    print(f"\n--- {name}: {len(c)} cells ---")
    print(c.describe().round(1).to_string())
    print(f"under 10: {(c < 10).mean():.1%} ({(c < 10).sum()})   "
          f"under 30: {(c < 30).mean():.1%} ({(c < 30).sum()})   "
          f"exactly 0: {(c == 0).sum()}")
    per_venue = c.groupby(level="venue").agg(
        cells="size", under10=lambda s: (s < 10).sum(), under30=lambda s: (s < 30).sum())
    per_venue["pct_under30"] = (100 * per_venue["under30"] / per_venue["cells"]).round(1)
    print(per_venue.to_string())


df, names = load_labeled_papers()
table = venue_year_table(df, names)

print("DENOMINATORS: papers per venue-year (n_total), labeled papers, and noise rate")
for col in ("n_total", "n_labeled", "noise_rate"):
    print(f"\n{col}")
    print(table.pivot(index="venue", columns="year", values=col).to_string())

present = set(zip(table["venue"], table["year"]))
absent = [(v, y) for v in sorted(table["venue"].unique()) for y in YEARS if (v, y) not in present]
print("\nSTRUCTURALLY ABSENT venue-years (no papers; no cells exist):")
for v, y in absent:
    print(f"  {v} {y}: {NOT_HELD.get((v, y), 'UNEXPECTED - not in NOT_HELD, investigate')}")
print(f"GENUINELY ZERO cells inside present venue-years (all 9 categories): "
      f"{(cells(table) == 0).sum()}")

summarize("unbinned, all 9 categories", table)
summarize("2-year windows, all 9 categories", bin_two_years(table))
print("\nwindows built from a single year (n_years_present == 1):")
print(bin_two_years(table).query("n_years_present == 1")[["venue", "year"]].to_string(index=False))

vp = venue_vs_pooled(table)
for n in (5, 6):
    top = top_categories(table, n)
    top_t = collapse_to_top(table, top)
    summarize(f"unbinned, top {n} + Other", top_t)
    summarize(f"2-year windows, top {n} + Other", bin_two_years(top_t))
    other = top_t.groupby("venue")[OTHER].sum() / top_t.groupby("venue")["n_labeled"].sum()
    print(f"\ntop {n}: '{OTHER}' = {top_t[OTHER].sum() / top_t['n_labeled'].sum():.1%} overall; "
          f"per venue: {(100 * other).round(1).to_dict()}")
    outside = [c for c in category_columns(table) if c not in top]
    hits = [(v, c, vp['venue_pct'].loc[v, c]) for v in vp.index for c in outside
            if vp['venue_pct'].loc[v, c] >= 10]
    print(f"top {n}: categories outside the set at >=10% of some venue: {hits or 'none'}")


# ---------------------------------------------------------------------------
# Threshold audit (N=6 fixed; binning measured but not adopted for the chart).
# ---------------------------------------------------------------------------
N_FIXED = 6  # judgment call (decision 013): chosen from the N=5 vs N=6 numbers above
Z95 = 1.959964


def wilson_half_width_pp(k: pd.Series, n: pd.Series) -> pd.Series:
    """Half-width of the 95% Wilson interval for a share k/n, in percentage points.

    Hand-written (no statsmodels dependency, CLAUDE.md rule 5); equals
    statsmodels.stats.proportion.proportion_confint(k, n, method="wilson") half-width.
    """
    p, z2 = k / n, Z95 ** 2
    half = Z95 * ((p * (1 - p) / n + z2 / (4 * n ** 2)) ** 0.5) / (1 + z2 / n)
    return 100 * half


def long_cells(t: pd.DataFrame) -> pd.DataFrame:
    """One row per cell: venue, year, category, count k, denominator n, Wilson half-width."""
    cats = category_columns(t)
    long = t.melt(id_vars=["venue", "year", "n_labeled"], value_vars=cats,
                  var_name="category", value_name="k")
    long["n"] = long.pop("n_labeled")
    long["half_pp"] = wilson_half_width_pp(long["k"], long["n"])
    return long


def rule_table(long: pd.DataFrame) -> pd.DataFrame:
    """% of each venue's cells hidden/greyed under each candidate rule."""
    rules = {
        "n<30": long["n"] < 30, "n<50": long["n"] < 50, "n<100": long["n"] < 100,
        "wilson>5": long["half_pp"] > 5, "wilson>10": long["half_pp"] > 10,
        "k<30 (extra)": long["k"] < 30,
    }
    return pd.DataFrame({r: (100 * m.groupby(long["venue"]).mean()).round(1)
                         for r, m in rules.items()})


top6 = top_categories(table, N_FIXED)
t6 = collapse_to_top(table, top6)
for label, tt in (("unbinned", t6), ("2-year windows", bin_two_years(t6))):
    long = long_cells(tt)
    print(f"\n===== THRESHOLD AUDIT: N={N_FIXED}, {label} ({len(long)} cells) =====")
    print("\nlabelled denominator per venue-period (min / median / max):")
    print(tt.groupby("venue")["n_labeled"].agg(["min", "median", "max"]).to_string())
    print("\n% of cells with Wilson 95% half-width > 5pp and > 10pp, and % hidden by each rule:")
    print(rule_table(long).to_string())

print("\nNLP venues: share of labelled papers in the single largest mega bucket, per year")
big = table[table["venue"].isin(["acl", "emnlp", "naacl"])].copy()
cats = category_columns(big)
big["largest_bucket_pct"] = (100 * big[cats].max(axis=1) / big["n_labeled"]).round(1)
big["bucket"] = big[cats].idxmax(axis=1).str[:12]
print(big.pivot(index="venue", columns="year", values="largest_bucket_pct").to_string())
print("bucket name:", sorted(big["bucket"].unique()))


# Relative-width rule (option 2): grey a cell when its Wilson half-width exceeds a fraction
# of its own share. Cutoffs below are for MEASURING only; none is adopted here.
def relative_rule_table(long: pd.DataFrame, cutoffs=(0.25, 0.5, 1.0)) -> pd.DataFrame:
    share_pp = 100 * long["k"] / long["n"]
    rel = (long["half_pp"] / share_pp).where(long["k"] > 0, float("inf"))  # k=0 -> always greyed
    return pd.DataFrame({f"half>{int(c*100)}% of share": (100 * (rel > c).groupby(long["venue"]).mean()).round(1)
                         for c in cutoffs})


for label, tt in (("unbinned", t6), ("2-year windows", bin_two_years(t6))):
    long = long_cells(tt)
    print(f"\n% of cells greyed by the RELATIVE rule, N={N_FIXED}, {label}:")
    print(relative_rule_table(long).to_string())
    k = long["k"]
    share_pp = 100 * k / long["n"]
    rel = long["half_pp"] / share_pp
    print("smallest k kept at each cutoff:", {c: int(k[(k > 0) & (rel <= c)].min())
                                              for c in (0.25, 0.5, 1.0)})
