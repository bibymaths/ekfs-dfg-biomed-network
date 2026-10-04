#' Entity Normalisation and Relational Data Modeling Module
#'
#' @description
#' Transforms diverse raw funding and bibliometric snapshots into a normalized,
#' relational schema with primary and foreign keys:
#' - researchers
#' - projects
#' - project_researchers
#' - publications
#' - publication_authors
#' - institutions
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(tidyr)
})

#' Build Normalised Relational Dataset
#'
#' @param ekfs_raw Ingested EKFS projects.
#' @param dfg_raw Ingested DFG projects.
#' @param resolved_researchers Resolved researcher identities.
#' @param works_raw Raw OpenAlex publications.
#' @param authorship_raw Raw authorship linkages.
#' @return A named list of relational tibbles.
normalise_entities <- function(ekfs_raw,
                               dfg_raw,
                               resolved_researchers,
                               works_raw,
                               authorship_raw) {
  message("Normalising entities into relational data model...")
  
  # 1. Projects Table
  ekfs_projects <- ekfs_raw %>%
    transmute(
      project_id = project_id,
      funder = "EKFS",
      title = title,
      programme_or_funding_line = funding_line,
      topic_or_subject = topic,
      start_date = start_date,
      end_date = end_date,
      status = status,
      funding_year = year,
      source_url = source_url
    )
  
  dfg_projects <- dfg_raw %>%
    transmute(
      project_id = project_id,
      funder = "DFG",
      title = title,
      programme_or_funding_line = programme,
      topic_or_subject = subject_classification,
      start_date = start_date,
      end_date = end_date,
      status = "active",
      funding_year = funding_year,
      source_url = source_url
    )
  
  projects <- bind_rows(ekfs_projects, dfg_projects) %>%
    distinct(project_id, .keep_all = TRUE)
  
  # 2. Researchers Table & Funder Membership Classification
  # Determine funder_membership: 'EKFS only', 'DFG only', 'both'
  researcher_funder_counts <- resolved_researchers %>%
    group_by(canonical_id) %>%
    summarise(
      has_ekfs = any(funder == "EKFS"),
      has_dfg = any(funder == "DFG"),
      funder_membership = case_when(
        has_ekfs & has_dfg ~ "both",
        has_ekfs & !has_dfg ~ "EKFS only",
        !has_ekfs & has_dfg ~ "DFG only",
        TRUE ~ "neither"
      ),
      .groups = "drop"
    )
  
  researchers <- resolved_researchers %>%
    distinct(canonical_id, .keep_all = TRUE) %>%
    left_join(researcher_funder_counts %>% select(canonical_id, funder_membership), by = "canonical_id") %>%
    transmute(
      researcher_id = canonical_id,
      display_name = canonical_display_name,
      openalex_id = openalex_id,
      orcid = orcid,
      institution = institution,
      country = "Germany",
      funder_membership = funder_membership,
      identity_confidence = confidence_score,
      needs_manual_review = needs_manual_review
    )
  
  # 3. Project-Researchers Linking Table
  project_researchers <- resolved_researchers %>%
    transmute(
      project_id = project_ids,
      researcher_id = canonical_id,
      role = "Principal Investigator / Lead"
    ) %>%
    distinct()
  
  # 4. Publications Table
  publications <- works_raw %>%
    transmute(
      work_id = work_id,
      doi = doi,
      title = title,
      publication_year = publication_year,
      cited_by_count = cited_by_count,
      type = type,
      primary_topic = primary_topic
    ) %>%
    distinct(work_id, .keep_all = TRUE)
  
  # 5. Publication Authors Table
  publication_authors <- authorship_raw %>%
    transmute(
      work_id = work_id,
      researcher_id = researcher_id,
      authorship_position = authorship_position
    ) %>%
    distinct()
  
  # 6. Institutions Table
  institutions <- researchers %>%
    filter(!is.na(institution) & institution != "") %>%
    distinct(institution) %>%
    mutate(
      institution_id = sprintf("INST_%03d", row_number()),
      canonical_name = institution,
      country = "Germany"
    )
  
  message(sprintf("Normalisation complete: %d researchers, %d projects, %d publications.",
                  nrow(researchers), nrow(projects), nrow(publications)))
  
  return(list(
    researchers = researchers,
    projects = projects,
    project_researchers = project_researchers,
    publications = publications,
    publication_authors = publication_authors,
    institutions = institutions
  ))
}
