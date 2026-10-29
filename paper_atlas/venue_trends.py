"""Venue x year x mega-category counts and within-venue-year shares (issue #4).

Single source of truth for these numbers: build_analytics_data.py (writes analytics.json)
and report_cell_sizes.py (prints the sample-size audit) both import from here, so the
chart and the audit cannot disagree. Pure aggregation: no clustering, no LLM, no GPU.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from paper_atlas.embed import load_corpus

# 2026 excluded: structurally partial for most venues (001-scope.md).
LAST_COMPLETE_YEAR = 2025


def load_labeled_papers() -> tuple[pd.DataFrame, dict[int, str]]:
    """One row per paper: year, venue, mega (category id). Includes noise (-1) and 2026.

    Same alignment and orphan-remap logic as build_frontend.py / build_analytics_data.py
    so the totals match the pooled chart. Returns (df, mega_names).
    """
    t = load_corpus()
    ids = t.column("paper_id").to_pylist()
    years = t.column("year").to_pylist()
    venues = t.column("venue").to_pylist()

    mega = np.load("data/knn/megacat_mcs2000_ms5.npz", allow_pickle=False)
    top = np.load("data/knn/midlevel_mcs400_ms5.npz", allow_pickle=False)
    clust = np.load("data/knn/cluster_umap10d_mcs15_ms5.npz", allow_pickle=False)
    names_json = json.load(open("data/knn/megacat_labels.json"))

    pos = {p: i for i, p in enumerate(ids)}
    order = [pos[p] for p in mega["ids"]]
    labels, top_labels, mega_labels = clust["labels"], top["labels"].copy(), mega["labels"].copy()

    # Orphans: leaves with no mid-level parent -> -2; mid groups with no mega parent -> -3.
    for leaf_id in range(int(labels.max()) + 1):
        idx = np.where(labels == leaf_id)[0]
        if len(idx) and (top_labels[idx] >= 0).sum() == 0:
            top_labels[idx] = -2
    for group_val in np.unique(top_labels):
        idx = np.where(top_labels == group_val)[0]
        if (mega_labels[idx] >= 0).sum() == 0:
            mega_labels[idx] = -3

    mega_names = {int(k): v["label"] for k, v in names_json.items()}
    mega_names[-3] = "Cross-Cutting & Specialized Research"
    mega_names[-1] = "Unclustered"

    df = pd.DataFrame({
        "year": [years[i] for i in order],
        "venue": [venues[i] for i in order],
        "mega": mega_labels,
    })
    return df, mega_names


def venue_year_table(df: pd.DataFrame, mega_names: dict[int, str]) -> pd.DataFrame:
    """One row per venue-year PRESENT in df, with counts and within-venue-year shares.

    Judgment call (issue #4, decision 013): the denominator is the venue-year's own
    labeled papers, not the pooled year total. Noise (-1) is dropped before shares are
    computed, matching the pooled chart. n_total / n_noise / noise_rate are reported
    so a venue with a high noise rate is visible rather than silently shrinking its cell.
    Venue-years with no papers (e.g. naacl 2020) have no row; the manifest says why.
    """
    df = df[df["year"] <= LAST_COMPLETE_YEAR]
    totals = df.groupby(["venue", "year"]).size().rename("n_total")
    labeled = df[df["mega"] != -1]
    counts = labeled.groupby(["venue", "year", "mega"]).size().unstack(fill_value=0)
    counts.columns = [mega_names.get(c, str(c)) for c in counts.columns]

    out = counts.copy()
    out.insert(0, "n_labeled", counts.sum(axis=1))
    out.insert(0, "n_total", totals.reindex(out.index))
    out.insert(2, "n_noise", out["n_total"] - out["n_labeled"])
    out.insert(3, "noise_rate", (out["n_noise"] / out["n_total"]).round(4))
    return out.reset_index()


def category_columns(table: pd.DataFrame) -> list[str]:
    meta = ("venue", "year", "n_total", "n_labeled", "n_noise", "noise_rate", "n_years_present")
    return [c for c in table.columns if c not in meta]


OTHER = "Other"


def top_categories(table: pd.DataFrame, n: int) -> list[str]:
    """The n largest categories by POOLED labeled-paper count across all venues and years.

    Judgment call (decision 013): one fixed set for every venue, so panels are comparable.
    Ranked on the whole pooled corpus, not any single year, so the set cannot drift.
    Ties break alphabetically so the choice is deterministic across runs.
    """
    pooled = table[category_columns(table)].sum()
    return sorted(pooled.index, key=lambda c: (-pooled[c], c))[:n]


def collapse_to_top(table: pd.DataFrame, top: list[str]) -> pd.DataFrame:
    """Keep `top` as columns and sum every other category into a plotted "Other" column.

    "Other" is kept, not dropped, so counts still sum to n_labeled and shares to 100%.
    """
    rest = [c for c in category_columns(table) if c not in top]
    out = table.drop(columns=rest)
    out[OTHER] = table[rest].sum(axis=1)
    return out


def venue_vs_pooled(table: pd.DataFrame) -> pd.DataFrame:
    """Per venue x category: share of that venue's labeled papers (all years) vs the pooled
    share, plus the gap in percentage points. Used to check whether a category that is
    small pooled is large in one venue, which a fixed top-N would hide inside "Other".
    """
    cats = category_columns(table)
    by_venue = table.groupby("venue")[cats].sum()
    venue_share = by_venue.div(by_venue.sum(axis=1), axis=0) * 100
    pooled_share = table[cats].sum() / table[cats].sum().sum() * 100
    return pd.concat({
        "venue_pct": venue_share.round(1),
        "gap_pp": (venue_share - pooled_share).round(1),
    }, axis=1)
