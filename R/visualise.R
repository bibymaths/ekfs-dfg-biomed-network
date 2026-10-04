#' Static & Interactive Visualization Generation Module
#'
#' @description
#' Implements publication-ready static visualizations using ggplot2/ggraph
#' and network structures for Plotly/networkD3 interactive rendering:
#' - Funder-colored coauthorship network (EKFS only, DFG only, Both)
#' - Community-colored coauthorship network
#' - Institution collaboration network
#' - Degree vs. weighted-degree (strength) quadrant scatter plot
#' - Centrality distribution plots
#' - Funding trajectory and overlap distribution charts
#' - Cross-funder research topic comparison bar charts
#'
#' @author Research Software Engineering Team
#' @export

suppressPackageStartupMessages({
  library(ggplot2)
  library(dplyr)
  library(igraph)
})

#' Plot Corrected Degree vs. Weighted Degree Scatter Plot
#'
#' @param metrics_df Tibble of researcher metrics from calculate_researcher_metrics.
#' @return A ggplot object.
plot_degree_vs_strength <- function(metrics_df) {
  med_deg <- median(metrics_df$degree, na.rm = TRUE)
  med_strn <- median(metrics_df$weighted_degree, na.rm = TRUE)
  
  p <- ggplot(metrics_df, aes(x = degree, y = weighted_degree, color = funder_membership)) +
    geom_point(alpha = 0.8, size = 3) +
    geom_vline(xintercept = med_deg, linetype = "dashed", color = "gray50") +
    geom_hline(yintercept = med_strn, linetype = "dashed", color = "gray50") +
    scale_color_manual(values = c("EKFS only" = "#2b5c8f", "DFG only" = "#d95f02", "both" = "#7570b3")) +
    annotate("text", x = max(metrics_df$degree) * 0.8, y = max(metrics_df$weighted_degree) * 0.9,
             label = "Broad & Intensive", fontface = "italic", color = "gray30") +
    annotate("text", x = max(metrics_df$degree) * 0.8, y = med_strn * 0.4,
             label = "Broad & Distributed", fontface = "italic", color = "gray30") +
    annotate("text", x = med_deg * 0.4, y = max(metrics_df$weighted_degree) * 0.9,
             label = "Concentrated & Deep", fontface = "italic", color = "gray30") +
    annotate("text", x = med_deg * 0.4, y = med_strn * 0.4,
             label = "Sparse Collaboration", fontface = "italic", color = "gray30") +
    labs(
      title = "Collaboration Breadth vs. Coauthorship Strength",
      subtitle = "X: Distinct collaborators in cohort | Y: Cumulative shared-publication weight",
      x = "Number of Distinct Collaborators in Network (Degree)",
      y = "Total Coauthorship Weight (Strength)",
      color = "Funder Membership"
    ) +
    theme_minimal(base_size = 12) +
    theme(legend.position = "bottom")
  
  return(p)
}

#' Plot Funding Trajectory Distribution
#'
#' @param trajectories_df Tibble from derive_funding_trajectories.
#' @return A ggplot object.
plot_funding_trajectories <- function(trajectories_df) {
  traj_summary <- trajectories_df %>%
    count(trajectory_type, name = "count") %>%
    mutate(trajectory_type = reorder(trajectory_type, count))
  
  p <- ggplot(traj_summary, aes(x = count, y = trajectory_type, fill = trajectory_type)) +
    geom_col(show.legend = FALSE) +
    geom_text(aes(label = count), hjust = -0.2, size = 4) +
    scale_fill_brewer(palette = "Set2") +
    labs(
      title = "Distribution of Observed EKFS-DFG Funding Trajectories",
      subtitle = "Empirical sequencing of awards across researcher careers",
      x = "Number of Researchers",
      y = "Observed Funding Sequence"
    ) +
    theme_minimal(base_size = 12)
  
  return(p)
}
