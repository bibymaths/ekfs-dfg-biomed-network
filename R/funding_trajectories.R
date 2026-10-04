#' Funding Overlap, Trajectories & Eligibility Screening Module
#'
#' @description
#' Analyzes the intersection between EKFS and DFG funding histories:
#' - Quantitative overlap statistics (Jaccard coefficient, counts, shares)
#' - Temporal funding trajectories (EKFS -> DFG, DFG -> EKFS, concurrent, multi-phase)
#' - Observed time intervals between initial and subsequent awards
#' - Factual funding-history screening view relevant to EKFS eligibility constraints
#'   (explicitly flagged as an informational aid, NOT an authoritative decision)
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(tibble)
})

#' Compute Funder Overlap Statistics
#'
#' @param researchers Tibble of researchers with funder_membership.
#' @param projects Tibble of projects.
#' @param project_researchers Tibble linking project to researcher.
#' @return A list with overall overlap summary, overlap by institution, and overlap by topic.
calculate_funding_overlap <- function(researchers, projects, project_researchers) {
  message("Computing EKFS-DFG overlap metrics...")
  
  res_projects <- project_researchers %>%
    inner_join(projects, by = "project_id")
  
  ekfs_res <- res_projects %>% filter(funder == "EKFS") %>% pull(researcher_id) %>% unique()
  dfg_res  <- res_projects %>% filter(funder == "DFG") %>% pull(researcher_id) %>% unique()
  
  both_res <- intersect(ekfs_res, dfg_res)
  all_res  <- union(ekfs_res, dfg_res)
  
  n_ekfs <- length(ekfs_res)
  n_dfg  <- length(dfg_res)
  n_both <- length(both_res)
  n_total <- length(all_res)
  
  jaccard_overlap <- round(n_both / n_total, 4)
  ekfs_overlap_share <- round(n_both / n_ekfs, 4)
  dfg_overlap_share  <- round(n_both / n_dfg, 4)
  
  overall_summary <- tibble(
    metric = c(
      "Total Unique Investigators",
      "EKFS Unique Investigators",
      "DFG Unique Investigators",
      "Investigators Funded by Both",
      "EKFS-Only Investigators",
      "DFG-Only Investigators",
      "Jaccard Overlap Index",
      "EKFS Cohort Overlap Share",
      "DFG Cohort Overlap Share"
    ),
    value = c(
      as.character(n_total),
      as.character(n_ekfs),
      as.character(n_dfg),
      as.character(n_both),
      as.character(n_ekfs - n_both),
      as.character(n_dfg - n_both),
      as.character(jaccard_overlap),
      sprintf("%.2f%%", ekfs_overlap_share * 100),
      sprintf("%.2f%%", dfg_overlap_share * 100)
    )
  )
  
  # Overlap by Institution
  inst_overlap <- researchers %>%
    filter(!is.na(institution) & institution != "") %>%
    group_by(institution) %>%
    summarise(
      total_researchers = n_distinct(researcher_id),
      ekfs_investigators = n_distinct(researcher_id[researcher_id %in% ekfs_res]),
      dfg_investigators = n_distinct(researcher_id[researcher_id %in% dfg_res]),
      both_investigators = n_distinct(researcher_id[researcher_id %in% both_res]),
      jaccard_index = round(both_investigators / pmax(ekfs_investigators + dfg_investigators - both_investigators, 1), 3),
      .groups = "drop"
    ) %>%
    arrange(desc(both_investigators), desc(total_researchers))
  
  return(list(
    overall_summary = overall_summary,
    institution_overlap = inst_overlap,
    both_researcher_ids = both_res
  ))
}

#' Classify Observed Funding Trajectories
#'
#' @param project_researchers Tibble linking project to researcher.
#' @param projects Tibble of projects with funding_year and funder.
#' @param researchers Tibble of researchers.
#' @return A tibble with per-researcher temporal trajectories and interval analysis.
derive_funding_trajectories <- function(project_researchers, projects, researchers) {
  message("Deriving time-aware funding trajectories...")
  
  res_grants <- project_researchers %>%
    inner_join(projects, by = "project_id") %>%
    select(researcher_id, funder, funding_year, programme_or_funding_line, project_id)
  
  # For each researcher, identify grant timelines
  traj_list <- res_grants %>%
    group_by(researcher_id) %>%
    summarise(
      has_ekfs = "EKFS" %in% funder,
      has_dfg = "DFG" %in% funder,
      ekfs_years = list(funding_year[funder == "EKFS"]),
      dfg_years = list(funding_year[funder == "DFG"]),
      first_ekfs_year = if (has_ekfs) min(funding_year[funder == "EKFS"], na.rm = TRUE) else NA_integer_,
      last_ekfs_year  = if (has_ekfs) max(funding_year[funder == "EKFS"], na.rm = TRUE) else NA_integer_,
      first_dfg_year  = if (has_dfg) min(funding_year[funder == "DFG"], na.rm = TRUE) else NA_integer_,
      last_dfg_year   = if (has_dfg) max(funding_year[funder == "DFG"], na.rm = TRUE) else NA_integer_,
      dfg_grant_count = sum(funder == "DFG"),
      ekfs_grant_count = sum(funder == "EKFS"),
      dfg_programmes = paste(unique(programme_or_funding_line[funder == "DFG"]), collapse = "; "),
      ekfs_funding_lines = paste(unique(programme_or_funding_line[funder == "EKFS"]), collapse = "; "),
      .groups = "drop"
    ) %>%
    mutate(
      trajectory_type = case_when(
        has_ekfs & !has_dfg ~ "EKFS_Only",
        !has_ekfs & has_dfg ~ "DFG_Only",
        has_ekfs & has_dfg & first_dfg_year < first_ekfs_year & last_dfg_year > last_ekfs_year ~ "DFG_EKFS_DFG_MultiPhase",
        has_ekfs & has_dfg & last_dfg_year < first_ekfs_year ~ "DFG_preceding_EKFS",
        has_ekfs & has_dfg & first_ekfs_year < first_dfg_year ~ "EKFS_preceding_DFG",
        has_ekfs & has_dfg & first_ekfs_year == first_dfg_year ~ "Concurrent_Initial_Funding",
        TRUE ~ "Overlapping_Mixed"
      ),
      interval_years = case_when(
        trajectory_type == "DFG_preceding_EKFS" ~ first_ekfs_year - first_dfg_year,
        trajectory_type == "EKFS_preceding_DFG" ~ first_dfg_year - first_ekfs_year,
        trajectory_type %in% c("Concurrent_Initial_Funding", "DFG_EKFS_DFG_MultiPhase") ~ 0L,
        TRUE ~ NA_integer_
      ),
      # Factual screening view for EKFS Memorial Stipendien
      # Memorial Stipendien target young clinician scientists, typically restricted if already lead on large DFG grant
      observed_prior_dfg_grants = case_when(
        !has_dfg ~ 0L,
        !has_ekfs ~ dfg_grant_count,
        TRUE ~ as.integer(mapply(function(d_yrs, e_yr) sum(d_yrs < e_yr), dfg_years, first_ekfs_year))
      ),
      prior_dfg_programmes = dfg_programmes,
      screening_note = case_when(
        observed_prior_dfg_grants >= 1 & stringr::str_detect(prior_dfg_programmes, "Sachbeihilfe|Heisenberg|SFB") ~
          "Observed independent prior DFG project (Sachbeihilfe/major line); relevant for programs requiring prior third-party funding or junior restrictions.",
        observed_prior_dfg_grants == 0 & has_ekfs ~
          "No observed prior DFG funding in records; typical profile for junior clinician scientist lines.",
        TRUE ~ "Informational observation only."
      ),
      data_completeness_flag = "Observational records bounded by available GEPRIS and EKFS database snapshots. Not an official eligibility ruling."
    ) %>%
    left_join(researchers %>% select(researcher_id, display_name, institution), by = "researcher_id") %>%
    select(
      researcher_id,
      researcher = display_name,
      institution,
      trajectory_type,
      interval_years,
      has_ekfs,
      has_dfg,
      first_ekfs_year,
      first_dfg_year,
      ekfs_grant_count,
      dfg_grant_count,
      observed_prior_dfg_grants,
      prior_dfg_programmes,
      screening_note,
      data_completeness_flag
    )
  
  return(traj_list)
}
