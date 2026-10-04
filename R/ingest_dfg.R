#' DFG GEPRIS Project Ingestion Module
#'
#' @description
#' Ingestion adapters for Deutsche Forschungsgemeinschaft (DFG) project data
#' derived from the official GEPRIS database. Supports filtering by DFG programme,
#' subject classification (Life Sciences), funding period, and participating institution.
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})

#' Ingest DFG GEPRIS Project Data
#'
#' @param file_path Path to a structured CSV/TSV snapshot file.
#' @param config List of configuration parameters from config.yaml.
#' @return A tibble of raw DFG GEPRIS records.
ingest_dfg_projects <- function(file_path = "data/raw/dfg/dfg_gepris_snapshot.csv",
                                config = NULL) {
  if (!file.exists(file_path)) {
    stop(sprintf("DFG data file not found at %s. Please provide a valid snapshot.", file_path))
  }
  
  message(sprintf("Ingesting DFG GEPRIS projects from: %s", file_path))
  
  df <- readr::read_csv(
    file_path,
    col_types = readr::cols(
      dfg_project_number = readr::col_character(),
      project_id = readr::col_character(),
      title = readr::col_character(),
      applicants_pi = readr::col_character(),
      participating_investigators = readr::col_character(),
      participating_institutions = readr::col_character(),
      programme = readr::col_character(),
      subject_classification = readr::col_character(),
      research_area = readr::col_character(),
      start_date = readr::col_character(),
      end_date = readr::col_character(),
      funding_year = readr::col_integer(),
      description = readr::col_character(),
      source_url = readr::col_character(),
      retrieval_date = readr::col_character()
    )
  )
  
  # Cohort filtering based on configuration
  if (!is.null(config) && !is.null(config$funders$dfg)) {
    dfg_cfg <- config$funders$dfg
    if (!is.null(dfg_cfg$years) && !identical(dfg_cfg$years, "all")) {
      df <- df %>% filter(funding_year %in% dfg_cfg$years)
    }
    if (!is.null(dfg_cfg$programmes) && !identical(dfg_cfg$programmes, "all")) {
      df <- df %>% filter(programme %in% dfg_cfg$programmes)
    }
    if (!is.null(dfg_cfg$subject_classifications) && !identical(dfg_cfg$subject_classifications, "all")) {
      df <- df %>% filter(subject_classification %in% dfg_cfg$subject_classifications)
    }
    if (!is.null(dfg_cfg$research_area) && !identical(dfg_cfg$research_area, "all")) {
      df <- df %>% filter(tolower(research_area) == tolower(dfg_cfg$research_area))
    }
  }
  
  df <- df %>%
    mutate(
      funder = "DFG",
      funder_name = "Deutsche Forschungsgemeinschaft"
    )
  
  message(sprintf("Loaded %d DFG GEPRIS projects after filtering.", nrow(df)))
  return(df)
}
