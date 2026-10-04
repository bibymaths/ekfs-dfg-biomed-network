#' Temporal Network Snapshots & Period Dynamics Module
#'
#' @description
#' Constructs multi-period network snapshots to examine the evolution of
#' collaboration and coauthorship across pre-funding, during-funding, and post-funding
#' temporal windows without making causal claims.
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(igraph)
  library(purrr)
})

#' Generate Multi-Period Temporal Network Snapshots
#'
#' @param publication_authors Tibble with work_id and researcher_id.
#' @param publications Tibble with work_id and publication_year.
#' @param researchers Tibble of researchers.
#' @param snapshot_configs List of snapshot specifications (e.g. from config.yaml).
#' @return A list of network metrics and summary statistics for each snapshot.
build_temporal_snapshots <- function(publication_authors,
                                     publications,
                                     researchers,
                                     snapshot_configs) {
  message("Building temporal network snapshots...")
  
  pub_with_year <- publication_authors %>%
    inner_join(publications %>% select(work_id, publication_year), by = "work_id")
  
  snapshot_results <- map(snapshot_configs, function(snap) {
    message(sprintf("Processing temporal window: %s [%d-%d]",
                    snap$label, snap$start_year, snap$end_year))
    
    # Filter publications to this temporal window
    window_pubs <- pub_with_year %>%
      filter(publication_year >= snap$start_year & publication_year <= snap$end_year)
    
    # Build coauthor edges within window
    pairs <- window_pubs %>%
      inner_join(window_pubs, by = "work_id", relationship = "many-to-many") %>%
      filter(researcher_id.x < researcher_id.y) %>%
      rename(from = researcher_id.x, to = researcher_id.y)
    
    # Restrict to cohort
    cohort_ids <- researchers$researcher_id
    cohort_pairs <- pairs %>%
      filter(from %in% cohort_ids & to %in% cohort_ids)
    
    edges <- cohort_pairs %>%
      group_by(from, to) %>%
      summarise(weight = n(), .groups = "drop")
    
    active_nodes <- unique(c(edges$from, edges$to))
    
    # Construct graph
    g_snap <- igraph::graph_from_data_frame(
      d = edges,
      directed = FALSE,
      vertices = researchers %>% filter(researcher_id %in% active_nodes)
    )
    
    dens <- if (igraph::vcount(g_snap) > 1) igraph::edge_density(g_snap) else 0
    comp <- if (igraph::vcount(g_snap) > 0) igraph::components(g_snap)$no else 0
    mean_deg <- if (igraph::vcount(g_snap) > 0) mean(igraph::degree(g_snap)) else 0
    
    list(
      name = snap$name,
      label = snap$label,
      start_year = snap$start_year,
      end_year = snap$end_year,
      node_count = igraph::vcount(g_snap),
      edge_count = igraph::ecount(g_snap),
      density = round(dens, 4),
      components = comp,
      mean_degree = round(mean_deg, 2),
      graph = g_snap,
      edges = edges
    )
  })
  
  # Summary table across periods
  summary_tbl <- map_df(snapshot_results, function(res) {
    tibble(
      period = res$name,
      label = res$label,
      years = sprintf("%d-%d", res$start_year, res$end_year),
      active_researchers = res$node_count,
      coauthorship_edges = res$edge_count,
      network_density = res$density,
      connected_components = res$components,
      mean_collaborator_degree = res$mean_degree
    )
  })
  
  return(list(
    snapshots = snapshot_results,
    summary = summary_tbl
  ))
}
