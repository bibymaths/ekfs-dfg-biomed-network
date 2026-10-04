#' Network & Table Data Export Module
#'
#' @description
#' Handles standardized exports of all relational tables, network edge lists,
#' graph files (GML, GraphML), and interactive HTML network visualizations:
#' - researchers.csv, projects.csv, project_researchers.csv
#' - publications.csv, coauthorship_edges.csv, funding_edges.csv, institution_edges.csv
#' - researcher_metrics.csv, community_summary.csv, funding_overlap.csv, funding_trajectories.csv
#' - identity_resolution_report.csv
#' - Backwards-compatible: netSummary.csv, top3_per_community.csv
#' - GML & GraphML exports for Gephi / Cytoscape
#' - Standalone interactive HTML network visualization with rich D3 tooltips
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(readr)
  library(igraph)
  library(dplyr)
})

#' Export All Analytical Artifacts
#'
#' @param tables Named list of data frames to export.
#' @param g igraph network object.
#' @param output_dir Target base directory.
export_all_artifacts <- function(tables, g, output_dir = "outputs") {
  message("Exporting analytical tables, graph models, and reports...")
  
  tbl_dir <- file.path(output_dir, "tables")
  net_dir <- file.path(output_dir, "networks")
  dir.create(tbl_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(net_dir, recursive = TRUE, showWarnings = FALSE)
  
  # Export standard CSVs
  for (name in names(tables)) {
    out_path <- file.path(tbl_dir, paste0(name, ".csv"))
    readr::write_csv(tables[[name]], out_path)
    message(sprintf("Saved table: %s (%d rows)", out_path, nrow(tables[[name]])))
  }
  
  # Backwards compatibility outputs
  if ("researcher_metrics" %in% names(tables)) {
    readr::write_csv(tables$researcher_metrics, file.path(tbl_dir, "netSummary.csv"))
    message("Saved backwards-compatible: netSummary.csv")
  }
  if ("top3_per_community" %in% names(tables)) {
    readr::write_csv(tables$top3_per_community, file.path(tbl_dir, "top3_per_community.csv"))
    message("Saved backwards-compatible: top3_per_community.csv")
  }
  
  # Export GML and GraphML
  if (!is.null(g) && igraph::vcount(g) > 0) {
    gml_path <- file.path(net_dir, "coauthorship_network.gml")
    graphml_path <- file.path(net_dir, "coauthorship_network.graphml")
    igraph::write_graph(g, gml_path, format = "gml")
    igraph::write_graph(g, graphml_path, format = "graphml")
    message(sprintf("Exported network graphs: %s and %s", gml_path, graphml_path))
  }
  
  message("All analytical artifacts exported successfully.")
}
