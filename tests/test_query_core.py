"""Query-core contract checks using a small, intentionally inconsistent corpus."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from paper_atlas.query_core import PaperCorpus


class QueryCoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        (root / "normalized" / "iclr").mkdir(parents=True)
        (root / "knn").mkdir()
        self.root = root
        rows = []
        for paper_id, title, abstract, year in (
            ("iclr:2023:a", "Alpha", "x" * 360 + " diffusion evidence", 2023),
            ("iclr:2024:b", "Beta Diffusion", "A short abstract", 2024),
            ("iclr:2024:c", "Unrelated", "No match", 2024),
            ("iclr:2024:d", "Unclustered", "No match", 2024),
        ):
            rows.append({
                "paper_id": paper_id, "title": title, "abstract": abstract,
                "authors": [{"name": "A Researcher", "source_author_id": None}],
                "venue": "iclr", "year": year, "source": "openreview",
                "source_url": f"https://example.test/{paper_id}", "pdf_url": None,
                "keywords": [],
            })
        pq.write_table(pa.Table.from_pylist(rows), root / "normalized" / "iclr" / "papers.parquet")
        self.ids = [row["paper_id"] for row in rows]
        np.savez(root / "knn" / "cluster_umap10d_mcs15_ms5.npz",
                 ids=self.ids, labels=[7, 7, 8, -1])
        (root / "knn" / "cluster_labels.json").write_text(
            json.dumps({"7": {"label": "Diffusion"}, "8": {"label": "Other"}}))

    def test_search_exposes_matching_text_and_source(self):
        corpus = PaperCorpus(self.root)
        result = corpus.search_papers("diffusion", limit=2)
        self.assertEqual(result["search_method"], "lexical")
        self.assertEqual([p["paper_id"] for p in result["papers"]], self.ids[:2][::-1])
        self.assertIn("diffusion", result["papers"][1]["abstract_excerpt"])
        self.assertEqual(result["papers"][0]["source_url"],
                         "https://example.test/iclr:2024:b")
        self.assertEqual(corpus.search_papers("diffusion", year=2023)["total_matches"], 1)

    def test_related_is_cluster_membership_not_a_claim_of_support(self):
        corpus = PaperCorpus(self.root)
        self.assertEqual(corpus.get_paper(self.ids[0])["leaf_cluster"]["label"], "Diffusion")
        related = corpus.related_papers(self.ids[0])
        self.assertEqual([p["paper_id"] for p in related["papers"]], [self.ids[1]])
        self.assertIn("not similarity-ranked", related["relationship"])
        self.assertEqual(corpus.related_papers(self.ids[3])["papers"], [])

    def test_rejects_mismatched_cluster_snapshot(self):
        np.savez(self.root / "knn" / "cluster_umap10d_mcs15_ms5.npz",
                 ids=self.ids[:-1], labels=[7, 7, 8])
        with self.assertRaisesRegex(ValueError, "do not match"):
            PaperCorpus(self.root)


if __name__ == "__main__":
    unittest.main()
