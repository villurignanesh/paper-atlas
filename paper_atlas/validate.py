"""Independent recall check against DBLP (002's Phase 1 acceptance test).

Scoped deliberately to the SCRAPED sources, NeurIPS (papers.nips.cc HTML) and ICML
(PMLR HTML), where silent omission is a real risk and DBLP is genuinely independent.

Not run for ACL/EMNLP/NAACL: the ACL Anthology *is* the canonical record for those
venues and DBLP indexes from it, so the comparison would be close to circular. It would
also require re-deriving 006's volume mapping in DBLP's second naming scheme
(naacl2024-1..-6, naacl2024f, emnlp2025i), which buys no independent evidence.

ICLR is validated separately and by construction: DBLP supplies its accept list (007).
"""

from __future__ import annotations

from paper_atlas.dblp import normalise_title, toc_titles
from paper_atlas.embed import load_corpus

# DBLP renamed the NeurIPS stream partway through: nips2018/19, neurips2020 onward.
NEURIPS_KEY = lambda y: ("nips" if y <= 2019 else "neurips") + str(y)
ICML_KEY = lambda y: f"icml{y}"


def check(venue: str, key_fn, years: range | list[int]) -> list[dict]:
    corpus = load_corpus()
    ours: dict[int, set[str]] = {}
    for pid, v, y, t in zip(corpus.column("paper_id").to_pylist(),
                            corpus.column("venue").to_pylist(),
                            corpus.column("year").to_pylist(),
                            corpus.column("title").to_pylist()):
        if v == venue:
            ours.setdefault(y, set()).add(normalise_title(t))

    rows = []
    for y in years:
        key = key_fn(y)
        conf = "nips" if venue == "neurips" else venue
        # toc_titles caches, so re-running this check is free after the first pass
        dblp = {normalise_title(t) for t in toc_titles(conf, y, None) } if True else set()
        if not dblp:
            rows.append({"year": y, "dblp": 0, "ours": len(ours.get(y, ())),
                         "matched": 0, "recall": None, "note": f"no DBLP TOC for {key}"})
            continue
        mine = ours.get(y, set())
        matched = dblp & mine
        rows.append({"year": y, "dblp": len(dblp), "ours": len(mine),
                     "matched": len(matched),
                     "recall": round(len(matched) / len(dblp), 4),
                     "missing_sample": sorted(dblp - mine)[:2]})
    return rows
