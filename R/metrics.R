#' Network Centrality & Collaboration Profile Metrics Module
#'
#' @description
#' Computes rigorous topological and collaboration centrality metrics:
#' - degree: number of distinct collaborators
#' - weighted_degree / strength: cumulative coauthorship edge weight
#' - betweenness centrality
#' - eigenvector centrality
#' - closeness centrality (calculated within connected components)
#' - connected component membership
#' - strongest collaborator identification
#' - collaboration profile classification (broad-intensive, broad-distributed, concentrated-deep, sparse)
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(dplyr)
  library(igraph)
  library(tibble)
})

#' Compute Comprehensive Researcher Network Metrics
#'
#' @param g igraph network object.
#' @param researchers_df Data frame of researcher metadata.
#' @return A tibble with all researcher-level centrality and profile metrics.
calculate_researcher_metrics <- function(g, researchers_df) {
  message("Calculating network centrality metrics...")
  
  if (igraph::vcount(g) == 0) {
    return(tibble())
  }
  
  v_names <- igraph::V(g)$name
  
  # 1. Degree: Count of distinct collaborators in graph
  deg <- igraph::degree(g, mode = "all")
  
  # 2. Weighted Degree / Strength: Cumulative sum of shared publication weights
  if ("weight" %in% igraph::edge_attr_names(g)) {
    strn <- igraph::strength(g, weights = igraph::E(g)$weight)
  } else {
    strn <- deg
  }
  
  # 3. Betweenness Centrality (using inverse weights for shortest path distance)
  if ("weight" %in% igraph::edge_attr_names(g)) {
    inv_weights <- 1 / pmax(igraph::E(g)$weight, 1e-4)
    betw <- igraph::betweenness(g, weights = inv_weights, directed = FALSE, normalized = TRUE)
  } else {
    betw <- igraph::betweenness(g, directed = FALSE, normalized = TRUE)
  }
  
  # 4. Eigenvector Centrality
  eigen_res <- tryCatch({
    ev <- igraph::eigen_centrality(g, weights = if ("weight" %in% igraph::edge_attr_names(g)) igraph::E(g)$weight else NULL)
    ev$vector
  }, error = function(e) {
    rep(0, length(v_names))
  })
  
  # 5. Connected Components
  comp <- igraph::components(g)
  comp_membership <- comp$membership
  
  # 6. Closeness Centrality (meaningful within connected components)
  close_res <- tryCatch({
    igraph::closeness(g, normalized = TRUE)
  }, error = function(e) {
    rep(0, length(v_names))
  })
  
  # 7. Identify Strongest Collaborator for Each Node
  el <- igraph::as_data_frame(g, what = "edges")
  strongest_collab <- rep(NA_character_, length(v_names))
  strongest_weight <- rep(0, length(v_names))
  
  if (nrow(el) > 0) {
    # Combine (from, to) and (to, from)
    dir_el <- bind_rows(
      el %>% transmute(node = from, neighbor = to, w = weight),
      el %>% transmute(node = to, neighbor = from, w = weight)
    )
    
    top_neighbors <- dir_el %>%
      group_by(node) %>%
      arrange(desc(w)) %>%
      slice(1) %>%
      ungroup()
    
    match_idx <- match(v_names, top_neighbors$node)
    valid_mask <- !is.na(match_idx)
    strongest_collab[valid_mask] <- top_neighbors$neighbor[match_idx[valid_mask]]
    strongest_weight[valid_mask] <- top_neighbors$w[match_idx[valid_mask]]
  }
  
  # 8. Collaboration Profile Quadrant Classification
  # Based on median splits of degree and weighted degree (strength)
  med_deg <- median(deg, na.rm = TRUE)
  med_strn <- median(strn, na.rm = TRUE)
  
  profile_category <- case_when(
    deg >= med_deg & strn >= med_strn ~ "broad_intensive",
    deg >= med_deg & strn < med_strn  ~ "broad_distributed",
    deg < med_deg & strn >= med_strn  ~ "concentrated_deep",
    TRUE                              ~ "sparse_collaboration"
  )
  
  # Assemble Metrics Tibble
  metrics_tbl <- tibble(
    researcher_id = v_names,
    degree = as.integer(deg),
    weighted_degree = round(as.numeric(strn), 2),
    betweenness = round(as.numeric(betw), 5),
    eigenvector_centrality = round(as.numeric(eigen_res), 5),
    closeness = round(as.numeric(close_res), 5),
    component_id = as.integer(comp_membership),
    strongest_collaborator_id = strongest_collab,
    strongest_tie_weight = as.integer(strongest_weight),
    collaboration_profile = profile_category
  )
  
  # Merge with researcher display names and funder metadata
  if (!is.null(researchers_df)) {
    metrics_tbl <- metrics_tbl %>%
      left_join(
        researchers_df %>% select(researcher_id, display_name, institution, funder_membership),
        by = "researcher_id"
      ) %>%
      # Also resolve strongest collaborator display name
      left_join(
        researchers_df %>% select(researcher_id, strongest_collaborator_name = display_name),
        by = c("strongest_collaborator_id" = "researcher_id")
      )
  }
  
  message(sprintf("Metrics computed for %d nodes across %d connected components.",
                  nrow(metrics_tbl), comp$no))
  
  return(metrics_tbl)
}
