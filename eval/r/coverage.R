# How many categories cover how much of the repairs, shared by eval/categorizer/coverage.R and
# eval/ora/coverage.R. Needs eval/r/theme.R.
#
#   curve <- coverage_curve(counts)          counts has name and n, one row per category
#   marks <- coverage_marks(curve, "Kategorien")
#   coverage_plot(curve, marks, ...)         the chart with table and examples, wide or square

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
})

de <- function(x, digits = 0) formatC(x, format = "f", digits = digits, big.mark = ".", decimal.mark = ",")
wrap <- function(parts, width) paste(unlist(lapply(parts, strwrap, width = width)), collapse = "\n")

coverage_curve <- function(counts) {
  counts |>
    arrange(desc(n), name) |>
    mutate(rank = row_number(), share = cumsum(n) / sum(n))
}

# 80 percent, the limit of class A, and every percent from 90
coverage_marks <- function(curve, unit) {
  reach <- function(level) min(curve$rank[curve$share >= level - 1e-9])
  tibble(level = c(0.80, seq(90, 100) / 100)) |>
    mutate(rank = vapply(level, reach, integer(1)),
           label = paste0(de(100 * level), " % mit ", de(rank), " ", unit))
}

# Numbers for the text, the same measures for every chart
coverage_facts <- function(curve, marks) {
  bind_rows(
    tibble(measure = c("categories", "entries", "categories_without_entries", "categories_below_10_entries",
                       "categories_with_one_entry"),
           value = c(nrow(curve), sum(curve$n), sum(curve$n == 0), sum(curve$n < 10), sum(curve$n == 1))),
    transmute(marks, measure = paste0("categories_for_", 100 * level, "_percent"), value = rank)
  )
}

# The step curve of categories against the share of repairs. The curve labels 80, 90 and 100 percent,
# a table lists every percent from 90. Positions of table and examples are given as shares of the
# height, so the chart works for a few dozen categories as well as for thousands.
coverage_plot <- function(curve, marks, unit, title, subtitle, caption, y_label, top_text, rare_text,
                          square = FALSE) {
  top <- max(curve$rank) * 1.06
  cols <- if (square) c(0.09, 0.27) else c(0.06, 0.17)
  table <- filter(marks, level >= 0.90) |>
    mutate(y = top * (0.867 - (row_number() - 1) * 0.0537))
  curve_labels <- filter(marks, level %in% c(0.80, 0.90, 1))
  ggplot(curve, aes(share, rank)) +
    geom_vline(xintercept = c(0.8, 0.9, 1), colour = light[["grid"]], linewidth = 0.4) +
    geom_step(colour = light[["s1"]], linewidth = 0.9, direction = "vh") +
    geom_point(data = marks, aes(level, rank), size = 2.2, colour = light[["s1"]], fill = light[["bg"]],
               shape = 21, stroke = 1.4) +
    geom_text(data = curve_labels, aes(level, rank, label = label), hjust = 1.06, vjust = -0.7, size = 3.6,
              colour = light[["secondary"]]) +
    annotate("rect", xmin = 0, xmax = cols[2] + 0.02, ymin = top * 0.286, ymax = top * 0.962,
             fill = light[["bg"]]) +
    annotate("text", x = cols[1], y = top * 0.93, label = "Anteil", hjust = 1, size = 3.6,
             colour = light[["primary"]], fontface = "bold") +
    annotate("text", x = cols[2], y = top * 0.93, label = unit, hjust = 1, size = 3.6,
             colour = light[["primary"]], fontface = "bold") +
    geom_text(data = table, aes(cols[1], y, label = paste0(de(100 * level), " %")), hjust = 1, size = 3.6,
              colour = light[["secondary"]]) +
    geom_text(data = table, aes(cols[2], y, label = de(rank)), hjust = 1, size = 3.6,
              colour = light[["secondary"]]) +
    annotate("text", x = 0.03, y = top * 0.082, label = wrap(top_text, if (square) 40 else 60), hjust = 0,
             vjust = 0, size = 3.6, lineheight = 1.1, colour = light[["primary"]]) +
    annotate("text", x = 0.94, y = top * 0.763, label = wrap(rare_text, if (square) 40 else 60), hjust = 1,
             size = 3.6, lineheight = 1.1, colour = light[["primary"]]) +
    scale_x_continuous(labels = \(x) paste0(de(100 * x), " %"), breaks = seq(0, 1, 0.2),
                       limits = c(0, 1.01), expand = expansion(mult = c(0, 0))) +
    scale_y_continuous(breaks = scales::breaks_pretty(5), labels = \(x) de(x),
                       limits = c(0, top), expand = expansion(mult = c(0, 0))) +
    labs(title = title,
         subtitle = if (square) wrap(subtitle, 78) else paste(subtitle, collapse = "\n"),
         x = "Anteil der Reparaturen", y = y_label,
         caption = if (square) wrap(caption, 125) else paste(caption, collapse = "\n")) +
    theme_manuel()
}

# "A mit 1, B mit 2 und C mit 3"
coverage_list <- function(rows) {
  items <- paste(rows$name, "mit", de(rows$n))
  if (length(items) == 1) return(items)
  paste(paste(items[-length(items)], collapse = ", "), "und", items[length(items)])
}
