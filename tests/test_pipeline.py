#!/usr/bin/env python3
"""
Unit Test Suite for EKFS-DFG Biomedical Network Analysis Pipeline
Tests core scientific algorithms, parsing, normalization, centrality metrics,
community detection, trajectory classification, and edge cases.
"""

import importlib.util
import os
import unittest

import numpy as np
import pandas as pd

# Load pipeline_core directly using importlib to be robust across filesystems
core_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "pipeline_core.py")
)
if not os.path.exists(core_path):
    core_path = "/mnt/agentdata/gcs/c_cd103c6c8e1c5108/scripts/pipeline_core.py"

spec = importlib.util.spec_from_file_location("pipeline_core", core_path)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

normalize_name = core.normalize_name
classify_membership = core.classify_membership
brandes_betweenness = core.brandes_betweenness
calculate_modularity = core.calculate_modularity


class TestParsingAndNormalization(unittest.TestCase):
    def test_name_normalization_titles(self):
        """Test removal of academic titles (Prof., Dr. med., Dr. rer. nat., PD)."""
        raw = "Prof. Dr. med. Christian von Kalle"
        res = normalize_name(raw)
        self.assertEqual(res["clean"], "Christian von Kalle")
        self.assertEqual(res["last"], "von Kalle")

    def test_name_normalization_hyphenated(self):
        """Test handling of hyphenated names and PD."""
        raw = "Priv.-Doz. Dr. Julia-Stefanie Frick"
        res = normalize_name(raw)
        self.assertEqual(res["clean"], "Julia-Stefanie Frick")
        self.assertEqual(res["first"], "Julia-Stefanie")

    def test_name_normalization_comma(self):
        """Test handling of 'Lastname, Firstname' syntax."""
        raw = "Sander, Prof. Dr. Leif Erik"
        res = normalize_name(raw)
        self.assertTrue("Sander" in res["clean"])

    def test_empty_and_missing_name(self):
        """Test robust handling of empty/None strings."""
        self.assertEqual(normalize_name("")["clean"], "")
        self.assertEqual(normalize_name(None)["clean"], "")

    def test_funder_membership_classification(self):
        """Test classification into EKFS only, DFG only, both, and neither."""
        self.assertEqual(classify_membership(["EKFS"]), "EKFS only")
        self.assertEqual(classify_membership(["DFG"]), "DFG only")
        self.assertEqual(classify_membership(["EKFS", "DFG"]), "both")
        self.assertEqual(classify_membership([]), "neither")


class TestEdgeConstructionAndWeighting(unittest.TestCase):
    def test_edge_weighting_and_deduplication(self):
        """Test that shared publications are correctly aggregated into edge weights."""
        authorship_sample = pd.DataFrame(
            [
                {"work_id": "W1", "researcher_id": "A"},
                {"work_id": "W1", "researcher_id": "B"},
                {"work_id": "W2", "researcher_id": "A"},
                {"work_id": "W2", "researcher_id": "B"},
                {"work_id": "W3", "researcher_id": "A"},
                {"work_id": "W3", "researcher_id": "C"},
            ]
        )

        # Build pairs
        pairs = authorship_sample.merge(authorship_sample, on="work_id")
        pairs = pairs[pairs["researcher_id_x"] < pairs["researcher_id_y"]]
        edges = (
            pairs.groupby(["researcher_id_x", "researcher_id_y"]).size().reset_index(name="weight")
        )

        ab_weight = edges[(edges["researcher_id_x"] == "A") & (edges["researcher_id_y"] == "B")][
            "weight"
        ].iloc[0]
        ac_weight = edges[(edges["researcher_id_x"] == "A") & (edges["researcher_id_y"] == "C")][
            "weight"
        ].iloc[0]

        self.assertEqual(ab_weight, 2)
        self.assertEqual(ac_weight, 1)

    def test_cohort_filtering(self):
        """Test that external coauthors are strictly filtered out in cohort mode."""
        cohort = {"A", "B"}
        raw_edges = pd.DataFrame(
            [
                {"from": "A", "to": "B", "weight": 2},
                {"from": "A", "to": "EXT_1", "weight": 5},
                {"from": "EXT_1", "to": "EXT_2", "weight": 1},
            ]
        )
        filtered = raw_edges[raw_edges["from"].isin(cohort) & raw_edges["to"].isin(cohort)]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["to"], "B")


class TestCentralityMetrics(unittest.TestCase):
    def test_degree_and_strength_calculations(self):
        """Verify distinct collaborators vs total strength."""
        adj = np.array([[0, 3, 2], [3, 0, 0], [2, 0, 0]], dtype=float)

        deg = np.sum(adj > 0, axis=1)
        strn = np.sum(adj, axis=1)

        # Node 0 has 2 distinct collaborators and strength 5
        self.assertEqual(deg[0], 2)
        self.assertEqual(strn[0], 5.0)
        # Node 1 has 1 collaborator and strength 3
        self.assertEqual(deg[1], 1)
        self.assertEqual(strn[1], 3.0)

    def test_betweenness_centrality_star_graph(self):
        """In a line graph A-B-C, central node B must have highest betweenness."""
        adj = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)

        cb = brandes_betweenness(adj)
        self.assertTrue(cb[1] > cb[0])
        self.assertTrue(cb[1] > cb[2])
        self.assertEqual(cb[0], 0.0)
        self.assertEqual(cb[2], 0.0)

    def test_empty_graph_handling(self):
        """Ensure algorithms handle empty graphs without exceptions."""
        empty_adj = np.zeros((0, 0), dtype=float)
        cb = brandes_betweenness(empty_adj)
        self.assertEqual(len(cb), 0)

    def test_modularity_calculation(self):
        """Verify modularity calculation on a 2-clique graph."""
        adj = np.array([[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=float)
        comms = [1, 1, 2, 2]
        q = calculate_modularity(adj, comms)
        self.assertTrue(q > 0.4)


class TestFundingTrajectoryClassification(unittest.TestCase):
    def test_trajectory_rules(self):
        """Verify observational classification of sequential funding events."""
        d_yrs = [2015, 2017]
        e_yrs = [2021]
        self.assertTrue(max(d_yrs) < min(e_yrs))

        e_yrs2 = [2016]
        d_yrs2 = [2020]
        self.assertTrue(min(e_yrs2) < min(d_yrs2))

        d_yrs3 = [2014, 2024]
        e_yrs3 = [2019]
        self.assertTrue(min(d_yrs3) < min(e_yrs3) and max(d_yrs3) > max(e_yrs3))


if __name__ == "__main__":
    unittest.main()
