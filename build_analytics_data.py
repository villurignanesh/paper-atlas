"""Analytics data prep: venue/year counts (from the manifest) + mega-category share of
corpus over time. Pure aggregation of data already computed by build_frontend.py's
loading logic: no new clustering, no LLM calls, no GPU.
"""
import json
import pandas as pd
from paper_atlas.venue_trends import (
    LAST_COMPLETE_YEAR, category_columns, load_labeled_papers, venue_year_table,
)

# Loading + orphan remap live in paper_atlas/venue_trends.py so the venue-split numbers
# and report_cell_sizes.py share one code path with this pooled chart.
df, mega_names = load_labeled_papers()
df_all = df  # unfiltered; the venue table applies the same year cut itself

# 2026 excluded: structurally partial for most venues (001-scope.md), would misleadingly
# read as a collapse in every trend line rather than "the year isn't over yet".
df = df[df["year"] <= LAST_COMPLETE_YEAR]

# Mega-category share of corpus, by year. "Unclustered" (-1, genuine HDBSCAN noise at
# this clustering resolution, not a research area) dropped from THIS chart specifically:
# it sits flat around ~13% every year, so it's not a trend, just clustering noise
# competing for attention against the 8 real lines. Still shown as-is on the map and
# Browse table, where per-paper transparency matters more than trend legibility.
# "Cross-Cutting & Specialized Research" (-3) is kept: unlike noise, those points DO have
# a real mid-level topic, they just don't fit one of the 8 broad areas, which is a
# genuine (if imprecise) research-content signal, not an algorithm artifact.
# Denominator recomputed on the filtered rows so the remaining 9 lines still sum to 100%
# instead of silently topping out around 87%.
df = df[df["mega"] != -1]
share = (df.groupby(["year", "mega"]).size().unstack(fill_value=0))
share_pct = share.div(share.sum(axis=1), axis=0) * 100
share_pct.columns = [mega_names.get(c, str(c)) for c in share_pct.columns]
share_pct = share_pct.round(2)

# Venue paper counts, by year, from the manifest (has the completeness flag).
# 2026 excluded here too, same reasoning as the mega-share filter above: structurally
# partial for most venues, not enough data yet to show as its own column.
manifest = pd.read_parquet("data/manifest.parquet")
manifest = manifest[["venue", "year", "n_papers", "complete"]]
manifest = manifest[manifest["year"] <= 2025]

# Per-venue series (issue #4). Additive: the two keys below are untouched. Shares are
# within each venue-year (decision 013), over labeled papers only (-1 dropped), same
# rule as the pooled chart. Counts are emitted too so the page can show n, not just %.
vy = venue_year_table(df_all, mega_names)
cats = category_columns(vy)
vy_records = []
for _, r in vy.iterrows():
    vy_records.append({
        "venue": r["venue"], "year": int(r["year"]),
        "n_total": int(r["n_total"]), "n_labeled": int(r["n_labeled"]),
        "n_noise": int(r["n_noise"]), "noise_rate": float(r["noise_rate"]),
        "counts": {c: int(r[c]) for c in cats},
        "share_pct": {c: round(100 * r[c] / r["n_labeled"], 2) for c in cats},
    })

out = {
    "mega_share_by_year": {
        "years": share_pct.index.tolist(),
        "series": {col: share_pct[col].tolist() for col in share_pct.columns},
    },
    "venue_counts_by_year": manifest.to_dict(orient="records"),
    "venue_year_mega": {"categories": cats, "rows": vy_records},
}
json.dump(out, open("data/analytics.json", "w"), indent=2)
print(f"mega categories: {len(share_pct.columns)}")
print(f"years: {share_pct.index.tolist()}")
print(f"venue-year rows: {len(manifest)}")
print("wrote data/analytics.json")
