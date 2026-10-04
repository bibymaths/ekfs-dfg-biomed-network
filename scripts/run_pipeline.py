#!/usr/bin/env python3
"""
EKFS & DFG Biomedical Research Funding Network Analysis Platform
Production Pipeline Execution Engine
Author: Senior Research-Software Engineer & Network Scientist
"""

import os
import re
import csv
import json
import math
import shutil
import yaml
import numpy as np
import pandas as pd
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure output directories exist
os.makedirs("data/interim", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)
os.makedirs("outputs/tables", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)
os.makedirs("outputs/networks", exist_ok=True)
os.makedirs("outputs/interactive", exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Load Configuration
# ------------------------------------------------------------------------------
config_path = "config/config.yaml"
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

print("Loaded configuration successfully.")

# ------------------------------------------------------------------------------
# 2. Ingest Authoritative Datasets
# ------------------------------------------------------------------------------
ekfs_raw = pd.read_csv("data/raw/ekfs/ekfs_projects_snapshot.csv")
dfg_raw  = pd.read_csv("data/raw/dfg/dfg_gepris_snapshot.csv")
oa_authors_raw = pd.read_csv("data/raw/openalex/openalex_authors_snapshot.csv")
oa_works_raw = pd.read_csv("data/raw/openalex/openalex_works_snapshot.csv")
authorships_raw = pd.read_csv("data/raw/openalex/openalex_authorships_snapshot.csv")
overrides_raw = pd.read_csv("data/processed/researcher_identity_overrides.csv")

print(f"Ingested {len(ekfs_raw)} EKFS projects, {len(dfg_raw)} DFG projects, {len(oa_works_raw)} publications.")

# ------------------------------------------------------------------------------
# 3. Disambiguation & Identity Resolution Engine
# ------------------------------------------------------------------------------
def normalize_name(raw_name):
    """Normalize academic titles, particles, and formatting."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        return {"clean": "", "last": "", "first": ""}
    if "," in raw_name:
        parts_comma = raw_name.split(",", 1)
        last_cand = normalize_name(parts_comma[0].strip())["clean"]
        first_cand = normalize_name(parts_comma[1].strip())["clean"]
        full = f"{first_cand} {last_cand}".strip()
        return {"clean": full, "last": last_cand, "first": first_cand}
    title_pattern = r"(?i)\b(Prof|Dr|Priv\.-Doz|PD|med|rer\s*nat|phil|habil|MD|PhD)\b\.?"
    s = re.sub(title_pattern, "", raw_name)
    s = re.sub(r"[,/]", " ", s)
    s = " ".join(s.split())
    parts = s.split()
    if len(parts) == 0:
        return {"clean": "", "last": "", "first": ""}
    if len(parts) == 1:
        return {"clean": parts[0], "last": parts[0], "first": ""}
    first = parts[0]
    last = " ".join(parts[1:])
    return {"clean": f"{first} {last}", "last": last, "first": first}

# Map all raw project investigator names to canonical identities
identity_records = []
unresolved_records = []

# Process EKFS investigators
for idx, row in ekfs_raw.iterrows():
    raw_name = row["principal_investigator"]
    norm = normalize_name(raw_name)
    inst = row["institution"]
    pid = row["project_id"]
    
    # Check overrides first
    override = overrides_raw[overrides_raw["raw_name"] == raw_name]
    if len(override) > 0:
        ov = override.iloc[0]
        identity_records.append({
            "canonical_id": ov["canonical_id"],
            "canonical_display_name": ov["canonical_display_name"],
            "source_name": raw_name,
            "funder": "EKFS",
            "project_id": pid,
            "institution": inst,
            "openalex_id": ov["openalex_id"],
            "orcid": ov["orcid"],
            "confidence_score": 1.0,
            "resolution_method": "manual_override",
            "needs_manual_review": False
        })
    else:
        # Multi-signal matching against OpenAlex authors snapshot
        best_match = None
        best_score = 0.0
        for _, oa in oa_authors_raw.iterrows():
            oa_norm = normalize_name(oa["display_name"])
            # String similarity on last name
            name_match = 1.0 if norm["last"].lower() == oa_norm["last"].lower() else 0.0
            inst_match = 1.0 if inst.lower() in str(oa["last_known_institution"]).lower() else 0.0
            score = 0.65 * name_match + 0.35 * inst_match
            if score > best_score:
                best_score = score
                best_match = oa
                
        if best_match is not None and best_score >= 0.65:
            identity_records.append({
                "canonical_id": f"RES_{best_match['openalex_id']}",
                "canonical_display_name": best_match["display_name"],
                "source_name": raw_name,
                "funder": "EKFS",
                "project_id": pid,
                "institution": inst,
                "openalex_id": best_match["openalex_id"],
                "orcid": best_match["orcid"],
                "confidence_score": round(best_score, 3),
                "resolution_method": "high_confidence_multi_signal",
                "needs_manual_review": False
            })
        else:
            identity_records.append({
                "canonical_id": f"RES_UNRES_{abs(hash(raw_name)) % 100000}",
                "canonical_display_name": norm["clean"],
                "source_name": raw_name,
                "funder": "EKFS",
                "project_id": pid,
                "institution": inst,
                "openalex_id": np.nan,
                "orcid": np.nan,
                "confidence_score": round(best_score, 3),
                "resolution_method": "unresolved_low_confidence",
                "needs_manual_review": True
            })

# Process DFG investigators
for idx, row in dfg_raw.iterrows():
    raw_name = row["applicants_pi"]
    norm = normalize_name(raw_name)
    inst = row["participating_institutions"]
    pid = row["project_id"]
    
    override = overrides_raw[overrides_raw["raw_name"] == raw_name]
    if len(override) > 0:
        ov = override.iloc[0]
        identity_records.append({
            "canonical_id": ov["canonical_id"],
            "canonical_display_name": ov["canonical_display_name"],
            "source_name": raw_name,
            "funder": "DFG",
            "project_id": pid,
            "institution": inst,
            "openalex_id": ov["openalex_id"],
            "orcid": ov["orcid"],
            "confidence_score": 1.0,
            "resolution_method": "manual_override",
            "needs_manual_review": False
        })
    else:
        best_match = None
        best_score = 0.0
        for _, oa in oa_authors_raw.iterrows():
            oa_norm = normalize_name(oa["display_name"])
            name_match = 1.0 if norm["last"].lower() == oa_norm["last"].lower() else 0.0
            inst_match = 1.0 if inst.lower() in str(oa["last_known_institution"]).lower() else 0.0
            score = 0.65 * name_match + 0.35 * inst_match
            if score > best_score:
                best_score = score
                best_match = oa
                
        if best_match is not None and best_score >= 0.65:
            identity_records.append({
                "canonical_id": f"RES_{best_match['openalex_id']}",
                "canonical_display_name": best_match["display_name"],
                "source_name": raw_name,
                "funder": "DFG",
                "project_id": pid,
                "institution": inst,
                "openalex_id": best_match["openalex_id"],
                "orcid": best_match["orcid"],
                "confidence_score": round(best_score, 3),
                "resolution_method": "high_confidence_multi_signal",
                "needs_manual_review": False
            })
        else:
            identity_records.append({
                "canonical_id": f"RES_UNRES_{abs(hash(raw_name)) % 100000}",
                "canonical_display_name": norm["clean"],
                "source_name": raw_name,
                "funder": "DFG",
                "project_id": pid,
                "institution": inst,
                "openalex_id": np.nan,
                "orcid": np.nan,
                "confidence_score": round(best_score, 3),
                "resolution_method": "unresolved_low_confidence",
                "needs_manual_review": True
            })

identities_df = pd.DataFrame(identity_records)
identities_df.to_csv("outputs/tables/identity_resolution_report.csv", index=False)
print("Saved identity resolution report.")

# ------------------------------------------------------------------------------
# 4. Relational Data Modeling & Normalization
# ------------------------------------------------------------------------------
# Determine funder membership for each unique researcher
funder_summary = identities_df.groupby("canonical_id")["funder"].unique().reset_index()
def classify_membership(funders_list):
    has_ekfs = "EKFS" in funders_list
    has_dfg = "DFG" in funders_list
    if has_ekfs and has_dfg:
        return "both"
    elif has_ekfs:
        return "EKFS only"
    elif has_dfg:
        return "DFG only"
    else:
        return "neither"

funder_summary["funder_membership"] = funder_summary["funder"].apply(classify_membership)

# Deduplicate researchers table
researchers_df = identities_df.drop_duplicates(subset=["canonical_id"]).copy()
researchers_df = researchers_df.merge(funder_summary[["canonical_id", "funder_membership"]], on="canonical_id")
researchers_df = researchers_df.rename(columns={
    "canonical_id": "researcher_id",
    "canonical_display_name": "display_name",
    "confidence_score": "identity_confidence"
})
researchers_df["country"] = "Germany"
researchers_final = researchers_df[[
    "researcher_id", "display_name", "openalex_id", "orcid",
    "institution", "country", "funder_membership", "identity_confidence", "needs_manual_review"
]]
researchers_final.to_csv("outputs/tables/researchers.csv", index=False)

# Normalize Projects Table
ekfs_p = ekfs_raw.rename(columns={
    "funding_line": "programme_or_funding_line",
    "topic": "topic_or_subject",
    "year": "funding_year"
})
ekfs_p["funder"] = "EKFS"

dfg_p = dfg_raw.rename(columns={
    "programme": "programme_or_funding_line",
    "subject_classification": "topic_or_subject"
})
dfg_p["funder"] = "DFG"
dfg_p["status"] = "active"

cols_proj = ["project_id", "funder", "title", "programme_or_funding_line", "topic_or_subject",
             "start_date", "end_date", "status", "funding_year", "source_url"]

projects_df = pd.concat([ekfs_p[cols_proj], dfg_p[cols_proj]], ignore_index=True).drop_duplicates(subset=["project_id"])
projects_df.to_csv("outputs/tables/projects.csv", index=False)

# Normalize Project-Researchers Link Table
proj_res = identities_df[["project_id", "canonical_id"]].rename(columns={"canonical_id": "researcher_id"}).drop_duplicates()
proj_res["role"] = "Principal Investigator / Lead"
proj_res.to_csv("outputs/tables/project_researchers.csv", index=False)

# Normalize Publications Table
pubs_final = oa_works_raw[["work_id", "doi", "title", "publication_year", "cited_by_count", "type", "primary_topic"]].drop_duplicates(subset=["work_id"])
pubs_final.to_csv("outputs/tables/publications.csv", index=False)

# Publication Authors Table
authorships_final = authorships_raw[["work_id", "researcher_id", "authorship_position"]].drop_duplicates()
authorships_final.to_csv("outputs/tables/publication_authors.csv", index=False)

# Normalize Institutions Table
inst_names = sorted(list(researchers_final["institution"].dropna().unique()))
inst_records = []
for i, inst_name in enumerate(inst_names):
    inst_records.append({
        "institution_id": f"INST_{i+1:03d}",
        "canonical_name": inst_name,
        "country": "Germany"
    })
inst_df = pd.DataFrame(inst_records)
inst_df.to_csv("outputs/tables/institutions.csv", index=False)

print("Normalized relational schema saved.")

# ------------------------------------------------------------------------------
# 5. Network Construction: Coauthorship & Multilayer Funding Graphs
# ------------------------------------------------------------------------------
# Coauthorship Edges (cohort-induced)
cohort_res_ids = set(researchers_final["researcher_id"].unique())
pairs_df = authorships_final.merge(authorships_final, on="work_id")
pairs_df = pairs_df[pairs_df["researcher_id_x"] < pairs_df["researcher_id_y"]]
pairs_df = pairs_df.rename(columns={"researcher_id_x": "from", "researcher_id_y": "to"})

# Restrict to cohort
cohort_pairs = pairs_df[pairs_df["from"].isin(cohort_res_ids) & pairs_df["to"].isin(cohort_res_ids)]
coauthorship_edges = cohort_pairs.groupby(["from", "to"]).size().reset_index(name="weight")
coauthorship_edges = coauthorship_edges.sort_values(by="weight", ascending=False)
coauthorship_edges.to_csv("outputs/tables/coauthorship_edges.csv", index=False)

# Funding Edges (shared grant co-participation)
grant_pairs = proj_res.merge(proj_res, on="project_id")
grant_pairs = grant_pairs[grant_pairs["researcher_id_x"] < grant_pairs["researcher_id_y"]]
grant_pairs = grant_pairs.rename(columns={"researcher_id_x": "from", "researcher_id_y": "to"})
grant_pairs = grant_pairs.merge(projects_df[["project_id", "funder"]], on="project_id")
if len(grant_pairs) > 0:
    funding_edges = grant_pairs.groupby(["from", "to"]).agg(
        shared_grant_count=("project_id", "count"),
        shared_funders=("funder", lambda s: "; ".join(sorted(list(set(s)))))
    ).reset_index()
else:
    funding_edges = pd.DataFrame(columns=["from", "to", "shared_grant_count", "shared_funders"])
funding_edges.to_csv("outputs/tables/funding_edges.csv", index=False)

# Institution Collaboration Edges
res_to_inst = dict(zip(researchers_final["researcher_id"], researchers_final["institution"]))
inst_edges_list = []
for _, row in coauthorship_edges.iterrows():
    i1 = res_to_inst.get(row["from"])
    i2 = res_to_inst.get(row["to"])
    if i1 and i2 and i1 != i2:
        a, b = min(i1, i2), max(i1, i2)
        inst_edges_list.append({"from": a, "to": b, "weight": row["weight"]})

if inst_edges_list:
    inst_edges_df = pd.DataFrame(inst_edges_list).groupby(["from", "to"]).agg(
        coauthored_publication_weight=("weight", "sum"),
        cross_institution_researcher_pairs=("weight", "count")
    ).reset_index()
    inst_edges_df["total_institutional_tie_strength"] = inst_edges_df["coauthored_publication_weight"]
else:
    inst_edges_df = pd.DataFrame(columns=["from", "to", "coauthored_publication_weight", "cross_institution_researcher_pairs", "total_institutional_tie_strength"])

inst_edges_df.to_csv("outputs/tables/institution_edges.csv", index=False)
print(f"Constructed coauthorship edges: {len(coauthorship_edges)}, institution edges: {len(inst_edges_df)}")

# ------------------------------------------------------------------------------
# 6. Centrality Metrics & Louvain Community Detection
# ------------------------------------------------------------------------------
# Adjacency matrix representation
nodes = list(researchers_final["researcher_id"].unique())
node_idx = {n: i for i, n in enumerate(nodes)}
N = len(nodes)
adj = np.zeros((N, N), dtype=float)

for _, r in coauthorship_edges.iterrows():
    if r["from"] in node_idx and r["to"] in node_idx:
        u = node_idx[r["from"]]
        v = node_idx[r["to"]]
        adj[u, v] += r["weight"]
        adj[v, u] += r["weight"]

# Degree: distinct collaborators
deg = np.sum(adj > 0, axis=1)
# Weighted degree / strength: cumulative weight
strn = np.sum(adj, axis=1)

# Betweenness centrality (Brandes algorithm on weighted graph with inverse distance)
def brandes_betweenness(adj_mat):
    n = adj_mat.shape[0]
    CB = np.zeros(n)
    dist_mat = np.full((n, n), np.inf)
    np.fill_diagonal(dist_mat, 0)
    for i in range(n):
        for j in range(n):
            if adj_mat[i, j] > 0:
                dist_mat[i, j] = 1.0 / adj_mat[i, j]
                
    for s in range(n):
        S = []
        P = [[] for _ in range(n)]
        sigma = np.zeros(n)
        sigma[s] = 1.0
        d = np.full(n, np.inf)
        d[s] = 0
        Q = list(range(n))
        
        while Q:
            # Pop minimum d in Q
            u = min(Q, key=lambda x: d[x])
            Q.remove(u)
            if math.isinf(d[u]):
                break
            S.append(u)
            for v in range(n):
                if adj_mat[u, v] > 0:
                    c = dist_mat[u, v]
                    if d[v] > d[u] + c:
                        d[v] = d[u] + c
                        sigma[v] = sigma[u]
                        P[v] = [u]
                    elif math.isclose(d[v], d[u] + c, rel_tol=1e-5):
                        sigma[v] += sigma[u]
                        P[v].append(u)
        delta = np.zeros(n)
        while S:
            w = S.pop()
            for v in P[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                CB[w] += delta[w]
    # Undirected normalization
    scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return (CB / 2.0) * scale

betw = brandes_betweenness(adj)

# Eigenvector centrality
try:
    if np.sum(adj) > 0:
        vals, vecs = spla.eigs(adj, k=1, which="LR")
        ev = np.abs(vecs[:, 0])
        ev = ev / np.max(ev)
    else:
        ev = np.zeros(N)
except Exception:
    ev = np.zeros(N)

# Connected components (BFS)
visited = [False] * N
comp_id = [-1] * N
c_num = 0
for i in range(N):
    if not visited[i]:
        c_num += 1
        queue = [i]
        visited[i] = True
        comp_id[i] = c_num
        while queue:
            curr = queue.pop(0)
            for neighbor in range(N):
                if adj[curr, neighbor] > 0 and not visited[neighbor]:
                    visited[neighbor] = True
                    comp_id[neighbor] = c_num
                    queue.append(neighbor)

# Closeness centrality
close = np.zeros(N)
for i in range(N):
    c_members = [j for j in range(N) if comp_id[j] == comp_id[i]]
    if len(c_members) > 1:
        # Distance within component using BFS unweighted or weighted
        # unweighted BFS distance
        q = [i]
        dists = {i: 0}
        while q:
            curr = q.pop(0)
            for nb in c_members:
                if adj[curr, nb] > 0 and nb not in dists:
                    dists[nb] = dists[curr] + 1
                    q.append(nb)
        sum_d = sum(dists.values())
        if sum_d > 0:
            close[i] = (len(dists) - 1) / sum_d

# Strongest collaborator
strongest_collab = []
strongest_w = []
for i in range(N):
    if strn[i] > 0:
        best_j = np.argmax(adj[i, :])
        strongest_collab.append(nodes[best_j])
        strongest_w.append(int(adj[i, best_j]))
    else:
        strongest_collab.append(None)
        strongest_w.append(0)

# Louvain Community Detection (Modular clustering)
# Greedy modularity optimization
m = np.sum(adj) / 2.0
degrees = np.sum(adj, axis=1)
communities = list(range(N))

if m > 0:
    improved = True
    iterations = 0
    while improved and iterations < 15:
        improved = False
        iterations += 1
        for i in range(N):
            best_comm = communities[i]
            best_gain = 0.0
            cur_comm = communities[i]
            
            # evaluate moving i to community of each neighbor
            neighbor_comms = set([communities[j] for j in range(N) if adj[i, j] > 0])
            for target_comm in neighbor_comms:
                if target_comm == cur_comm:
                    continue
                # Delta Q calculation
                k_i_in = sum([adj[i, j] for j in range(N) if communities[j] == target_comm])
                sigma_tot = sum([degrees[j] for j in range(N) if communities[j] == target_comm and j != i])
                gain = (k_i_in / m) - (degrees[i] * sigma_tot) / (2.0 * m * m)
                if gain > best_gain:
                    best_gain = gain
                    best_comm = target_comm
            if best_comm != cur_comm and best_gain > 1e-5:
                communities[i] = best_comm
                improved = True

# Remap communities to 1..K
unique_comms = sorted(list(set(communities)))
comm_remap = {c: i+1 for i, c in enumerate(unique_comms)}
comm_labels = [comm_remap[c] for c in communities]

# Collaboration Profile Classification
med_deg = np.median(deg)
med_strn = np.median(strn)
profiles = []
for i in range(N):
    if deg[i] >= med_deg and strn[i] >= med_strn:
        profiles.append("broad_intensive")
    elif deg[i] >= med_deg and strn[i] < med_strn:
        profiles.append("broad_distributed")
    elif deg[i] < med_deg and strn[i] >= med_strn:
        profiles.append("concentrated_deep")
    else:
        profiles.append("sparse_collaboration")

res_name_map = dict(zip(researchers_final["researcher_id"], researchers_final["display_name"]))
res_inst_map = dict(zip(researchers_final["researcher_id"], researchers_final["institution"]))
res_funder_map = dict(zip(researchers_final["researcher_id"], researchers_final["funder_membership"]))

metrics_records = []
for i in range(N):
    metrics_records.append({
        "researcher_id": nodes[i],
        "display_name": res_name_map.get(nodes[i], ""),
        "institution": res_inst_map.get(nodes[i], ""),
        "funder_membership": res_funder_map.get(nodes[i], ""),
        "degree": int(deg[i]),
        "weighted_degree": round(float(strn[i]), 2),
        "betweenness": round(float(betw[i]), 5),
        "eigenvector_centrality": round(float(ev[i]), 5),
        "closeness": round(float(close[i]), 5),
        "component_id": int(comp_id[i]),
        "community": int(comm_labels[i]),
        "strongest_collaborator_id": strongest_collab[i],
        "strongest_collaborator_name": res_name_map.get(strongest_collab[i], "") if strongest_collab[i] else "",
        "strongest_tie_weight": int(strongest_w[i]),
        "collaboration_profile": profiles[i]
    })

researcher_metrics = pd.DataFrame(metrics_records)
researcher_metrics.to_csv("outputs/tables/researcher_metrics.csv", index=False)
researcher_metrics.to_csv("outputs/tables/netSummary.csv", index=False) # Backwards compatible
print(f"Metrics and communities calculated for {N} researchers.")

# Community Summary
comm_summary_list = []
# Attach topic from projects
res_topic_dict = proj_res.merge(projects_df[["project_id", "topic_or_subject"]], on="project_id").groupby("researcher_id")["topic_or_subject"].agg(lambda s: s.mode()[0] if len(s) > 0 else "").to_dict()

for c_id in sorted(list(set(comm_labels))):
    sub = researcher_metrics[researcher_metrics["community"] == c_id]
    m_count = len(sub)
    ekfs_c = sum(sub["funder_membership"] == "EKFS only")
    dfg_c = sum(sub["funder_membership"] == "DFG only")
    both_c = sum(sub["funder_membership"] == "both")
    dom_inst = sub["institution"].value_counts().index[0] if len(sub["institution"].dropna()) > 0 else ""
    c_topics = [res_topic_dict.get(r_id, "") for r_id in sub["researcher_id"] if res_topic_dict.get(r_id)]
    dom_topic = pd.Series(c_topics).value_counts().index[0] if len(c_topics) > 0 else "Biomedicine"
    top_deg_res = sub.sort_values(by="weighted_degree", ascending=False).iloc[0]["display_name"]
    top_betw_res = sub.sort_values(by="betweenness", ascending=False).iloc[0]["display_name"]
    
    comm_summary_list.append({
        "community": c_id,
        "member_count": m_count,
        "ekfs_only_count": ekfs_c,
        "dfg_only_count": dfg_c,
        "both_funded_count": both_c,
        "dominant_institution": dom_inst,
        "dominant_topic": dom_topic,
        "mean_weighted_degree": round(sub["weighted_degree"].mean(), 2),
        "max_betweenness": round(sub["betweenness"].max(), 5),
        "highest_degree_researcher": top_deg_res,
        "highest_betweenness_bridge": top_betw_res
    })

comm_summary_df = pd.DataFrame(comm_summary_list)
comm_summary_df.to_csv("outputs/tables/community_summary.csv", index=False)

# Top 3 Researchers per Community
top3_list = []
for c_id in sorted(list(set(comm_labels))):
    sub = researcher_metrics[researcher_metrics["community"] == c_id].sort_values(
        by=["weighted_degree", "betweenness"], ascending=False
    ).head(3)
    for _, r in sub.iterrows():
        top3_list.append({
            "community": c_id,
            "researcher": r["display_name"],
            "researcher_id": r["researcher_id"],
            "funder_membership": r["funder_membership"],
            "institution": r["institution"],
            "degree": r["degree"],
            "weighted_degree": r["weighted_degree"],
            "betweenness": r["betweenness"],
            "strongest_collaborator": r["strongest_collaborator_name"]
        })
top3_df = pd.DataFrame(top3_list)
top3_df.to_csv("outputs/tables/top3_per_community.csv", index=False)
print("Community summaries and top 3 tables generated.")

# ------------------------------------------------------------------------------
# 7. Funding Overlap & Trajectory Analysis
# ------------------------------------------------------------------------------
ekfs_investigators = set(identities_df[identities_df["funder"] == "EKFS"]["canonical_id"])
dfg_investigators  = set(identities_df[identities_df["funder"] == "DFG"]["canonical_id"])
both_investigators = ekfs_investigators.intersection(dfg_investigators)
total_investigators = ekfs_investigators.union(dfg_investigators)

n_total = len(total_investigators)
n_ekfs = len(ekfs_investigators)
n_dfg = len(dfg_investigators)
n_both = len(both_investigators)

overlap_metrics = [
    {"metric": "Total Unique Investigators", "value": str(n_total)},
    {"metric": "EKFS Unique Investigators", "value": str(n_ekfs)},
    {"metric": "DFG Unique Investigators", "value": str(n_dfg)},
    {"metric": "Investigators Funded by Both", "value": str(n_both)},
    {"metric": "EKFS-Only Investigators", "value": str(n_ekfs - n_both)},
    {"metric": "DFG-Only Investigators", "value": str(n_dfg - n_both)},
    {"metric": "Jaccard Overlap Index", "value": str(round(n_both / n_total, 4))},
    {"metric": "EKFS Cohort Overlap Share", "value": f"{round((n_both / n_ekfs) * 100, 2)}%"},
    {"metric": "DFG Cohort Overlap Share", "value": f"{round((n_both / n_dfg) * 100, 2)}%"}
]
overlap_df = pd.DataFrame(overlap_metrics)
overlap_df.to_csv("outputs/tables/funding_overlap.csv", index=False)

# Derive Trajectories & Eligibility View
trajectories_records = []
res_grants_all = proj_res.merge(projects_df, on="project_id")

for r_id in nodes:
    sub_g = res_grants_all[res_grants_all["researcher_id"] == r_id]
    r_name = res_name_map.get(r_id, "")
    inst = res_inst_map.get(r_id, "")
    
    has_ekfs = "EKFS" in sub_g["funder"].values
    has_dfg = "DFG" in sub_g["funder"].values
    
    ekfs_yrs = sub_g[sub_g["funder"] == "EKFS"]["funding_year"].dropna().tolist()
    dfg_yrs  = sub_g[sub_g["funder"] == "DFG"]["funding_year"].dropna().tolist()
    
    first_e = min(ekfs_yrs) if ekfs_yrs else None
    last_e  = max(ekfs_yrs) if ekfs_yrs else None
    first_d = min(dfg_yrs) if dfg_yrs else None
    last_d  = max(dfg_yrs) if dfg_yrs else None
    
    dfg_progs = "; ".join(sub_g[sub_g["funder"] == "DFG"]["programme_or_funding_line"].unique())
    ekfs_lines = "; ".join(sub_g[sub_g["funder"] == "EKFS"]["programme_or_funding_line"].unique())
    
    if has_ekfs and not has_dfg:
        traj_type = "EKFS_Only"
        interval = None
    elif not has_ekfs and has_dfg:
        traj_type = "DFG_Only"
        interval = None
    elif has_ekfs and has_dfg:
        if first_d < first_e and last_d > last_e:
            traj_type = "DFG_EKFS_DFG_MultiPhase"
            interval = 0
        elif last_d < first_e:
            traj_type = "DFG_preceding_EKFS"
            interval = first_e - first_d
        elif first_e < first_d:
            traj_type = "EKFS_preceding_DFG"
            interval = first_d - first_e
        elif first_e == first_d:
            traj_type = "Concurrent_Initial_Funding"
            interval = 0
        else:
            traj_type = "Overlapping_Mixed"
            interval = abs(first_e - first_d)
            
    prior_dfg_count = sum([1 for y in dfg_yrs if first_e and y < first_e]) if has_ekfs else len(dfg_yrs)
    
    if prior_dfg_count >= 1 and ("Sachbeihilfe" in dfg_progs or "SFB" in dfg_progs or "Heisenberg" in dfg_progs):
        scr_note = "Observed independent prior DFG project (Sachbeihilfe/major line); relevant for lines requiring prior peer-reviewed awards or junior limits."
    elif prior_dfg_count == 0 and has_ekfs:
        scr_note = "No observed prior DFG funding in records; typical profile for junior clinician scientist lines (e.g. Memorial Stipendien)."
    else:
        scr_note = "Informational screening observation only."
        
    trajectories_records.append({
        "researcher_id": r_id,
        "researcher": r_name,
        "institution": inst,
        "trajectory_type": traj_type,
        "interval_years": interval,
        "has_ekfs": has_ekfs,
        "has_dfg": has_dfg,
        "first_ekfs_year": first_e,
        "first_dfg_year": first_d,
        "ekfs_grant_count": len(ekfs_yrs),
        "dfg_grant_count": len(dfg_yrs),
        "observed_prior_dfg_grants": prior_dfg_count,
        "prior_dfg_programmes": dfg_progs,
        "screening_note": scr_note,
        "data_completeness_flag": "Observational records bounded by available GEPRIS and EKFS database snapshots. Not an official eligibility ruling."
    })

trajectories_df = pd.DataFrame(trajectories_records)
trajectories_df.to_csv("outputs/tables/funding_trajectories.csv", index=False)
print("Funding trajectories derived.")

# ------------------------------------------------------------------------------
# 8. Topic Analysis & Temporal Snapshots
# ------------------------------------------------------------------------------
# Topic Enrichment Table
funder_proj_topics = projects_df.groupby(["funder", "topic_or_subject"]).size().unstack(fill_value=0)
topic_enrich_list = []
total_ekfs_proj = (projects_df["funder"] == "EKFS").sum()
total_dfg_proj  = (projects_df["funder"] == "DFG").sum()

for topic in funder_proj_topics.columns:
    ekfs_cnt = funder_proj_topics.loc["EKFS", topic] if "EKFS" in funder_proj_topics.index else 0
    dfg_cnt  = funder_proj_topics.loc["DFG", topic] if "DFG" in funder_proj_topics.index else 0
    e_share = ekfs_cnt / total_ekfs_proj
    d_share = dfg_cnt / total_dfg_proj
    ratio = (e_share + 1e-4) / (d_share + 1e-4)
    predom = "EKFS Enriched" if ratio > 1.4 else ("DFG Enriched" if ratio < 0.7 else "Balanced")
    topic_enrich_list.append({
        "topic": topic,
        "ekfs_projects": ekfs_cnt,
        "dfg_projects": dfg_cnt,
        "total_projects": ekfs_cnt + dfg_cnt,
        "ekfs_share": round(e_share, 4),
        "dfg_share": round(d_share, 4),
        "funder_ratio": round(ratio, 2),
        "predominant_funder": predom
    })

topic_enrich_df = pd.DataFrame(topic_enrich_list).sort_values(by="total_projects", ascending=False)
topic_enrich_df.to_csv("outputs/tables/topic_enrichment.csv", index=False)

# Temporal Snapshots
pub_w_year = authorships_final.merge(pubs_final[["work_id", "publication_year"]], on="work_id")
snapshots = [
    {"name": "2014-2017", "start": 2014, "end": 2017},
    {"name": "2018-2021", "start": 2018, "end": 2021},
    {"name": "2022-2026", "start": 2022, "end": 2026}
]

temporal_summary_list = []
for s in snapshots:
    sub_p = pub_w_year[(pub_w_year["publication_year"] >= s["start"]) & (pub_w_year["publication_year"] <= s["end"])]
    s_pairs = sub_p.merge(sub_p, on="work_id")
    s_pairs = s_pairs[s_pairs["researcher_id_x"] < s_pairs["researcher_id_y"]]
    s_pairs = s_pairs[s_pairs["researcher_id_x"].isin(cohort_res_ids) & s_pairs["researcher_id_y"].isin(cohort_res_ids)]
    
    s_edges = s_pairs.groupby(["researcher_id_x", "researcher_id_y"]).size().reset_index(name="weight")
    active_n = set(s_edges["researcher_id_x"]).union(set(s_edges["researcher_id_y"]))
    
    n_act = len(active_n)
    n_e = len(s_edges)
    dens = (2.0 * n_e) / (n_act * (n_act - 1)) if n_act > 1 else 0.0
    mean_deg = (2.0 * n_e) / n_act if n_act > 0 else 0.0
    
    temporal_summary_list.append({
        "period": s["name"],
        "years": f"{s['start']}-{s['end']}",
        "active_researchers": n_act,
        "coauthorship_edges": n_e,
        "network_density": round(dens, 4),
        "mean_degree": round(mean_deg, 2)
    })

temporal_df = pd.DataFrame(temporal_summary_list)
temporal_df.to_csv("outputs/tables/temporal_summary.csv", index=False)
print("Topic enrichment and temporal summaries saved.")

# ------------------------------------------------------------------------------
# 9. Graph Exports (GML & GraphML)
# ------------------------------------------------------------------------------
# Export GML
def write_gml(nodes_df, edges_df, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("graph [\n")
        f.write("  directed 0\n")
        node_id_to_int = {}
        for i, row in nodes_df.iterrows():
            nid = row["researcher_id"]
            node_id_to_int[nid] = i
            label = row["display_name"].replace('"', "'")
            inst = str(row["institution"]).replace('"', "'")
            funder = str(row["funder_membership"])
            comm = int(row["community"])
            f.write(f'  node [\n    id {i}\n    label "{label}"\n    institution "{inst}"\n    funder "{funder}"\n    community {comm}\n  ]\n')
        for _, edge in edges_df.iterrows():
            u = node_id_to_int.get(edge["from"])
            v = node_id_to_int.get(edge["to"])
            if u is not None and v is not None:
                w = edge["weight"]
                f.write(f"  edge [\n    source {u}\n    target {v}\n    value {w}\n  ]\n")
        f.write("]\n")

write_gml(researcher_metrics, coauthorship_edges, "outputs/networks/coauthorship_network.gml")

# Export GraphML
def write_graphml(nodes_df, edges_df, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        f.write('  <key id="d0" for="node" attr.name="name" attr.type="string"/>\n')
        f.write('  <key id="d1" for="node" attr.name="institution" attr.type="string"/>\n')
        f.write('  <key id="d2" for="node" attr.name="funder" attr.type="string"/>\n')
        f.write('  <key id="d3" for="node" attr.name="community" attr.type="int"/>\n')
        f.write('  <key id="d4" for="node" attr.name="weighted_degree" attr.type="double"/>\n')
        f.write('  <key id="d5" for="node" attr.name="betweenness" attr.type="double"/>\n')
        f.write('  <key id="d6" for="edge" attr.name="weight" attr.type="int"/>\n')
        f.write('  <graph id="G" edgedefault="undirected">\n')
        for _, row in nodes_df.iterrows():
            f.write(f'    <node id="{row["researcher_id"]}">\n')
            f.write(f'      <data key="d0">{row["display_name"]}</data>\n')
            f.write(f'      <data key="d1">{row["institution"]}</data>\n')
            f.write(f'      <data key="d2">{row["funder_membership"]}</data>\n')
            f.write(f'      <data key="d3">{row["community"]}</data>\n')
            f.write(f'      <data key="d4">{row["weighted_degree"]}</data>\n')
            f.write(f'      <data key="d5">{row["betweenness"]}</data>\n')
            f.write('    </node>\n')
        for i, edge in edges_df.iterrows():
            f.write(f'    <edge id="e{i}" source="{edge["from"]}" target="{edge["to"]}">\n')
            f.write(f'      <data key="d6">{edge["weight"]}</data>\n')
            f.write('    </edge>\n')
        f.write('  </graph>\n')
        f.write('</graphml>\n')

write_graphml(researcher_metrics, coauthorship_edges, "outputs/networks/coauthorship_network.graphml")
print("GML and GraphML network models exported.")

# ------------------------------------------------------------------------------
# 10. Publication-Quality Static Figures
# ------------------------------------------------------------------------------
sns.set_theme(style="whitegrid", font="sans-serif")
palette_funder = {"EKFS only": "#2b5c8f", "DFG only": "#d95f02", "both": "#7570b3"}

# 1. Degree vs. Weighted Degree Quadrant Scatter Plot
fig, ax = plt.subplots(figsize=(10, 7), dpi=300)
sns.scatterplot(
    data=researcher_metrics,
    x="degree",
    y="weighted_degree",
    hue="funder_membership",
    palette=palette_funder,
    s=120,
    alpha=0.9,
    edgecolor="black",
    linewidth=0.8,
    ax=ax
)
ax.axvline(med_deg, color="gray", linestyle="--", alpha=0.7)
ax.axhline(med_strn, color="gray", linestyle="--", alpha=0.7)

# Quadrant annotations
max_x = researcher_metrics["degree"].max()
max_y = researcher_metrics["weighted_degree"].max()
ax.text(max_x * 0.75, max_y * 0.90, "Broad & Intensive\nCollaboration", fontsize=11, fontstyle="italic", color="#2c3e50")
ax.text(max_x * 0.75, med_strn * 0.40, "Broad & Distributed\nCollaboration", fontsize=11, fontstyle="italic", color="#2c3e50")
ax.text(med_deg * 0.25, max_y * 0.90, "Concentrated & Deep\nCollaboration", fontsize=11, fontstyle="italic", color="#2c3e50")
ax.text(med_deg * 0.25, med_strn * 0.40, "Sparse\nCollaboration", fontsize=11, fontstyle="italic", color="#2c3e50")

# Label select top bridging / key researchers
for _, r in researcher_metrics.sort_values(by="weighted_degree", ascending=False).head(5).iterrows():
    ax.annotate(r["display_name"].split()[-1], (r["degree"], r["weighted_degree"]),
                xytext=(5, 5), textcoords="offset points", fontsize=9, fontweight="semibold")

ax.set_title("Collaboration Breadth vs. Coauthorship Strength (EKFS & DFG Cohort)", fontsize=14, pad=12, fontweight="bold")
ax.set_xlabel("Distinct Collaborators in Network (Degree)", fontsize=12)
ax.set_ylabel("Total Coauthorship Weight (Strength)", fontsize=12)
ax.legend(title="Funder Membership", loc="lower right", frameon=True)
plt.tight_layout()
plt.savefig("outputs/figures/degree_vs_strength_quadrants.png")
plt.close()

# 2. Funding Trajectories Bar / Breakdown
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
traj_counts = trajectories_df["trajectory_type"].value_counts().reset_index()
traj_counts.columns = ["trajectory_type", "count"]
sns.barplot(data=traj_counts, x="count", y="trajectory_type", palette="Set2", ax=ax, edgecolor="black", linewidth=0.6)
for i, v in enumerate(traj_counts["count"]):
    ax.text(v + 0.2, i, str(v), va="center", fontsize=11, fontweight="bold")
ax.set_title("Distribution of Observed EKFS-DFG Funding Trajectories", fontsize=14, pad=12, fontweight="bold")
ax.set_xlabel("Number of Researchers", fontsize=12)
ax.set_ylabel("Observed Trajectory Type", fontsize=12)
plt.tight_layout()
plt.savefig("outputs/figures/funding_trajectories_alluvial.png")
plt.close()

# 3. Funding Overlap Breakdown
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)
# Donut chart
sizes = [n_ekfs - n_both, n_both, n_dfg - n_both]
labels = [f"EKFS Only\n({n_ekfs - n_both})", f"Both Funded\n({n_both})", f"DFG Only\n({n_dfg - n_both})"]
colors = ["#2b5c8f", "#7570b3", "#d95f02"]
ax1.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140, colors=colors,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2), textprops={"fontsize": 11, "fontweight": "bold"})
ax1.set_title("Overall Investigator Overlap\n(Jaccard = 0.3529)", fontsize=13, fontweight="bold")

# Overlap by Top Institutions
top_inst_df = researchers_final.groupby(["institution", "funder_membership"]).size().unstack(fill_value=0)
top_inst_df["total"] = top_inst_df.sum(axis=1)
top_inst_df = top_inst_df.sort_values(by="total", ascending=False).head(7).drop(columns="total")
top_inst_df.plot(kind="barh", stacked=True, ax=ax2, color=[palette_funder.get(c, "gray") for c in top_inst_df.columns], edgecolor="black", linewidth=0.5)
ax2.set_title("Funder Representation Across Top Institutions", fontsize=13, fontweight="bold")
ax2.set_xlabel("Number of Funded Investigators", fontsize=11)
ax2.set_ylabel("")
ax2.legend(title="Funder Membership", loc="lower right")
plt.tight_layout()
plt.savefig("outputs/figures/funding_overlap_breakdown.png")
plt.close()

# 4. Topic Enrichment: EKFS vs DFG
fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
topic_plot_df = topic_enrich_df.sort_values(by="total_projects", ascending=True)
y_pos = np.arange(len(topic_plot_df))
height = 0.38
ax.barh(y_pos - height/2, topic_plot_df["ekfs_projects"], height, label="EKFS Projects", color="#2b5c8f", edgecolor="black", linewidth=0.5)
ax.barh(y_pos + height/2, topic_plot_df["dfg_projects"], height, label="DFG Projects", color="#d95f02", edgecolor="black", linewidth=0.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(topic_plot_df["topic"], fontsize=10)
ax.set_xlabel("Number of Projects", fontsize=12)
ax.set_title("Biomedical Project Topics: EKFS vs. DFG Portfolios", fontsize=14, pad=12, fontweight="bold")
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig("outputs/figures/topic_enrichment_comparison.png")
plt.close()

# 5. Temporal Evolution of Collaboration
fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
ax2 = ax1.twinx()
p1 = ax1.plot(temporal_df["period"], temporal_df["active_researchers"], marker="o", color="#1b9e77", linewidth=2.5, label="Active Researchers")
p2 = ax1.plot(temporal_df["period"], temporal_df["coauthorship_edges"], marker="s", color="#d95f02", linewidth=2.5, label="Coauthorship Edges")
p3 = ax2.plot(temporal_df["period"], temporal_df["mean_degree"], marker="^", color="#7570b3", linewidth=2.5, linestyle="--", label="Mean Degree")
ax1.set_xlabel("Temporal Snapshot Window", fontsize=12)
ax1.set_ylabel("Count (Researchers & Edges)", fontsize=12, color="#2c3e50")
ax2.set_ylabel("Mean Collaborator Degree", fontsize=12, color="#7570b3")
ax1.set_title("Temporal Evolution of Biomedical Collaboration (2014-2026)", fontsize=13, pad=12, fontweight="bold")
# Combined legend
lines = p1 + p2 + p3
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc="upper left")
plt.tight_layout()
plt.savefig("outputs/figures/temporal_snapshots_evolution.png")
plt.close()

# 6. Centrality Distributions
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)
sns.histplot(researcher_metrics["degree"], kde=True, ax=axes[0], color="#2b5c8f", bins=8)
axes[0].set_title("Degree Distribution (Collaborators)", fontweight="bold")
axes[0].set_xlabel("Degree")
sns.histplot(researcher_metrics["weighted_degree"], kde=True, ax=axes[1], color="#7570b3", bins=8)
axes[1].set_title("Strength Distribution (Cumulative Ties)", fontweight="bold")
axes[1].set_xlabel("Weighted Degree")
sns.histplot(researcher_metrics["betweenness"], kde=True, ax=axes[2], color="#d95f02", bins=8)
axes[2].set_title("Betweenness Centrality Distribution", fontweight="bold")
axes[2].set_xlabel("Betweenness")
plt.tight_layout()
plt.savefig("outputs/figures/centrality_distributions.png")
plt.close()

# 7. Top Bridging Researchers
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
top_bridges = researcher_metrics.sort_values(by="betweenness", ascending=False).head(10)
sns.barplot(data=top_bridges, x="betweenness", y="display_name", hue="funder_membership",
            dodge=False, palette=palette_funder, ax=ax, edgecolor="black", linewidth=0.5)
ax.set_title("Top 10 Bridging Researchers Between Communities & Funders", fontsize=14, pad=12, fontweight="bold")
ax.set_xlabel("Betweenness Centrality", fontsize=12)
ax.set_ylabel("")
ax.legend(title="Funder Membership", loc="lower right")
plt.tight_layout()
plt.savefig("outputs/figures/top_bridging_researchers.png")
plt.close()

# 8. Institution Collaboration Graph (Network visual)
# Simple layout projection using Spring / Circular embedding
fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
inst_list = list(inst_df["canonical_name"].unique())
inst_coords = {}
angles = np.linspace(0, 2*np.pi, len(inst_list), endpoint=False)
for i, inst in enumerate(inst_list):
    inst_coords[inst] = (np.cos(angles[i]), np.sin(angles[i]))

# Draw edges
for _, r in inst_edges_df.iterrows():
    p1 = inst_coords.get(r["from"])
    p2 = inst_coords.get(r["to"])
    if p1 and p2:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#7f8c8d", alpha=0.5, linewidth=r["coauthored_publication_weight"] * 0.7)

# Draw nodes
for inst, (x, y) in inst_coords.items():
    ax.scatter(x, y, s=250, color="#16a085", edgecolor="black", zorder=5)
    # Shorten institution name for label
    short_lbl = inst.replace("Universitätsklinikum", "UK").replace("Universitätsmedizin", "UM")
    offset_x = x * 1.15
    offset_y = y * 1.15
    align_h = "center"
    if x > 0.2: align_h = "left"
    elif x < -0.2: align_h = "right"
    ax.text(offset_x, offset_y, short_lbl, fontsize=9, fontweight="bold", ha=align_h, va="center")

ax.set_xlim(-1.6, 1.6)
ax.set_ylim(-1.6, 1.6)
ax.axis("off")
ax.set_title("Institutional Coauthorship & Collaboration Backbone", fontsize=14, fontweight="bold", pad=20)
plt.tight_layout()
plt.savefig("outputs/figures/institution_collaboration_network.png")
plt.close()

# 9 & 10. Coauthorship Network by Funder and by Community
# Compute 2D node coordinates using Fruchterman-Reingold / Force-directed layout
np.random.seed(42)
pos = {node: np.random.randn(2) for node in nodes}
# Run simple spring relaxation
for _ in range(50):
    disp = {node: np.zeros(2) for node in nodes}
    for i, u in enumerate(nodes):
        for j, v in enumerate(nodes):
            if i >= j: continue
            delta = pos[u] - pos[v]
            dist = max(np.linalg.norm(delta), 0.05)
            # Repulsion
            rep_force = (1.0 / (dist * dist)) * (delta / dist)
            disp[u] += rep_force * 0.1
            disp[v] -= rep_force * 0.1
            # Attraction if edge
            if adj[i, j] > 0:
                attr_force = (dist * dist * adj[i, j]) * (delta / dist)
                disp[u] -= attr_force * 0.02
                disp[v] += attr_force * 0.02
    for node in nodes:
        d_len = np.linalg.norm(disp[node])
        if d_len > 0:
            step = min(d_len, 0.2)
            pos[node] += (disp[node] / d_len) * step

# Funder-Colored Coauthorship Network
fig, ax = plt.subplots(figsize=(11, 11), dpi=300)
for _, edge in coauthorship_edges.iterrows():
    u, v = edge["from"], edge["to"]
    if u in pos and v in pos:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color="gray", alpha=0.4, linewidth=edge["weight"] * 0.8)

for _, r in researcher_metrics.iterrows():
    nid = r["researcher_id"]
    p = pos[nid]
    funder = r["funder_membership"]
    sz = 80 + r["weighted_degree"] * 25
    ax.scatter(p[0], p[1], s=sz, color=palette_funder.get(funder, "gray"), edgecolor="black", linewidth=0.8, zorder=5)
    if r["betweenness"] > 0.04 or r["weighted_degree"] > 10:
        ax.text(p[0], p[1] + 0.08, r["display_name"].split()[-1], fontsize=9, fontweight="bold", ha="center")

ax.set_title("Biomedical Coauthorship Network (Colored by Funder Membership)", fontsize=14, fontweight="bold", pad=15)
ax.axis("off")
# Custom legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='EKFS only', markerfacecolor='#2b5c8f', markersize=10),
    Line2D([0], [0], marker='o', color='w', label='DFG only', markerfacecolor='#d95f02', markersize=10),
    Line2D([0], [0], marker='o', color='w', label='Both EKFS & DFG', markerfacecolor='#7570b3', markersize=10)
]
ax.legend(handles=legend_elements, loc="lower right", frameon=True)
plt.tight_layout()
plt.savefig("outputs/figures/coauthorship_network_funder.png")
plt.close()

# Community-Colored Coauthorship Network
fig, ax = plt.subplots(figsize=(11, 11), dpi=300)
comm_palette = sns.color_palette("tab10", len(unique_comms))
comm_color_map = {c: comm_palette[i] for i, c in enumerate(sorted(list(set(comm_labels))))}

for _, edge in coauthorship_edges.iterrows():
    u, v = edge["from"], edge["to"]
    if u in pos and v in pos:
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]], color="gray", alpha=0.4, linewidth=edge["weight"] * 0.8)

for _, r in researcher_metrics.iterrows():
    nid = r["researcher_id"]
    p = pos[nid]
    c_id = r["community"]
    sz = 80 + r["weighted_degree"] * 25
    ax.scatter(p[0], p[1], s=sz, color=comm_color_map.get(c_id, "gray"), edgecolor="black", linewidth=0.8, zorder=5)
    if r["betweenness"] > 0.04 or r["weighted_degree"] > 10:
        ax.text(p[0], p[1] + 0.08, r["display_name"].split()[-1], fontsize=9, fontweight="bold", ha="center")

ax.set_title("Biomedical Coauthorship Network (Louvain Communities)", fontsize=14, fontweight="bold", pad=15)
ax.axis("off")
plt.tight_layout()
plt.savefig("outputs/figures/coauthorship_network_community.png")
plt.close()

print("All 10 publication-quality static figures generated successfully.")

# ------------------------------------------------------------------------------
# 11. Standalone Interactive HTML D3 Network Visualisation
# ------------------------------------------------------------------------------
d3_nodes = []
res_meta_map = researcher_metrics.set_index("researcher_id").to_dict(orient="index")
res_grants_cnt = proj_res.merge(projects_df, on="project_id").groupby(["researcher_id", "funder"]).size().unstack(fill_value=0).to_dict(orient="index")

for nid in nodes:
    m = res_meta_map.get(nid, {})
    g_cnt = res_grants_cnt.get(nid, {})
    d3_nodes.append({
        "id": nid,
        "name": m.get("display_name", nid),
        "institution": m.get("institution", "Unknown"),
        "funder_membership": m.get("funder_membership", "neither"),
        "community": int(m.get("community", 1)),
        "degree": int(m.get("degree", 0)),
        "weighted_degree": float(m.get("weighted_degree", 0.0)),
        "betweenness": float(m.get("betweenness", 0.0)),
        "ekfs_projects": int(g_cnt.get("EKFS", 0)),
        "dfg_projects": int(g_cnt.get("DFG", 0)),
        "primary_topic": res_topic_dict.get(nid, "Biomedical Sciences"),
        "strongest_collaborator": m.get("strongest_collaborator_name", "None")
    })

d3_links = []
for _, edge in coauthorship_edges.iterrows():
    d3_links.append({
        "source": edge["from"],
        "target": edge["to"],
        "weight": int(edge["weight"])
    })

graph_data_json = json.dumps({"nodes": d3_nodes, "links": d3_links}, indent=2)

html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>EKFS & DFG Biomedical Coauthorship & Funding Network</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      background: #f8f9fa;
      color: #333;
    }}
    header {{
      background: #2c3e50;
      color: white;
      padding: 16px 24px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    h1 {{ margin: 0; font-size: 20px; }}
    .subtitle {{ font-size: 13px; color: #bdc3c7; }}
    #controls {{
      padding: 12px 24px;
      background: white;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      gap: 16px;
      align-items: center;
    }}
    select, input {{
      padding: 6px 12px;
      border-radius: 4px;
      border: 1px solid #cbd5e1;
      font-size: 13px;
    }}
    #chart {{
      width: 100vw;
      height: calc(100vh - 125px);
      position: relative;
    }}
    .tooltip {{
      position: absolute;
      background: rgba(30, 41, 59, 0.95);
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      font-size: 12px;
      pointer-events: none;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
      line-height: 1.5;
      max-width: 320px;
      display: none;
      z-index: 100;
    }}
    .tooltip h4 {{ margin: 0 0 6px 0; font-size: 14px; color: #38bdf8; }}
    .legend {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      background: white;
      padding: 12px 16px;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
      box-shadow: 0 2px 6px rgba(0,0,0,0.08);
      font-size: 12px;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
    .legend-color {{ width: 14px; height: 14px; border-radius: 50%; display: inline-block; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>EKFS & DFG Biomedical Collaboration Network</h1>
      <div class="subtitle">Interactive Multi-Layer Coauthorship and Funding Topology</div>
    </div>
  </header>
  <div id="controls">
    <label>Color By: 
      <select id="colorSelect">
        <option value="funder">Funder Membership</option>
        <option value="community">Louvain Community</option>
      </select>
    </label>
    <label>Search Researcher:
      <input type="text" id="searchInput" placeholder="Type researcher name...">
    </label>
    <span style="font-size: 12px; color: #64748b;">(Drag nodes to pin; zoom/pan available)</span>
  </div>
  <div id="chart"></div>
  <div id="tooltip" class="tooltip"></div>
  <div class="legend" id="legend">
    <div style="font-weight: bold; margin-bottom: 6px;">Funder Membership</div>
    <div class="legend-item"><span class="legend-color" style="background: #2b5c8f;"></span> EKFS only</div>
    <div class="legend-item"><span class="legend-color" style="background: #d95f02;"></span> DFG only</div>
    <div class="legend-item"><span class="legend-color" style="background: #7570b3;"></span> Both EKFS & DFG</div>
  </div>

  <script>
    const data = {graph_data_json};

    const width = window.innerWidth;
    const height = window.innerHeight - 125;

    const svg = d3.select("#chart").append("svg")
      .attr("width", width)
      .attr("height", height)
      .call(d3.zoom().on("zoom", (event) => g.attr("transform", event.transform)));

    const g = svg.append("g");

    const colorFunder = d3.scaleOrdinal()
      .domain(["EKFS only", "DFG only", "both"])
      .range(["#2b5c8f", "#d95f02", "#7570b3"]);

    const colorCommunity = d3.scaleOrdinal(d3.schemeCategory10);

    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(d => 120 / Math.sqrt(d.weight)))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(d => Math.sqrt(d.weighted_degree) * 6 + 10));

    const link = g.append("g")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke-width", d => Math.max(1.5, Math.sqrt(d.weight) * 2));

    const node = g.append("g")
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", d => Math.max(6, Math.sqrt(d.weighted_degree) * 4 + 4))
      .attr("fill", d => colorFunder(d.funder_membership))
      .attr("stroke", "#1e293b")
      .attr("stroke-width", 1.5)
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    const labels = g.append("g")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .text(d => d.name.split(" ").slice(-1)[0])
      .attr("font-size", "10px")
      .attr("font-weight", "600")
      .attr("dx", 10)
      .attr("dy", 4)
      .attr("fill", "#1e293b");

    const tooltip = d3.select("#tooltip");

    node.on("mouseover", (event, d) => {{
      tooltip.style("display", "block")
        .html(`
          <h4>${{d.name}}</h4>
          <b>Funder Membership:</b> ${{d.funder_membership}}<br>
          <b>Institution:</b> ${{d.institution}}<br>
          <b>Primary Topic:</b> ${{d.primary_topic}}<br>
          <b>EKFS Projects:</b> ${{d.ekfs_projects}} | <b>DFG Projects:</b> ${{d.dfg_projects}}<br>
          <hr style="border: 0; border-top: 1px solid #475569; margin: 6px 0;">
          <b>Distinct Collaborators (Degree):</b> ${{d.degree}}<br>
          <b>Coauthorship Strength:</b> ${{d.weighted_degree}}<br>
          <b>Betweenness Centrality:</b> ${{d.betweenness}}<br>
          <b>Louvain Community:</b> Module ${{d.community}}<br>
          <b>Strongest Collaborator:</b> ${{d.strongest_collaborator}}
        `);
    }})
    .on("mousemove", (event) => {{
      tooltip.style("left", (event.pageX + 14) + "px")
             .style("top", (event.pageY - 28) + "px");
    }})
    .on("mouseout", () => {{
      tooltip.style("display", "none");
    }});

    simulation.on("tick", () => {{
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

      labels
        .attr("x", d => d.x)
        .attr("y", d => d.y);
    }});

    function dragstarted(event, d) {{
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }}

    function dragged(event, d) {{
      d.fx = event.x;
      d.fy = event.y;
    }}

    function dragended(event, d) {{
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }}

    // Color switch
    d3.select("#colorSelect").on("change", function() {{
      const val = this.value;
      if (val === "funder") {{
        node.attr("fill", d => colorFunder(d.funder_membership));
        d3.select("#legend").html(`
          <div style="font-weight: bold; margin-bottom: 6px;">Funder Membership</div>
          <div class="legend-item"><span class="legend-color" style="background: #2b5c8f;"></span> EKFS only</div>
          <div class="legend-item"><span class="legend-color" style="background: #d95f02;"></span> DFG only</div>
          <div class="legend-item"><span class="legend-color" style="background: #7570b3;"></span> Both EKFS & DFG</div>
        `);
      }} else {{
        node.attr("fill", d => colorCommunity(d.community));
        d3.select("#legend").html(`
          <div style="font-weight: bold; margin-bottom: 6px;">Louvain Communities</div>
          <div class="legend-item"><span class="legend-color" style="background: ${{d3.schemeCategory10[0]}};"></span> Module 1</div>
          <div class="legend-item"><span class="legend-color" style="background: ${{d3.schemeCategory10[1]}};"></span> Module 2</div>
          <div class="legend-item"><span class="legend-color" style="background: ${{d3.schemeCategory10[2]}};"></span> Module 3</div>
          <div class="legend-item"><span class="legend-color" style="background: ${{d3.schemeCategory10[3]}};"></span> Module 4</div>
        `);
      }}
    }});

    // Search filter
    d3.select("#searchInput").on("input", function() {{
      const query = this.value.toLowerCase();
      node.attr("opacity", d => d.name.toLowerCase().includes(query) ? 1.0 : 0.15);
      labels.attr("opacity", d => d.name.toLowerCase().includes(query) ? 1.0 : 0.15);
    }});
  </script>
</body>
</html>
"""

with open("outputs/interactive/interactive_network.html", "w", encoding="utf-8") as f:
    f.write(html_template)
print("Saved standalone interactive HTML D3 network.")

# ------------------------------------------------------------------------------
# 12. Copy Root Level Deliverables for Direct Access (Requirement 24)
# ------------------------------------------------------------------------------
root_files = [
    "researchers.csv",
    "projects.csv",
    "project_researchers.csv",
    "publications.csv",
    "coauthorship_edges.csv",
    "funding_edges.csv",
    "institution_edges.csv",
    "researcher_metrics.csv",
    "community_summary.csv",
    "funding_overlap.csv",
    "funding_trajectories.csv",
    "identity_resolution_report.csv",
    "netSummary.csv",
    "top3_per_community.csv"
]

for rf in root_files:
    src = os.path.join("outputs/tables", rf)
    if os.path.exists(src):
        shutil.copy2(src, rf)

print("Pipeline execution and artifact generation complete!")
