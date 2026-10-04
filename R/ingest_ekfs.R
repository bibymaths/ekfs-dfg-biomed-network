#' EKFS Project Database Ingestion Module
#'
#' @description
#' Provides ingestion adapters for the Else Kröner-Fresenius-Stiftung (EKFS)
#' scientific project database. Supports loading from local cached snapshots,
#' structured CSV/TSV exports, and defensive web acquisition.
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})

#' Ingest EKFS Project Data
#'
#' @param file_path Path to a structured CSV/TSV/JSON snapshot file.
#' @param config List of configuration parameters from config.yaml.
#' @return A tibble of raw EKFS project records with standardized columns.
ingest_ekfs_projects <- function(file_path = "data/raw/ekfs/ekfs_projects_snapshot.csv",
                                 config = NULL) {
  if (!file.exists(file_path)) {
    stop(sprintf("EKFS data file not found at %s. Please provide a valid snapshot.", file_path))
  }
  
  message(sprintf("Ingesting EKFS projects from: %s", file_path))
  
  df <- readr::read_csv(
    file_path,
    col_types = readr::cols(
      project_id = readr::col_character(),
      title = readr::col_character(),
      principal_investigator = readr::col_character(),
      partner_investigators = readr::col_character(),
      institution = readr::col_character(),
      funding_line = readr::col_character(),
      topic = readr::col_character(),
      status = readr::col_character(),
      year = readr::col_integer(),
      start_date = readr::col_character(),
      end_date = readr::col_character(),
      description = readr::col_character(),
      source_url = readr::col_character(),
      retrieval_date = readr::col_character()
    )
  )
  
  # Apply cohort filters if configuration provided
  if (!is.null(config) && !is.null(config$funders$ekfs)) {
    ekfs_cfg <- config$funders$ekfs
    if (!is.null(ekfs_cfg$years) && !identical(ekfs_cfg$years, "all")) {
      df <- df %>% filter(year %in% ekfs_cfg$years)
    }
    if (!is.null(ekfs_cfg$funding_lines) && !identical(ekfs_cfg$funding_lines, "all")) {
      df <- df %>% filter(funding_line %in% ekfs_cfg$funding_lines)
    }
    if (!is.null(ekfs_cfg$topics) && !identical(ekfs_cfg$topics, "all")) {
      df <- df %>% filter(topic %in% ekfs_cfg$topics)
    }
    if (!is.null(ekfs_cfg$status) && !identical(ekfs_cfg$status, "all")) {
      df <- df %>% filter(tolower(status) == tolower(ekfs_cfg$status))
    }
  }
  
  df <- df %>%
    mutate(
      funder = "EKFS",
      funder_name = "Else Kröner-Fresenius-Stiftung"
    )
  
  message(sprintf("Loaded %d EKFS projects after filtering.", nrow(df)))
  return(df)
}
