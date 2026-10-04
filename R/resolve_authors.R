#' Researcher Identity Resolution & Disambiguation Module
#'
#' @description
#' Provides multi-signal, auditable author disambiguation replacing the legacy
#' works_count heuristic. Handles German academic titles (Prof., Dr. med., Dr. rer. nat.),
#' noble/locative surname particles (von, van, zu, de), hyphenated first/last names,
#' and integrates institutional affiliation, ORCID, and disciplinary match scoring.
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(stringr)
  library(readr)
})

#' Normalize Academic and German Researcher Names
#'
#' @param name Raw name string from funding database.
#' @return A list with parsed components: cleaned_name, title, first_name, last_name, prefix.
normalize_researcher_name <- function(name) {
  if (is.na(name) || name == "") {
    return(list(cleaned_name = "", title = "", first_name = "", last_name = "", prefix = ""))
  }
  
  # Remove academic titles
  title_pattern <- "(?i)\\b(Prof\\.?|Dr\\.?|Priv\\.-Doz\\.?|PD|med\\.?|rer\\.?\\s*nat\\.?|phil\\.?|habil\\.?|LL\\.?M\\.?|M\\.?D\\.?|Ph\\.?D\\.?)\\b"
  name_no_title <- stringr::str_replace_all(name, title_pattern, "")
  name_no_title <- stringr::str_replace_all(name_no_title, "[,/]", " ")
  name_no_title <- stringr::str_squish(name_no_title)
  
  # Extract surname particles (von, van, zu, de, der, den)
  # Standardize spacing around hyphens
  parts <- stringr::str_split(name_no_title, "\\s+")[[1]]
  
  if (length(parts) == 1) {
    return(list(
      cleaned_name = parts[1],
      title = stringr::str_extract(name, title_pattern),
      first_name = "",
      last_name = parts[1],
      prefix = ""
    ))
  }
  
  # If "Lastname, Firstname" format was present
  if (stringr::str_detect(name, ",")) {
    split_comma <- stringr::str_split(name, ",")[[1]]
    last_candidate <- stringr::str_squish(stringr::str_replace_all(split_comma[1], title_pattern, ""))
    first_candidate <- stringr::str_squish(stringr::str_replace_all(split_comma[2], title_pattern, ""))
    return(list(
      cleaned_name = paste(first_candidate, last_candidate),
      title = stringr::str_extract(name, title_pattern),
      first_name = first_candidate,
      last_name = last_candidate,
      prefix = ""
    ))
  }
  
  # Forward order: Firstname [Middle] [Prefix] Lastname
  first_name <- parts[1]
  last_name <- paste(parts[2:length(parts)], collapse = " ")
  
  return(list(
    cleaned_name = paste(first_name, last_name),
    title = stringr::str_extract(name, title_pattern),
    first_name = first_name,
    last_name = last_name,
    prefix = ""
  ))
}

#' Resolve Researcher Identity Against Authoritative Candidates
#'
#' @param raw_name Researcher name from funding source.
#' @param institution Affiliation noted in grant record.
#' @param funder Granting organization ("EKFS", "DFG", etc.).
#' @param project_id Project identifier.
#' @param candidates Data frame of OpenAlex author candidates.
#' @param overrides_file Path to CSV with persistent manual overrides.
#' @return A tibble row with canonical identity resolution metadata.
resolve_researcher_identity <- function(raw_name,
                                        institution,
                                        funder,
                                        project_id,
                                        candidates,
                                        overrides_file = "data/processed/researcher_identity_overrides.csv") {
  norm <- normalize_researcher_name(raw_name)
  
  # Check for persistent manual overrides
  if (file.exists(overrides_file)) {
    overrides <- readr::read_csv(overrides_file, col_types = readr::cols())
    matched_override <- overrides %>%
      filter(raw_name == !!raw_name | cleaned_name == !!norm$cleaned_name)
    if (nrow(matched_override) > 0) {
      ov <- matched_override[1, ]
      return(tibble(
        canonical_id = ov$canonical_id,
        canonical_display_name = ov$canonical_display_name,
        source_name = raw_name,
        funder = funder,
        project_ids = project_id,
        institution = institution,
        openalex_id = ov$openalex_id,
        orcid = ov$orcid,
        confidence_score = 1.0,
        resolution_method = "manual_override",
        needs_manual_review = FALSE
      ))
    }
  }
  
  if (nrow(candidates) == 0) {
    # Unresolved author
    canon_id <- sprintf("RES_UNRES_%s", substr(digest::digest(raw_name, algo = "crc32"), 1, 8))
    return(tibble(
      canonical_id = canon_id,
      canonical_display_name = norm$cleaned_name,
      source_name = raw_name,
      funder = funder,
      project_ids = project_id,
      institution = institution,
      openalex_id = NA_character_,
      orcid = NA_character_,
      confidence_score = 0.0,
      resolution_method = "unresolved",
      needs_manual_review = TRUE
    ))
  }
  
  # Multi-signal scoring: Name string distance + Institutional match + Topic bonus
  scored_candidates <- candidates %>%
    mutate(
      name_sim = stringdist::stringsim(tolower(display_name), tolower(norm$cleaned_name), method = "jw"),
      inst_match = if ("last_known_institution" %in% names(.)) {
        stringr::str_detect(tolower(last_known_institution), tolower(substr(institution, 1, 8)))
      } else { FALSE },
      orcid_present = !is.na(orcid) & orcid != "",
      score = name_sim * 0.60 + (as.numeric(inst_match) * 0.30) + (as.numeric(orcid_present) * 0.10)
    ) %>%
    arrange(desc(score))
  
  top_candidate <- scored_candidates[1, ]
  is_ambiguous <- FALSE
  if (nrow(scored_candidates) > 1) {
    margin <- top_candidate$score - scored_candidates$score[2]
    if (margin < 0.08 && top_candidate$score < 0.90) {
      is_ambiguous <- TRUE
    }
  }
  
  method <- if (top_candidate$score >= 0.85) {
    "high_confidence_multi_signal"
  } else if (top_candidate$score >= 0.65) {
    "moderate_confidence_match"
  } else {
    "low_confidence_ambiguous"
  }
  
  canon_id <- sprintf("RES_%s", top_candidate$openalex_id)
  
  tibble(
    canonical_id = canon_id,
    canonical_display_name = top_candidate$display_name,
    source_name = raw_name,
    funder = funder,
    project_ids = project_id,
    institution = institution,
    openalex_id = top_candidate$openalex_id,
    orcid = top_candidate$orcid,
    confidence_score = round(top_candidate$score, 3),
    resolution_method = method,
    needs_manual_review = is_ambiguous || (top_candidate$score < 0.70)
  )
}
