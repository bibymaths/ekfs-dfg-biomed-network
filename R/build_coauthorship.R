#' Coauthorship Network Construction Module
#'
#' @description
#' Builds weighted coauthorship networks supporting both cohort-induced and
#' expanded collaboration topologies. Weight corresponds to the number of coauthored
#' papers within the publication window.
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(igraph)
  library(tidyr)
})

#' Build Coauthorship Network Edges and Graph
#'
#' @param publication_authors Data frame with work_id and researcher_id.
#' @param researchers Data frame of target researchers.
#' @param mode Character: "cohort" (cohort-induced) or "expanded" (includes external coauthors).
#' @return A list containing `edge_list` tibble and `igraph` object.
build_coauthorship_network <- function(publication_authors,
                                       researchers,
                                       mode = "cohort") {
  message(sprintf("Building coauthorship network in mode: %s", mode))
  
  cohort_ids <- researchers$researcher_id
  
  # Join publication authors to find coauthor pairs
  pairs <- publication_authors %>%
    inner_join(publication_authors, by = "work_id", relationship = "many-to-many") %>%
    filter(researcher_id.x < researcher_id.y) %>% # undirected pairs
    rename(from = researcher_id.x, to = researcher_id.y)
  
  if (mode == "cohort") {
    pairs <- pairs %>%
      filter(from %in% cohort_ids & to %in% cohort_ids)
  } else if (mode == "expanded") {
    pairs <- pairs %>%
      filter(from %in% cohort_ids | to %in% cohort_ids)
  } else {
    stop("Unknown network mode. Choose 'cohort' or 'expanded'.")
  }
  
  # Aggregate weights: shared publication count
  edge_list <- pairs %>%
    group_by(from, to) %>%
    summarise(
      weight = n(),
      shared_works = paste(unique(work_id), collapse = ";"),
      .groups = "drop"
    ) %>%
    arrange(desc(weight))
  
  # Vertex set
  all_active_nodes <- unique(c(edge_list$from, edge_list$to))
  if (mode == "cohort") {
    node_set <- researchers %>% filter(researcher_id %in% cohort_ids)
  } else {
    node_set <- researchers %>% filter(researcher_id %in% all_active_nodes)
  }
  
  # Construct igraph
  g <- igraph::graph_from_data_frame(
    d = edge_list,
    directed = FALSE,
    vertices = node_set
  )
  
  message(sprintf("Constructed graph with %d vertices and %d edges.",
                  igraph::vcount(g), igraph::ecount(g)))
  
  return(list(
    edge_list = edge_list,
    graph = g
  ))
}
