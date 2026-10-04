#' Research Topic Analysis and Disciplinary Comparison Module
#'
#' @description
#' Harmonizes and analyzes multidimensional topic vocabularies across:
#' - EKFS medical project topics
#' - DFG GEPRIS subject classifications (Fachkollegien)
#' - OpenAlex primary publication topics (modern taxonomy)
#'
#' Evaluates topic distributions by funder, over-represented topics,
#' institutional topic specializations, community topic diversity, and temporal evolution.
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(stringr)
})

#' Analyze Topic Landscape Across Funders
#'
#' @param projects_df Tibble of projects with topic_or_subject and funder.
#' @param publications_df Tibble of publications with primary_topic and publication_year.
#' @param project_researchers Tibble linking project to researcher.
#' @param researchers_df Tibble of researchers.
#' @return A list of topic distribution and comparison tables.
analyze_research_topics <- function(projects_df,
                                    publications_df,
                                    project_researchers,
                                    researchers_df) {
  message("Analyzing biomedical topic distributions across EKFS and DFG...")
  
  # 1. Project Topic Distribution by Funder
  funder_project_topics <- projects_df %>%
    group_by(funder, topic_or_subject) %>%
    summarise(
      project_count = n(),
      .groups = "drop"
    ) %>%
    arrange(funder, desc(project_count))
  
  # Calculate relative topic shares and odds-ratio / enrichment
  topic_totals <- funder_project_topics %>%
    group_by(topic_or_subject) %>%
    summarise(
      ekfs_projects = sum(project_count[funder == "EKFS"]),
      dfg_projects = sum(project_count[funder == "DFG"]),
      total_projects = sum(project_count),
      .groups = "drop"
    ) %>%
    mutate(
      ekfs_share = round(ekfs_projects / pmax(sum(ekfs_projects), 1), 4),
      dfg_share = round(dfg_projects / pmax(sum(dfg_projects), 1), 4),
      funder_ratio = round((ekfs_share + 1e-4) / (dfg_share + 1e-4), 2),
      predominant_funder = case_when(
        funder_ratio > 1.5 ~ "EKFS Enriched",
        funder_ratio < 0.67 ~ "DFG Enriched",
        TRUE ~ "Balanced"
      )
    ) %>%
    arrange(desc(total_projects))
  
  # 2. Publication Topic Distribution (OpenAlex modern taxonomy)
  pub_topics <- publications_df %>%
    filter(!is.na(primary_topic) & primary_topic != "") %>%
    group_by(primary_topic) %>%
    summarise(
      publication_count = n(),
      total_citations = sum(cited_by_count, na.rm = TRUE),
      mean_year = round(mean(publication_year, na.rm = TRUE), 1),
      .groups = "drop"
    ) %>%
    arrange(desc(publication_count))
  
  # 3. Topic Distribution by Institution
  inst_topics <- project_researchers %>%
    inner_join(researchers_df %>% select(researcher_id, institution), by = "researcher_id") %>%
    inner_join(projects_df %>% select(project_id, topic_or_subject, funder), by = "project_id") %>%
    filter(!is.na(institution) & institution != "") %>%
    group_by(institution, topic_or_subject) %>%
    summarise(
      project_count = n(),
      .groups = "drop"
    ) %>%
    arrange(institution, desc(project_count))
  
  # 4. Temporal Topic Evolution
  temporal_topics <- projects_df %>%
    group_by(funding_year, funder, topic_or_subject) %>%
    summarise(project_count = n(), .groups = "drop") %>%
    arrange(funding_year, funder, desc(project_count))
  
  return(list(
    funder_project_topics = funder_project_topics,
    topic_enrichment = topic_totals,
    publication_topics = pub_topics,
    institution_topics = inst_topics,
    temporal_topics = temporal_topics
  ))
}
