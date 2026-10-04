"""
Core Functional Logic and Scientific Algorithms for EKFS-DFG Pipeline
"""

import re
import math
import numpy as np
import pandas as pd

def normalize_name(raw_name):
    """Normalize academic titles, particles, and formatting."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        return {"clean": "", "last": "", "first": ""}
    # Handle "Lastname, Firstname" format first
    if "," in raw_name:
        parts_comma = raw_name.split(",", 1)
        last_cand = normalize_name(parts_comma[0].strip())["clean"]
        first_cand = normalize_name(parts_comma[1].strip())["clean"]
        full = f"{first_cand} {last_cand}".strip()
        return {"clean": full, "last": last_cand, "first": first_cand}

    # Strip academic titles robustly
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

def classify_membership(funders_list):
    """Classify researcher by grant support."""
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

def brandes_betweenness(adj_mat):
    """Compute Brandes betweenness centrality on weighted adjacency matrix."""
    n = adj_mat.shape[0]
    if n == 0:
        return np.zeros(0)
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
    scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return (CB / 2.0) * scale

def calculate_modularity(adj, communities):
    """Calculate Newman-Girvan modularity Q."""
    m = np.sum(adj) / 2.0
    if m == 0:
        return 0.0
    degrees = np.sum(adj, axis=1)
    n = len(degrees)
    q = 0.0
    for i in range(n):
        for j in range(n):
            if communities[i] == communities[j]:
                q += adj[i, j] - (degrees[i] * degrees[j]) / (2.0 * m)
    return q / (2.0 * m)
