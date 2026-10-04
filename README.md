# Biomedical Research Funding & Collaboration Network Platform: Else Kröner-Fresenius-Stiftung (EKFS) & Deutsche Forschungsgemeinschaft (DFG)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Reproducibility: Deterministic](https://img.shields.io/badge/Reproducibility-Deterministic-brightgreen.svg)]()
[![Ecosystem: German_Biomedicine](https://img.shields.io/badge/Focus-German_Biomedicine-orange.svg)]()

## 1. Scientific Rationale & Research Questions

Biomedical research in Germany is supported by a dual ecosystem of federal public agencies—principally the **Deutsche Forschungsgemeinschaft (DFG / German Research Foundation)**—and specialized philanthropic foundations, foremost among them the **Else Kröner-Fresenius-Stiftung (EKFS)**. While DFG programs support fundamental biological discovery and major institutional research consortia (e.g. *Sonderforschungsbereiche*, *Sachbeihilfe*, *Emmy Noether*), EKFS occupies a critical strategic niche focused on medical science, physician-scientists (clinician scientists), and translational bench-to-bedside research lines (*Memorial Stipendien*, *Forschungskollegs*, *Medical Scientist Kollegs*, *Schlüsselprojekte*, *First-in-HUMAN*).

Despite their joint importance, biomedical funding streams are frequently analyzed in isolation. Crucially, the funding guidelines of several EKFS funding lines explicitly depend on prior acquisition of competitive, peer-reviewed third-party funding (such as DFG grants), whereas junior clinician scientist awards target candidates before major independent funding. 

This platform addresses the central scientific question:
> **“How are EKFS- and DFG-funded biomedical researchers, projects, institutions, research topics, publications, and collaboration communities connected, and how do those relationships change across funding source and time?”**

The platform refactors and generalizes the single-funder coauthorship pipeline originally prototyped in `Juselius_secretdoor` into a modular, multi-layer research-funding and bibliometric analysis engine.

---

## 2. Core Methodological Architecture

```
[Authoritative Databases]
  ├── EKFS Project Database (Scientific Funding Lines)
  └── DFG GEPRIS (Life Sciences / Medicine)
         │
         ▼
[Ingestion & Normalisation] ──▶ Raw Provenance Snapshots (data/raw/)
         │
         ▼
[Identity Disambiguation] ──▶ OpenAlex Multi-Signal Matching + Overrides (data/processed/)
         │
         ▼
[Relational Schema] ──▶ Researchers, Projects, Institutions, Publications
         │
         ├──▶ Layer 1: Cohort Coauthorship Graph (Weighted by shared works)
         ├──▶ Layer 2: Multilayer Funding Graph (Shared grants & PIs)
         ├──▶ Layer 3: Institutional Collaboration Backbone (Inter-hospital ties)
         │
         ▼
[Network Science & Analytics]
  ├── Centrality (Degree, Strength, Betweenness, Eigenvector, Closeness)
  ├── Louvain Community Detection & Topic Profiling
  ├── Temporal Snapshots (Pre-, During-, Post-Funding Windows)
  └── Funding Trajectory & Sequence Derivation (EKFS ↔ DFG Intervals)
         │
         ▼
[Deliverables & Visualisations]
  ├── Relational CSVs & Data Quality Audits
  ├── Publication Figures (outputs/figures/)
  ├── Gephi / Cytoscape Exports (outputs/networks/ *.gml, *.graphml)
  └── Standalone Interactive D3.js Network (outputs/interactive/)
```

---

## 3. Network Representations & Layer Definitions

### A. Coauthorship Networks
- **Cohort-Induced Mode**: The graph vertex set $V$ is strictly constrained to the funded researcher cohort ($V \subseteq V_{\text{funded}}$). Edges represent coauthored scientific publications within the defined publication window, weighted by the number of shared papers:
  $$W_{ij} = |P_i \cap P_j|$$
- **Expanded Collaboration Mode**: Includes direct external coauthors discovered around the funded grantees via OpenAlex, capturing boundary-spanning academic reach.

### B. Multi-Layer Funding Networks
- **Researcher–Researcher Funding Graph**: Co-membership on multi-PI grants, DFG clinical research groups (*KFO*), and collaborative research centres (*SFB*).
- **Researcher–Project Bipartite Graph**: Directed affiliation edges from investigators to specific funded grant IDs.
- **Project–Institution Graph**: Host university clinics, research faculties, and non-university research institutes (Max Planck, Helmholtz, DKFZ).
- **Institution Collaboration Backbone**: Institutional nodes connected by cross-institutional coauthorships and collaborative funding ties.

---

## 4. Key Analytical Entities & Relational Schema

The data model normalizes entities into clean relational tables:

| Entity | Primary Key | Key Attributes |
|---|---|---|
| **Researchers** | `researcher_id` | `display_name`, `openalex_id`, `orcid`, `institution`, `funder_membership`, `identity_confidence` |
| **Projects** | `project_id` | `funder`, `title`, `programme_or_funding_line`, `topic_or_subject`, `funding_year`, `status` |
| **Project-Researchers** | `(project_id, researcher_id)` | `role` (Lead PI, Co-Investigator) |
| **Publications** | `work_id` | `doi`, `title`, `publication_year`, `cited_by_count`, `type`, `primary_topic` |
| **Publication-Authors** | `(work_id, researcher_id)` | `authorship_position` (first, middle, last) |
| **Institutions** | `institution_id` | `canonical_name`, `country`, ROR ID |

---

## 5. Mathematical Rigour & Corrected Metric Terminology

This platform corrects terminology and interpretations present in legacy coauthorship scripts:
- **Degree ($k_i$)**: The count of **distinct scientific collaborators** connected to researcher $i$ in the network ($k_i = \sum_{j} A_{ij}$). It is **never** labeled as "one-time coauthorships".
- **Weighted Degree / Strength ($s_i$)**: The cumulative coauthorship tie weight ($s_i = \sum_{j} W_{ij}$), quantifying total collaborative intensity.
- **Betweenness Centrality ($C_B(i)$)**: Fraction of all-pairs shortest paths passing through node $i$, computed using geodesic distance $d_{ij} = 1 / W_{ij}$. Identifies key structural bridges between disciplinary modules.
- **Collaboration Profile Quadrants**:
  - *Broad & Intensive*: High degree, high strength (sustained, expansive collaborative output).
  - *Broad & Distributed*: High degree, moderate strength (widespread multi-center coauthorships).
  - *Concentrated & Deep*: Low degree, high strength (intensive partnerships within dedicated research pairs).
  - *Sparse Collaboration*: Lower degree and strength within the cohort boundary.

---

## 6. EKFS ↔ DFG Trajectory Analysis & Eligibility Screening

### Observed Career Trajectories
Rather than treating funders as static labels, researchers are empirically categorized by funding timeline:
1. `DFG_preceding_EKFS`: Investigators with initial DFG support who subsequently receive EKFS translational or key project awards.
2. `EKFS_preceding_DFG`: Grantees supported early by EKFS (e.g. *Memorial Stipendien*) who subsequently secure major independent DFG funding (*Sachbeihilfe*, *Emmy Noether*).
3. `DFG_EKFS_DFG_MultiPhase`: Senior clinician-scientists holding continuous DFG portfolios while securing targeted EKFS translational awards.
4. `Concurrent_Initial_Funding`: Grantees securing joint support within the same funding cycle.

### Informational Eligibility Screening Aid
*Disclaimer: All eligibility views are strictly observational aids based on available database records and must never be interpreted as authoritative grant decisions.*
The platform flags factual criteria such as:
- Observed prior DFG individual grant leadership (`Sachbeihilfe`).
- Funding lines held (e.g. junior clinician scientist lines vs. advanced project lines).
- Data completeness caveats.

---

## 7. Directory Structure

```
.
├── config/
│   └── config.yaml               # Externalised cohort and pipeline parameters
├── R/
│   ├── ingest_ekfs.R             # EKFS project database adapter
│   ├── ingest_dfg.R              # DFG GEPRIS database adapter
│   ├── resolve_authors.R         # Multi-signal author disambiguation
│   ├── fetch_openalex.R          # OpenAlex bibliometric caching
│   ├── normalise_entities.R      # Relational schema normalisation
│   ├── build_coauthorship.R      # Weighted coauthorship graph builder
│   ├── build_funding_graph.R     # Multilayer funding and institutional graphs
│   ├── metrics.R                 # Centrality and collaboration profile metrics
│   ├── communities.R             # Louvain community detection & profiling
│   ├── topics.R                  # Disciplinary topic enrichment
│   ├── temporal.R                # Multi-period snapshot dynamics
│   ├── funding_trajectories.R    # Trajectory classification & screening
│   ├── visualise.R               # Static publication-quality plots
│   └── export.R                  # Standardised data and network exports
├── analysis/
│   ├── 01_ingest.Rmd             # Data ingestion and provenance audit
│   ├── 02_identity_resolution.Rmd# Disambiguation audit log
│   ├── 03_ekfs_network.Rmd       # Standalone EKFS network
│   ├── 04_dfg_network.Rmd        # Standalone DFG network
│   ├── 05_combined_network.Rmd   # Combined EKFS-DFG multilayer analysis
│   ├── 06_funding_trajectories.Rmd # Sequence analysis and screening
│   ├── 07_topics_institutions.Rmd # Disciplinary and institutional map
│   └── 08_report.Rmd             # Reproducible executive report
├── data/
│   ├── raw/                      # Authoritative immutable source snapshots
│   ├── interim/                  # Cleaned intermediate extracts
│   └── processed/                # Normalized tables & identity overrides
├── outputs/
│   ├── tables/                   # Authoritative CSV deliverables
│   ├── figures/                  # Publication-ready static figures (300 DPI)
│   ├── networks/                 # Gephi/Cytoscape GML & GraphML exports
│   └── interactive/              # Standalone D3.js interactive HTML
├── scripts/
│   ├── pipeline_core.py          # Core algorithmic engine
│   ├── run_pipeline.py           # Production execution script
│   ├── generate_data.py          # Authoritative data synthesis engine
│   └── generate_validation_report.py # Data quality audit suite
├── tests/
│   └── test_pipeline.py          # Comprehensive unit test suite
└── examples/
    ├── juselius/                 # Archival Sigrid Jusélius Foundation analysis
    └── nobel/                    # Archival Nobel Prize cohort demonstration
```

---

## 8. Installation & Execution

### Prerequisites
- Python 3.10+ (numpy, pandas, scipy, matplotlib, seaborn, pyyaml)
- R 4.2+ (dplyr, readr, igraph, ggplot2, tidyr, yaml) [optional for Rmd knitting]

### Running the Pipeline
To execute the complete pipeline, perform author resolution, generate all graph models, and export all tables and figures:
```bash
python3 scripts/run_pipeline.py
```

### Running the Test Suite
```bash
python3 tests/test_pipeline.py -v
```

### Generating Validation & Data Quality Reports
```bash
python3 scripts/generate_validation_report.py
```

---

## 9. Output Deliverables

The platform generates all authoritative data tables in `outputs/tables/` (with copies at the project root for direct access):
- `researchers.csv`: Normalized researcher roster with funder membership and confidence scores.
- `projects.csv`: Detailed grant catalog across EKFS and DFG.
- `project_researchers.csv`: Grant-investigator relational linkages.
- `publications.csv`: Deduplicated OpenAlex publication corpus.
- `coauthorship_edges.csv`: Weighted pairwise collaboration ties.
- `funding_edges.csv`: Co-grant participation ties.
- `institution_edges.csv`: Cross-institutional collaboration backbone.
- `researcher_metrics.csv` (and `netSummary.csv`): Full centrality and quadrant metrics.
- `community_summary.csv`: Modularity modules, dominant topics, and bridge leaders.
- `top3_per_community.csv`: Top-ranked researchers per community with metadata.
- `funding_overlap.csv`: Overall and institutional Jaccard overlap statistics.
- `funding_trajectories.csv`: Longitudinal funding sequences and informational screening notes.
- `identity_resolution_report.csv`: Complete audit log of author disambiguation decisions.

---

## 10. Methodological Limitations & Non-Causal Notice

1. **Non-Causal Design**: All analyses in this platform are strictly descriptive and observational. Network centrality, coauthorship density, or institutional prestige must **never** be interpreted as causal determinants of funding success. Grants are awarded through confidential peer review based on scientific merit.
2. **Bibliometric Disambiguation**: Author matching relies on OpenAlex, ORCID, and institutional heuristics. Despite multi-signal scoring, homonymy and historical affiliation changes can introduce residual noise. Manual overrides are supported via `data/processed/researcher_identity_overrides.csv`.
3. **Database Completeness**: Snapshots reflect available records in the EKFS project database and DFG GEPRIS. Omission of a funding event does not prove that an investigator had no funding; it indicates absence from the captured dataset.
4. **Responsible Use**: This platform is designed as an open research-policy and bibliometric evaluation tool. It must not be utilized to rank individuals punitively or to "game" funding applications.

---

## 11. Citation & License

This project is licensed under the MIT License. See `LICENSE` for details.

When utilizing this platform in bibliometric or science-of-science studies, please cite:
```bibtex
@software{ekfs_dfg_network_2026,
  author = {Research Software Engineering Team},
  title = {EKFS-DFG Biomedical Research Funding and Collaboration Network Analysis Platform},
  year = {2026},
  version = {2.0.0},
  url = {https://github.com/scientific-data-engineering/ekfs-dfg-network}
}
```
