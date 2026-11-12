"""Read-only paper queries shared by future local and hosted MCP transports.

Results are grounded in source metadata and abstracts, not extracted PDF text.
"""

from collections import defaultdict
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


PAPER_COLUMNS = (
    "paper_id", "title", "abstract", "authors", "venue", "year",
    "source", "source_url", "pdf_url", "keywords",
)
EVIDENCE_SCOPE = "source metadata and abstract; no full-text verification"


def _bounded_limit(limit: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("limit must be an integer from 1 to 50")
    return limit


def _summary(paper: dict, *, include_abstract: bool = False,
             query_terms: tuple[str, ...] = ()) -> dict:
    result = {key: paper.get(key) for key in (
        "paper_id", "title", "venue", "year", "source", "source_url", "pdf_url",
    )}
    abstract = paper.get("abstract") or ""
    excerpt = abstract[:320]
    if query_terms and len(abstract) > 320:
        positions = [abstract.casefold().find(term) for term in query_terms]
        positions = [pos for pos in positions if pos >= 0]
        if positions:
            start = max(0, min(positions) - 80)
            excerpt = ("…" if start else "") + abstract[start:start + 320]
            if start + 320 < len(abstract):
                excerpt += "…"
    result["abstract" if include_abstract else "abstract_excerpt"] = (
        abstract if include_abstract else excerpt
    )
    result["evidence_scope"] = EVIDENCE_SCOPE
    return result


class PaperCorpus:
    """Load one versioned local corpus; transport adapters call these methods."""

    def __init__(self, data_dir: str | Path):
        root = Path(data_dir)
        paths = sorted((root / "normalized").glob("*/*.parquet"))
        if not paths:
            raise FileNotFoundError(f"no normalized Parquet files under {root}")

        papers = {}
        for path in paths:
            for paper in pq.read_table(path, columns=list(PAPER_COLUMNS)).to_pylist():
                paper_id = paper["paper_id"]
                if paper_id in papers:
                    raise ValueError(f"duplicate paper_id: {paper_id}")
                papers[paper_id] = paper
        self.papers = papers

        cluster_path = root / "knn" / "cluster_umap10d_mcs15_ms5.npz"
        with np.load(cluster_path, allow_pickle=False) as clusters:
            ids = clusters["ids"].tolist()
            labels = clusters["labels"].tolist()
        if len(ids) != len(labels) or len(set(ids)) != len(ids):
            raise ValueError("leaf cluster snapshot has duplicate or missing assignments")
        assignments = dict(zip(ids, labels))
        if set(assignments) != set(papers):
            raise ValueError("leaf cluster IDs do not match normalized paper IDs")
        self.cluster_by_paper = assignments
        members = defaultdict(list)
        for paper_id, cluster_id in assignments.items():
            if cluster_id >= 0:
                members[cluster_id].append(paper_id)
        self.members_by_cluster = members
        label_path = root / "knn" / "cluster_labels.json"
        self.cluster_labels = json.loads(label_path.read_text())

    def get_paper(self, paper_id: str) -> dict:
        """Return source-linked metadata and the full available abstract."""
        paper = self.papers.get(paper_id)
        if paper is None:
            raise LookupError(f"unknown paper_id: {paper_id}")
        result = _summary(paper, include_abstract=True)
        result["authors"] = [author["name"] for author in paper.get("authors") or []]
        result["keywords"] = paper.get("keywords") or []
        cluster_id = self.cluster_by_paper[paper_id]
        result["leaf_cluster"] = (
            {"id": cluster_id, "label": self.cluster_labels.get(str(cluster_id), {}).get("label")}
            if cluster_id >= 0 else None
        )
        return result

    def search_papers(
        self, query: str, *, venue: str | None = None,
        year: int | None = None, limit: int = 10,
    ) -> dict:
        """Lexical AND search; title/author matches rank above abstract matches."""
        limit = _bounded_limit(limit)
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        terms = query.casefold().split()
        if not terms:
            raise ValueError("query must contain a search term")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            raise ValueError("year must be an integer")
        if venue is not None and not isinstance(venue, str):
            raise ValueError("venue must be a string")
        venue_key = venue.casefold() if venue else None
        matches = []
        for paper in self.papers.values():
            if venue_key and paper["venue"].casefold() != venue_key:
                continue
            if year is not None and paper["year"] != year:
                continue
            fields = {
                "title": (paper["title"] or "").casefold(),
                "abstract": (paper["abstract"] or "").casefold(),
                "authors": " ".join(a["name"] for a in paper["authors"] or []).casefold(),
                "keywords": " ".join(paper["keywords"] or []).casefold(),
            }
            if not all(any(term in value for value in fields.values()) for term in terms):
                continue
            basis = [name for name, value in fields.items() if any(t in value for t in terms)]
            score = sum(
                weight * sum(term in fields[name] for term in terms)
                for name, weight in (("title", 4), ("authors", 3),
                                     ("keywords", 2), ("abstract", 1))
            )
            if query.casefold() in fields["title"]:
                score += 8
            matches.append((score, paper, basis))
        matches.sort(key=lambda item: (-item[0], -item[1]["year"], item[1]["paper_id"]))
        papers = []
        for _score, paper, basis in matches[:limit]:
            result = _summary(paper, query_terms=tuple(terms))
            result["match_basis"] = basis
            papers.append(result)
        return {"query": query, "search_method": "lexical", "total_matches": len(matches),
                "papers": papers, "evidence_scope": EVIDENCE_SCOPE}

    def related_papers(self, paper_id: str, *, limit: int = 10) -> dict:
        """Return same-leaf papers, newest first; this is not similarity ranking."""
        limit = _bounded_limit(limit)
        if paper_id not in self.papers:
            raise LookupError(f"unknown paper_id: {paper_id}")
        cluster_id = self.cluster_by_paper[paper_id]
        if cluster_id < 0:
            return {"paper_id": paper_id, "relationship": "unclustered",
                    "papers": [], "evidence_scope": EVIDENCE_SCOPE}
        members = (self.papers[pid] for pid in self.members_by_cluster[cluster_id]
                   if pid != paper_id)
        ranked = sorted(members, key=lambda p: (-p["year"], p["paper_id"]))
        return {
            "paper_id": paper_id,
            "relationship": "same_leaf_cluster; newest first, not similarity-ranked",
            "leaf_cluster": {"id": cluster_id,
                             "label": self.cluster_labels.get(str(cluster_id), {}).get("label")},
            "total_cluster_peers": len(ranked),
            "papers": [_summary(p) for p in ranked[:limit]],
            "evidence_scope": EVIDENCE_SCOPE,
        }
