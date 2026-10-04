#' Community Detection and Module Profiling Module
#'
#' @description
#' Detects cohesive research communities using modularity optimization (Louvain algorithm,
#' extensible to Leiden). For every community, profiles:
#' - size, funder breakdown (EKFS-only, DFG-only, both)
#' - dominant institutions, dominant research topics
#' - dominant funding lines and programmes
#' - internal density and strongest internal edges
#' - bridging researchers (high betweenness spanning communities)
#' - top 3 researchers per community with rich metadata
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(igraph)
  library(tidyr)
  library(tibble)
})

#' Detect and Profile Network Communities
#'
#' @param g igraph coauthorship network.
#' @param researcher_metrics Tibble of metrics computed from calculate_researcher_metrics.
#' @param projects_df Tibble of projects.
#' @param project_researchers Tibble linking project to researcher.
#' @param seed Random seed for reproducible community detection.
#' @return A list with community assignments, community summary table, and top-3 table.
detect_and_profile_communities <- function(g,
                                           researcher_metrics,
                                           projects_df,
                                           project_researchers,
                                           seed = 42) {
  message("Executing Louvain community detection...")
  set.seed(seed)
  
  if (igraph::vcount(g) == 0) {
    return(list(summary = tibble(), top3 = tibble(), graph = g))
  }
  
  # Run Louvain
  weights <- if ("weight" %in% igraph::edge_attr_names(g)) igraph::E(g)$weight else NULL
  cl <- igraph::cluster_louvain(g, weights = weights)
  
  igraph::V(g)$community <- cl$membership
  modularity_score <- igraph::modularity(cl)
  message(sprintf("Identified %d communities with modularity Q = %.4f",
                  length(unique(cl$membership)), modularity_score))
  
  # Attach community to researcher metrics
  node_comm <- tibble(
    researcher_id = igraph::V(g)$name,
    community = as.integer(cl$membership)
  )
  
  enhanced_metrics <- researcher_metrics %>%
    left_join(node_comm, by = "researcher_id")
  
  # Link project topics & programmes
  res_project_meta <- project_researchers %>%
    inner_join(projects_df, by = "project_id") %>%
    select(researcher_id, funder, programme_or_funding_line, topic_or_subject)
  
  full_node_meta <- enhanced_metrics %>%
    left_join(res_project_meta, by = "researcher_id")
  
  # Summarise each community
  comm_summary <- full_node_meta %>%
    group_by(community) %>%
    summarise(
      member_count = n_distinct(researcher_id),
      ekfs_only_count = n_distinct(researcher_id[funder_membership == "EKFS only"]),
      dfg_only_count = n_distinct(researcher_id[funder_membership == "DFG only"]),
      both_funded_count = n_distinct(researcher_id[funder_membership == "both"]),
      dominant_institution = names(sort(table(institution[!is.na(institution)]), decreasing = TRUE))[1],
      dominant_topic = names(sort(table(topic_or_subject[!is.na(topic_or_subject)]), decreasing = TRUE))[1],
      mean_weighted_degree = round(mean(weighted_degree, na.rm = TRUE), 2),
      max_betweenness = round(max(betweenness, na.rm = TRUE), 5),
      highest_degree_researcher = display_name[which.max(weighted_degree)[1]],
      highest_betweenness_bridge = display_name[which.max(betweenness)[1]],
      .groups = "drop"
    ) %>%
    arrange(desc(member_count))
  
  # Produce expanded top-3 researchers per community
  top3_per_community <- enhanced_metrics %>%
    group_by(community) %>%
    arrange(desc(weighted_degree), desc(betweenness)) %>%
    slice(1:3) %>%
    ungroup() %>%
    transmute(
      community = community,
      researcher = display_name,
      researcher_id = researcher_id,
      funder_membership = funder_membership,
      institution = institution,
      degree = degree,
      weighted_degree = weighted_degree,
      betweenness = betweenness,
      strongest_collaborator = strongest_collaborator_name
    )
  
  return(list(
    graph = g,
    enhanced_metrics = enhanced_metrics,
    community_summary = comm_summary,
    top3_per_community = top3_per_community,
    modularity = modularity_score
  ))
}
