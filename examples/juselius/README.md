# Legacy Analysis: Sigrid Jusélius Foundation Coauthorship Pipeline

This directory preserves the historical implementation from the repository originally known as `Juselius_secretdoor`.
It serves as an archival record of the original single-funder (Sigrid Jusélius Stiftelse) coauthorship analysis and demonstrates how the core network analysis concepts were structured prior to generalisation.

## Contents
- `AuthorNet.Rmd`: The expanded coauthorship network pipeline. Starting from a target list of funded researchers, it queried OpenAlex for works, extracted all coauthors, and built an open collaboration graph around the cohort.
- `AuthorNetFilter.Rmd`: The cohort-filtered coauthorship network pipeline. It retained only coauthorship edges where *both* authors belonged to the target funded cohort.
- `legacy_data/`: Sample input list of Jusélius-funded medical researchers (`juselius_grants_sample.csv`).
- `legacy_outputs/`:
  - `netSummary.csv`: Legacy network summary table with degree, weighted degree, and betweenness.
  - `top3_per_community.csv`: Top 3 researchers per Louvain community ranked by degree.
  - `juselius_network.gml`: Exported Gephi-compatible GML graph.

## Architectural Audit & Evolution
| Legacy Concept | Legacy Implementation | New Modular Architecture (`R/`, `analysis/`) |
|---|---|---|
| Ingestion | Ad-hoc CSV reading inside Rmd | Dedicated ingest adapters (`R/ingest_ekfs.R`, `R/ingest_dfg.R`) |
| Author Disambiguation | Selected top hit by `works_count` | Multi-signal Bayesian/rule disambiguation (`R/resolve_authors.R`) with audit trail |
| Cohort Handling | Hardcoded for Jusélius cohort | Config-driven cohort selection (`config/config.yaml`, `R/normalise_entities.R`) |
| Network Construction | Inlined in Rmd chunks | Modular builders (`R/build_coauthorship.R`, `R/build_funding_graph.R`) |
| Degree Interpretation | Mislabelled "One-Time Coauthorships" | Rigorous graph theory: degree = distinct collaborators, strength = edge sum |
| Funder Scope | Single funder (Jusélius) | Multi-funder cross-layer (EKFS + DFG) with funding trajectories |
