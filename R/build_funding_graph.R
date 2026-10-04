#' Multi-Layer Funding and Institutional Network Builder Module
#'
#' @description
#' Constructs multi-layer graph structures linking researchers, projects,
#' institutions, and funding agencies:
#' 1. Researcher-Researcher shared project graph
#' 2. Researcher-Project bipartite network
#' 3. Project-Institution bipartite network
#' 4. Researcher-Funder bipartite network
#' 5. Institution-Institution collaboration network (coauthorships + shared grants)
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(igraph)
  library(tidyr)
})

#' Build Funding and Multilayer Networks
#'
#' @param project_researchers Tibble linking project_id and researcher_id.
#' @param projects Tibble of projects with metadata.
#' @param researchers Tibble of researchers with metadata.
#' @param coauthorship_edges Tibble of coauthorship edges.
#' @return A list of edge lists and igraph objects representing each network layer.
build_funding_networks <- function(project_researchers,
                                   projects,
                                   researchers,
                                   coauthorship_edges) {
  message("Building funding-aware multilayer network representations...")
  
  # 1. Researcher-Project Bipartite Network
  bipartite_edges <- project_researchers %>%
    inner_join(projects %>% select(project_id, funder, programme_or_funding_line, funding_year), by = "project_id") %>%
    transmute(
      from = researcher_id,
      to = project_id,
      funder = funder,
      programme = programme_or_funding_line,
      year = funding_year,
      edge_type = "funded_by_project"
    )
  
  # 2. Researcher-Researcher Shared Project Edges (Co-PI / Collaborating PI on same grant)
  shared_project_pairs <- project_researchers %>%
    inner_join(project_researchers, by = "project_id", relationship = "many-to-many") %>%
    filter(researcher_id.x < researcher_id.y) %>%
    inner_join(projects %>% select(project_id, funder), by = "project_id") %>%
    group_by(from = researcher_id.x, to = researcher_id.y) %>%
    summarise(
      shared_grant_count = n(),
      shared_projects = paste(unique(project_id), collapse = ";"),
      shared_funders = paste(unique(funder), collapse = ";"),
      .groups = "drop"
    ) %>%
    mutate(edge_type = "shared_grant")
  
  # 3. Multiplex Researcher-Researcher Edges (combining coauthorship + shared grant)
  full_rr_edges <- full_join(
    coauthorship_edges %>% select(from, to, coauthor_weight = weight),
    shared_project_pairs %>% select(from, to, shared_grant_count, shared_funders),
    by = c("from", "to")
  ) %>%
    mutate(
      coauthor_weight = coalesce(coauthor_weight, 0),
      shared_grant_count = coalesce(shared_grant_count, 0),
      has_coauthorship = coauthor_weight > 0,
      has_shared_grant = shared_grant_count > 0,
      relationship_type = case_when(
        has_coauthorship & has_shared_grant ~ "coauthor_and_grant",
        has_coauthorship & !has_shared_grant ~ "coauthor_only",
        !has_coauthorship & has_shared_grant ~ "grant_only",
        TRUE ~ "none"
      )
    )
  
  # 4. Institution Collaboration Network
  # Join researchers to their institutions
  res_inst <- researchers %>% select(researcher_id, institution)
  
  inst_coauth_pairs <- coauthorship_edges %>%
    inner_join(res_inst, by = c("from" = "researcher_id")) %>%
    rename(inst_from = institution) %>%
    inner_join(res_inst, by = c("to" = "researcher_id")) %>%
    rename(inst_to = institution) %>%
    filter(inst_from != inst_to) %>%
    mutate(
      inst_a = pmin(inst_from, inst_to),
      inst_b = pmax(inst_from, inst_to)
    ) %>%
    group_by(from = inst_a, to = inst_b) %>%
    summarise(
      coauthored_publication_weight = sum(weight),
      cross_institution_researcher_pairs = n(),
      .groups = "drop"
    )
  
  inst_grant_pairs <- shared_project_pairs %>%
    inner_join(res_inst, by = c("from" = "researcher_id")) %>%
    rename(inst_from = institution) %>%
    inner_join(res_inst, by = c("to" = "researcher_id")) %>%
    rename(inst_to = institution) %>%
    filter(inst_from != inst_to) %>%
    mutate(
      inst_a = pmin(inst_from, inst_to),
      inst_b = pmax(inst_from, inst_to)
    ) %>%
    group_by(from = inst_a, to = inst_b) %>%
    summarise(
      shared_grant_projects = sum(shared_grant_count),
      .groups = "drop"
    )
  
  inst_edges <- full_join(inst_coauth_pairs, inst_grant_pairs, by = c("from", "to")) %>%
    mutate(
      coauthored_publication_weight = coalesce(coauthored_publication_weight, 0),
      cross_institution_researcher_pairs = coalesce(cross_institution_researcher_pairs, 0),
      shared_grant_projects = coalesce(shared_grant_projects, 0),
      total_institutional_tie_strength = coauthored_publication_weight + (shared_grant_projects * 2)
    ) %>%
    arrange(desc(total_institutional_tie_strength))
  
  return(list(
    researcher_project_bipartite = bipartite_edges,
    shared_project_pairs = shared_project_pairs,
    multiplex_researcher_edges = full_rr_edges,
    institution_edges = inst_edges
  ))
}
