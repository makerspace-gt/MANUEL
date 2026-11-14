# ggplot2 theme in the style of eval/ora/charts.py, see docs/adr/0049-daten-mit-r-auswerten.adoc.
# save_chart() writes docs/grafiken/<name>.svg, which follows the colour scheme of the browser,
# and <name>-hell.svg, which stays light for the PDF of the case study. svglite writes colours as
# inline styles, so the dark version overrides them with attribute selectors in a media query.

suppressPackageStartupMessages({
  library(ggplot2)
  library(svglite)
})

light <- c(bg = "#FCFCFB", primary = "#0B0B0B", secondary = "#52514E", grid = "#E4E3DF",
           axis = "#B5B4AE", s0 = "#9A9992", s1 = "#2A78D6", s2 = "#EB6834")
dark <- c(bg = "#1A1A19", primary = "#F0EFEC", secondary = "#C3C2B7", grid = "#3A3A37",
          axis = "#5C5B55", s0 = "#75746E", s1 = "#3987E5", s2 = "#D95926")

theme_manuel <- function(base_size = 11) {
  theme_minimal(base_size = base_size, base_family = "sans") +
    theme(
      plot.background = element_rect(fill = light[["bg"]], colour = NA),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(colour = light[["grid"]], linewidth = 0.4),
      axis.line.x = element_line(colour = light[["axis"]], linewidth = 0.5),
      axis.text = element_text(colour = light[["secondary"]], size = base_size - 1),
      axis.title = element_text(colour = light[["secondary"]], size = base_size - 1),
      plot.title = element_text(colour = light[["primary"]], size = base_size + 5, face = "bold"),
      plot.subtitle = element_text(colour = light[["secondary"]], size = base_size + 1,
                                   margin = margin(b = 12)),
      plot.caption = element_text(colour = light[["secondary"]], size = base_size - 2, hjust = 0),
      strip.text = element_text(colour = light[["primary"]], size = base_size, hjust = 0, face = "bold"),
      legend.position = "top",
      legend.justification = "left",
      legend.text = element_text(colour = light[["secondary"]], size = base_size - 1),
      legend.title = element_blank(),
      plot.title.position = "plot",
      plot.caption.position = "plot",
      plot.margin = margin(18, 24, 12, 24)
    )
}

dark_css <- function() {
  rules <- unlist(lapply(names(light), function(key) {
    c(sprintf("[style*='fill: %s'] { fill: %s !important; }", light[[key]], dark[[key]]),
      sprintf("[style*='stroke: %s'] { stroke: %s !important; }", light[[key]], dark[[key]]))
  }))
  paste0("<style>@media (prefers-color-scheme: dark) {\n", paste(rules, collapse = "\n"), "\n}</style>")
}

save_chart <- function(plot, name, width = 880, height = 476, dir = "docs/grafiken") {
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  hell <- file.path(dir, paste0(name, "-hell.svg"))
  svglite(hell, width = width / 72, height = height / 72, bg = light[["bg"]])
  print(plot)
  invisible(dev.off())
  svg <- readLines(hell, warn = FALSE)
  open <- grep("<svg", svg)[1]
  adaptive <- append(svg, dark_css(), after = open)
  writeLines(adaptive, file.path(dir, paste0(name, ".svg")))
  c(file.path(dir, paste0(name, ".svg")), hell)
}
