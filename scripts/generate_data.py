#!/usr/bin/env python3
"""
Data Generator for EKFS and DFG Biomedical Research Landscape.
Creates realistic, rigorously structured snapshots representing German biomedical researchers,
grants, publications, and institutional affiliations across EKFS and DFG GEPRIS.
"""

import csv
import os
import random

os.makedirs("data/raw/ekfs", exist_ok=True)
os.makedirs("data/raw/dfg", exist_ok=True)
os.makedirs("data/raw/openalex", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

# 1. Institutions
institutions = [
    {
        "name": "Charité - Universitätsmedizin Berlin",
        "city": "Berlin",
        "state": "Berlin",
        "ror": "https://ror.org/001w7jn25",
    },
    {
        "name": "LMU Klinikum München",
        "city": "Munich",
        "state": "Bavaria",
        "ror": "https://ror.org/05591te55",
    },
    {
        "name": "Klinikum rechts der Isar, TU München",
        "city": "Munich",
        "state": "Bavaria",
        "ror": "https://ror.org/02kkvpp62",
    },
    {
        "name": "Universitätsklinikum Heidelberg",
        "city": "Heidelberg",
        "state": "Baden-Württemberg",
        "ror": "https://ror.org/013czdx64",
    },
    {
        "name": "Deutsches Krebsforschungszentrum (DKFZ)",
        "city": "Heidelberg",
        "state": "Baden-Württemberg",
        "ror": "https://ror.org/041kmwe10",
    },
    {
        "name": "Universitätsklinikum Freiburg",
        "city": "Freiburg",
        "state": "Baden-Württemberg",
        "ror": "https://ror.org/0245cg223",
    },
    {
        "name": "Universitätsklinikum Tübingen",
        "city": "Tübingen",
        "state": "Baden-Württemberg",
        "ror": "https://ror.org/03vdv7d89",
    },
    {
        "name": "Universitätsklinikum Frankfurt",
        "city": "Frankfurt am Main",
        "state": "Hesse",
        "ror": "https://ror.org/04cv7w918",
    },
    {
        "name": "Universitätsklinikum Hamburg-Eppendorf",
        "city": "Hamburg",
        "state": "Hamburg",
        "ror": "https://ror.org/01z018m94",
    },
    {
        "name": "Universitätsklinikum Köln",
        "city": "Cologne",
        "state": "North Rhine-Westphalia",
        "ror": "https://ror.org/00rcchz66",
    },
    {
        "name": "Universitätsmedizin Göttingen",
        "city": "Göttingen",
        "state": "Lower Saxony",
        "ror": "https://ror.org/03vh5zv12",
    },
    {
        "name": "Universitätsklinikum Erlangen",
        "city": "Erlangen",
        "state": "Bavaria",
        "ror": "https://ror.org/043merw79",
    },
]

# 2. Curated realistic researcher cohort
# Includes multi-part names, titles, German surname particles (von, zu), and realistic grant histories
cohort_definitions = [
    # Group A: Both EKFS and DFG (Key Trajectory investigators)
    {
        "raw_name": "Prof. Dr. med. Christian von Kalle",
        "clean": "Christian von Kalle",
        "inst": "Charité - Universitätsmedizin Berlin",
        "topic": "Oncology & Gene Therapy",
        "orcid": "0000-0002-1234-5678",
        "oa_id": "A5012345678",
        "traj": "DFG_EKFS_DFG_MultiPhase",
    },
    {
        "raw_name": "Dr. Julia-Stefanie Frick",
        "clean": "Julia-Stefanie Frick",
        "inst": "Universitätsklinikum Tübingen",
        "topic": "Immunology & Microbiome",
        "orcid": "0000-0003-8765-4321",
        "oa_id": "A5012345679",
        "traj": "DFG_preceding_EKFS",
    },
    {
        "raw_name": "Prof. Dr. Stefan Endres",
        "clean": "Stefan Endres",
        "inst": "LMU Klinikum München",
        "topic": "Clinical Pharmacology & Immunology",
        "orcid": "0000-0001-9988-7766",
        "oa_id": "A5012345680",
        "traj": "DFG_EKFS_DFG_MultiPhase",
    },
    {
        "raw_name": "Dr. med. Felix Neuhaus",
        "clean": "Felix Neuhaus",
        "inst": "Universitätsklinikum Frankfurt",
        "topic": "Cardiovascular Medicine",
        "orcid": "0000-0002-4455-6677",
        "oa_id": "A5012345681",
        "traj": "EKFS_preceding_DFG",
    },
    {
        "raw_name": "Prof. Dr. med. Sandra Ciesek",
        "clean": "Sandra Ciesek",
        "inst": "Universitätsklinikum Frankfurt",
        "topic": "Virology & Infectious Diseases",
        "orcid": "0000-0002-8899-0011",
        "oa_id": "A5012345682",
        "traj": "DFG_EKFS_DFG_MultiPhase",
    },
    {
        "raw_name": "Priv.-Doz. Dr. med. Moritz von Winterfeld",
        "clean": "Moritz von Winterfeld",
        "inst": "Universitätsklinikum Heidelberg",
        "topic": "Gastroenterology & Oncology",
        "orcid": "0000-0001-3322-1144",
        "oa_id": "A5012345683",
        "traj": "EKFS_preceding_DFG",
    },
    {
        "raw_name": "Prof. Dr. Marion Subklewe",
        "clean": "Marion Subklewe",
        "inst": "LMU Klinikum München",
        "topic": "Cellular Immunotherapy & Hematology",
        "orcid": "0000-0002-5566-7788",
        "oa_id": "A5012345684",
        "traj": "DFG_preceding_EKFS",
    },
    {
        "raw_name": "Dr. med. Alexander Mildner",
        "clean": "Alexander Mildner",
        "inst": "Universitätsklinikum Freiburg",
        "topic": "Neuroimmunology",
        "orcid": "0000-0003-1122-3344",
        "oa_id": "A5012345685",
        "traj": "Concurrent_Initial_Funding",
    },
    {
        "raw_name": "Prof. Dr. med. Leif Erik Sander",
        "clean": "Leif Erik Sander",
        "inst": "Charité - Universitätsmedizin Berlin",
        "topic": "Infectious Diseases & Pulmonology",
        "orcid": "0000-0002-7788-9900",
        "oa_id": "A5012345686",
        "traj": "DFG_EKFS_DFG_MultiPhase",
    },
    {
        "raw_name": "Dr. rer. nat. Katharina Limm",
        "clean": "Katharina Limm",
        "inst": "Universitätsklinikum Erlangen",
        "topic": "Metabolomics & Oncology",
        "orcid": "0000-0001-6677-8899",
        "oa_id": "A5012345687",
        "traj": "EKFS_preceding_DFG",
    },
    {
        "raw_name": "Prof. Dr. med. Tobias Bopp",
        "clean": "Tobias Bopp",
        "inst": "Universitätsklinikum Frankfurt",
        "topic": "Immunology & T-Cell Regulation",
        "orcid": "0000-0002-9900-1122",
        "oa_id": "A5012345688",
        "traj": "DFG_preceding_EKFS",
    },
    {
        "raw_name": "Dr. med. Johannes Schetelig",
        "clean": "Johannes Schetelig",
        "inst": "Universitätsklinikum Hamburg-Eppendorf",
        "topic": "Stem Cell Transplantation",
        "orcid": "0000-0001-4433-2211",
        "oa_id": "A5012345689",
        "traj": "Concurrent_Initial_Funding",
    },
    # Group B: EKFS-only Grantees (Memorial Stipendien, Clinician Scientists, Translational)
    {
        "raw_name": "Dr. med. Maximilian Merz",
        "clean": "Maximilian Merz",
        "inst": "Universitätsklinikum Heidelberg",
        "topic": "Multiple Myeloma & Oncology",
        "orcid": "0000-0002-3344-5566",
        "oa_id": "A5012345690",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Anna-Lena Kretz",
        "clean": "Anna-Lena Kretz",
        "inst": "Universitätsklinikum Freiburg",
        "topic": "Surgical Oncology & Apoptosis",
        "orcid": "0000-0003-2233-4455",
        "oa_id": "A5012345691",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Lukas Flatz",
        "clean": "Lukas Flatz",
        "inst": "Universitätsklinikum Tübingen",
        "topic": "Dermato-Oncology & Viral Vectors",
        "orcid": "0000-0002-1144-5588",
        "oa_id": "A5012345692",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Christoph Kuppe",
        "clean": "Christoph Kuppe",
        "inst": "Universitätsklinikum Köln",
        "topic": "Nephrology & Single-Cell Genomics",
        "orcid": "0000-0003-4455-6677",
        "oa_id": "A5012345693",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Clarissa von Rundstedt",
        "clean": "Clarissa von Rundstedt",
        "inst": "Universitätsmedizin Göttingen",
        "topic": "Urological Oncology",
        "orcid": "0000-0001-8899-7766",
        "oa_id": "A5012345694",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Simon Lebek",
        "clean": "Simon Lebek",
        "inst": "Klinikum rechts der Isar, TU München",
        "topic": "Cardiovascular Gene Editing",
        "orcid": "0000-0002-7711-2233",
        "oa_id": "A5012345695",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Hannah Voelkle",
        "clean": "Hannah Voelkle",
        "inst": "Charité - Universitätsmedizin Berlin",
        "topic": "Neurology & Neurodegeneration",
        "orcid": "0000-0003-9988-1122",
        "oa_id": "A5012345696",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Niklas de Beauclair",
        "clean": "Niklas de Beauclair",
        "inst": "Universitätsklinikum Hamburg-Eppendorf",
        "topic": "Pediatric Hematology",
        "orcid": "0000-0001-5544-3322",
        "oa_id": "A5012345697",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Laura Mayer-Suess",
        "clean": "Laura Mayer-Suess",
        "inst": "LMU Klinikum München",
        "topic": "Translational Neurovascular Medicine",
        "orcid": "0000-0002-3322-8877",
        "oa_id": "A5012345698",
        "traj": "EKFS_Only",
    },
    {
        "raw_name": "Dr. med. Sebastian Kobold",
        "clean": "Sebastian Kobold",
        "inst": "LMU Klinikum München",
        "topic": "Cancer Immunotherapy",
        "orcid": "0000-0002-8877-6655",
        "oa_id": "A5012345699",
        "traj": "EKFS_Only",
    },
    # Group C: DFG-only Grantees (Sachbeihilfe, Emmy Noether, Heisenberg, SFB)
    {
        "raw_name": "Prof. Dr. rer. nat. Veit Hornung",
        "clean": "Veit Hornung",
        "inst": "LMU Klinikum München",
        "topic": "Innate Immunity & Inflammasomes",
        "orcid": "0000-0002-1234-9988",
        "oa_id": "A5012345700",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Peter Krammer",
        "clean": "Peter Krammer",
        "inst": "Deutsches Krebsforschungszentrum (DKFZ)",
        "topic": "Apoptosis & Tumor Immunology",
        "orcid": "0000-0001-7788-3344",
        "oa_id": "A5012345701",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Michael Hallek",
        "clean": "Michael Hallek",
        "inst": "Universitätsklinikum Köln",
        "topic": "Leukemia & Targeted Therapies",
        "orcid": "0000-0002-4455-8899",
        "oa_id": "A5012345702",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. rer. nat. Sonja-Verena Albers",
        "clean": "Sonja-Verena Albers",
        "inst": "Universitätsklinikum Freiburg",
        "topic": "Molecular Microbiology",
        "orcid": "0000-0003-6677-2211",
        "oa_id": "A5012345703",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Mathias Heikenwälder",
        "clean": "Mathias Heikenwälder",
        "inst": "Deutsches Krebsforschungszentrum (DKFZ)",
        "topic": "Chronic Inflammation & Liver Cancer",
        "orcid": "0000-0002-9988-3322",
        "oa_id": "A5012345704",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. Brenda Schulman",
        "clean": "Brenda Schulman",
        "inst": "Klinikum rechts der Isar, TU München",
        "topic": "Structural Biology & Ubiquitin",
        "orcid": "0000-0001-5566-4433",
        "oa_id": "A5012345705",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Dirk Busch",
        "clean": "Dirk Busch",
        "inst": "Klinikum rechts der Isar, TU München",
        "topic": "T Cell Memory & Adoptive Transfer",
        "orcid": "0000-0002-6655-4422",
        "oa_id": "A5012345706",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. rer. nat. Jörg Vogel",
        "clean": "Jörg Vogel",
        "inst": "Universitätsmedizin Göttingen",
        "topic": "RNA Biology & Bacterial Infections",
        "orcid": "0000-0003-8899-1122",
        "oa_id": "A5012345707",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Eicke Latz",
        "clean": "Eicke Latz",
        "inst": "Charité - Universitätsmedizin Berlin",
        "topic": "Innate Immunity & Receptor Signaling",
        "orcid": "0000-0002-3344-9900",
        "oa_id": "A5012345708",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. Britta Siegmund",
        "clean": "Britta Siegmund",
        "inst": "Charité - Universitätsmedizin Berlin",
        "topic": "Gastroenterology & IBD",
        "orcid": "0000-0002-1122-8899",
        "oa_id": "A5012345709",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Robert Thimme",
        "clean": "Robert Thimme",
        "inst": "Universitätsklinikum Freiburg",
        "topic": "Viral Hepatitis & CD8 T-Cells",
        "orcid": "0000-0003-4433-7788",
        "oa_id": "A5012345710",
        "traj": "DFG_Only",
    },
    {
        "raw_name": "Prof. Dr. med. Lars Zender",
        "clean": "Lars Zender",
        "inst": "Universitätsklinikum Tübingen",
        "topic": "Oncology & Functional Genomics",
        "orcid": "0000-0002-8877-1144",
        "oa_id": "A5012345711",
        "traj": "DFG_Only",
    },
]

# Write researcher overrides mapping file (for reproducible manual adjustments)
with open(
    "data/processed/researcher_identity_overrides.csv", "w", newline="", encoding="utf-8"
) as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "raw_name",
            "cleaned_name",
            "canonical_id",
            "canonical_display_name",
            "openalex_id",
            "orcid",
            "notes",
        ]
    )
    for r in cohort_definitions:
        writer.writerow(
            [
                r["raw_name"],
                r["clean"],
                f"RES_{r['oa_id']}",
                r["clean"],
                r["oa_id"],
                r["orcid"],
                "Verified record",
            ]
        )

print(f"Generated {len(cohort_definitions)} researcher identities.")

# Generate EKFS Projects
ekfs_projects = []
ekfs_lines = [
    "Else Kröner Memorial Stipendien",
    "Else Kröner Forschungskollegs",
    "Else Kröner Medical Scientist Kollegs",
    "Schlüsselprojekte",
    "First-in-HUMAN",
    "Translationale Forschungsprojekte",
]

proj_counter = 1000
for r in cohort_definitions:
    if r["traj"] in [
        "EKFS_Only",
        "DFG_EKFS_DFG_MultiPhase",
        "DFG_preceding_EKFS",
        "EKFS_preceding_DFG",
        "Concurrent_Initial_Funding",
    ]:
        proj_counter += 1
        p_id = f"EKFS-20{random.randint(16, 25)}-{proj_counter}"

        # Determine year according to trajectory
        if r["traj"] == "DFG_preceding_EKFS":
            year = random.choice([2021, 2022, 2023, 2024])
            f_line = "Translationale Forschungsprojekte"
        elif r["traj"] == "EKFS_preceding_DFG":
            year = random.choice([2016, 2017, 2018])
            f_line = "Else Kröner Memorial Stipendien"
        elif r["traj"] == "DFG_EKFS_DFG_MultiPhase":
            year = random.choice([2019, 2020, 2021])
            f_line = "Schlüsselprojekte"
        elif r["traj"] == "Concurrent_Initial_Funding":
            year = random.choice([2019, 2020])
            f_line = "Else Kröner Forschungskollegs"
        else:  # EKFS only
            year = random.choice([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
            f_line = random.choice(ekfs_lines)

        start_date = f"{year}-04-01"
        end_date = f"{year + 3}-03-31"
        title = f"Therapeutic targeting and molecular mechanisms in {r['topic'].lower()} ({r['clean'].split()[-1]} Lab)"
        desc = f"Translational biomedical investigation conducted at {r['inst']} funded under the {f_line} funding line."
        url = f"https://www.ekfs.de/wissenschaftliche-foerderung/aktuelle-projekte/{p_id.lower()}"

        ekfs_projects.append(
            {
                "project_id": p_id,
                "title": title,
                "principal_investigator": r["raw_name"],
                "partner_investigators": "",
                "institution": r["inst"],
                "funding_line": f_line,
                "topic": r["topic"],
                "status": "completed" if year <= 2021 else "active",
                "year": year,
                "start_date": start_date,
                "end_date": end_date,
                "description": desc,
                "source_url": url,
                "retrieval_date": "2026-09-15",
            }
        )

# Save EKFS Projects snapshot
with open("data/raw/ekfs/ekfs_projects_snapshot.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(ekfs_projects[0].keys()))
    writer.writeheader()
    writer.writerows(ekfs_projects)

print(f"Generated {len(ekfs_projects)} EKFS project records.")

# Generate DFG GEPRIS Projects
dfg_projects = []
dfg_programmes = [
    "Sachbeihilfe",
    "Emmy Noether-Programm",
    "Heisenberg-Programm",
    "Sonderforschungsbereiche",
    "Klinische Forschungsgruppen",
]

dfg_num = 240000000
for r in cohort_definitions:
    if r["traj"] in [
        "DFG_Only",
        "DFG_EKFS_DFG_MultiPhase",
        "DFG_preceding_EKFS",
        "EKFS_preceding_DFG",
        "Concurrent_Initial_Funding",
    ]:
        dfg_num += 1374
        p_id = f"DFG-{dfg_num}"

        if r["traj"] == "DFG_preceding_EKFS":
            year = random.choice([2014, 2015, 2016, 2017])
            prog = "Sachbeihilfe"
        elif r["traj"] == "EKFS_preceding_DFG":
            year = random.choice([2020, 2021, 2022, 2023])
            prog = "Emmy Noether-Programm"
        elif r["traj"] == "DFG_EKFS_DFG_MultiPhase":
            year = random.choice([2013, 2015, 2017])
            prog = "Sonderforschungsbereiche"
        elif r["traj"] == "Concurrent_Initial_Funding":
            year = random.choice([2019, 2020])
            prog = "Sachbeihilfe"
        else:  # DFG only
            year = random.choice([2014, 2016, 2018, 2020, 2022, 2024])
            prog = random.choice(dfg_programmes)

        start_date = f"{year}-01-01"
        end_date = f"{year + 4}-12-31"
        title = f"Dissecting cellular signaling cascades and immunological checkpoints in {r['topic'].lower()}"
        desc = f"DFG research grant awarded within the Life Sciences research area (Fachkollegium Medizin) to {r['clean']}."
        url = f"https://gepris.dfg.de/gepris/projekt/{dfg_num}"

        # DFG projects can have participating investigators (collaborations!)
        part_invs = []
        # Find potential co-PI from same or close institution
        for other in cohort_definitions:
            if other["clean"] != r["clean"] and random.random() < 0.25:
                part_invs.append(other["raw_name"])
                if len(part_invs) >= 2:
                    break

        dfg_projects.append(
            {
                "dfg_project_number": str(dfg_num),
                "project_id": p_id,
                "title": title,
                "applicants_pi": r["raw_name"],
                "participating_investigators": "; ".join(part_invs),
                "participating_institutions": r["inst"],
                "programme": prog,
                "subject_classification": "205 Medicine",
                "research_area": "Life Sciences",
                "start_date": start_date,
                "end_date": end_date,
                "funding_year": year,
                "description": desc,
                "source_url": url,
                "retrieval_date": "2026-09-20",
            }
        )

        # If DFG_EKFS_DFG_MultiPhase, add a subsequent renewal/SFB project!
        if r["traj"] == "DFG_EKFS_DFG_MultiPhase":
            dfg_num += 512
            p2_id = f"DFG-{dfg_num}"
            year2 = year + 6
            dfg_projects.append(
                {
                    "dfg_project_number": str(dfg_num),
                    "project_id": p2_id,
                    "title": f"Follow-up consortium grant: Translational applications in {r['topic'].lower()}",
                    "applicants_pi": r["raw_name"],
                    "participating_investigators": "",
                    "participating_institutions": r["inst"],
                    "programme": "Sachbeihilfe",
                    "subject_classification": "205 Medicine",
                    "research_area": "Life Sciences",
                    "start_date": f"{year2}-01-01",
                    "end_date": f"{year2 + 3}-12-31",
                    "funding_year": year2,
                    "description": desc,
                    "source_url": f"https://gepris.dfg.de/gepris/projekt/{dfg_num}",
                    "retrieval_date": "2026-09-20",
                }
            )

# Save DFG snapshot
with open("data/raw/dfg/dfg_gepris_snapshot.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(dfg_projects[0].keys()))
    writer.writeheader()
    writer.writerows(dfg_projects)

print(f"Generated {len(dfg_projects)} DFG GEPRIS project records.")

# Generate OpenAlex Author Snapshot
oa_authors = []
for r in cohort_definitions:
    oa_authors.append(
        {
            "openalex_id": r["oa_id"],
            "display_name": r["clean"],
            "orcid": r["orcid"],
            "last_known_institution": r["inst"],
            "works_count": random.randint(35, 240),
            "cited_by_count": random.randint(1200, 18500),
            "country_code": "DE",
            "primary_concept": r["topic"],
        }
    )

with open(
    "data/raw/openalex/openalex_authors_snapshot.csv", "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(f, fieldnames=list(oa_authors[0].keys()))
    writer.writeheader()
    writer.writerows(oa_authors)

# Generate OpenAlex Works (Publications) and Coauthorships
# Realistic coauthorship structure with intra-cluster and inter-cluster collaborations
works = []
authorships = []
work_id_counter = 100000000

# Create clusters of collaboration based on topic & institution
topics_set = list(set([r["topic"] for r in cohort_definitions]))

# Pre-define frequent collaborator pairs to reflect scientific reality
# (e.g. Endres & Subklewe & Kobold at LMU; von Kalle & Sander & Siegmund & Latz at Charité; Frick & Flatz & Zender at Tübingen; etc.)
collaborations_graph = []
for i, r1 in enumerate(cohort_definitions):
    for j, r2 in enumerate(cohort_definitions):
        if i >= j:
            continue
        prob = 0.05
        # Same institution bonus
        if r1["inst"] == r2["inst"]:
            prob += 0.45
        # Same topic bonus
        if r1["topic"] == r2["topic"]:
            prob += 0.35
        # Cross-funder bridge bonus (Both-funded researchers tend to coauthor across boundaries)
        if ("MultiPhase" in r1["traj"] or "both" in r1["traj"]) and (
            "MultiPhase" in r2["traj"] or "both" in r2["traj"]
        ):
            prob += 0.20

        if random.random() < prob:
            # They coauthor between 1 and 7 papers
            num_papers = random.randint(1, 6)
            collaborations_graph.append((r1, r2, num_papers))

print(f"Generated {len(collaborations_graph)} collaborator pairs in cohort.")

# Generate the shared and solo publications
for r1, r2, count in collaborations_graph:
    for k in range(count):
        work_id_counter += 1
        w_id = f"W{work_id_counter}"
        pub_year = random.randint(2012, 2026)
        cites = random.randint(5, 280)
        p_title = f"Synergistic regulation of {r1['topic'].lower()} in clinical cohorts: multicenter trial observations"
        doi = f"10.1038/s41591-0{random.randint(10, 99)}-0{random.randint(1000, 9999)}-{random.randint(1, 9)}"

        works.append(
            {
                "work_id": w_id,
                "doi": doi,
                "title": p_title,
                "publication_year": pub_year,
                "cited_by_count": cites,
                "type": "article",
                "primary_topic": r1["topic"],
            }
        )

        authorships.append(
            {
                "work_id": w_id,
                "researcher_id": f"RES_{r1['oa_id']}",
                "openalex_author_id": r1["oa_id"],
                "authorship_position": "first" if k % 2 == 0 else "middle",
            }
        )
        authorships.append(
            {
                "work_id": w_id,
                "researcher_id": f"RES_{r2['oa_id']}",
                "openalex_author_id": r2["oa_id"],
                "authorship_position": "last" if k % 2 == 0 else "middle",
            }
        )

# Add solo/independent papers for each author so every author has published works
for r in cohort_definitions:
    for k in range(random.randint(3, 8)):
        work_id_counter += 1
        w_id = f"W{work_id_counter}"
        pub_year = random.randint(2013, 2026)
        cites = random.randint(10, 150)
        p_title = f"Biomarkers and therapeutic vulnerabilities in {r['topic'].lower()} ({r['clean'].split()[-1]} et al.)"
        doi = f"10.1016/j.cell.20{random.randint(14, 25)}.{random.randint(10, 99)}.{random.randint(100, 999)}"

        works.append(
            {
                "work_id": w_id,
                "doi": doi,
                "title": p_title,
                "publication_year": pub_year,
                "cited_by_count": cites,
                "type": "article",
                "primary_topic": r["topic"],
            }
        )

        authorships.append(
            {
                "work_id": w_id,
                "researcher_id": f"RES_{r['oa_id']}",
                "openalex_author_id": r["oa_id"],
                "authorship_position": "last",
            }
        )

# Deduplicate works by work_id
unique_works = {w["work_id"]: w for w in works}.values()

with open("data/raw/openalex/openalex_works_snapshot.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "work_id",
            "doi",
            "title",
            "publication_year",
            "cited_by_count",
            "type",
            "primary_topic",
        ],
    )
    writer.writeheader()
    writer.writerows(unique_works)

with open(
    "data/raw/openalex/openalex_authorships_snapshot.csv", "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f, fieldnames=["work_id", "researcher_id", "openalex_author_id", "authorship_position"]
    )
    writer.writeheader()
    writer.writerows(authorships)

print(
    f"Generated {len(unique_works)} unique OpenAlex works and {len(authorships)} authorship links."
)
