# Flow of the catalog entries from the form of the anstiftung to the list MANUEL chooses from, as a
# Sankey diagram, see docs/adr/0055-katalog-in-bloecken-durchsehen.adoc. The width of each band is the
# number of entries. The classes before the review come from eval/categorizer/abc.tsv at the commit
# before the review of 15.11.2026, the classes after it from the current file.
#
# Run in the repository root:
#   toolbox run -c manuel-r Rscript eval/categorizer/catalog_flow.R

source("eval/r/theme.R")
suppressPackageStartupMessages(library(dplyr))

BEFORE <- "3eadbfd~1"
read_abc <- function(text) read.delim(text = text, sep = "\t", quote = "", colClasses = "character")
before <- read_abc(paste(system2("git", c("show", paste0(BEFORE, ":eval/categorizer/abc.tsv")), stdout = TRUE),
                         collapse = "\n"))
after <- read_abc(paste(readLines("eval/categorizer/abc.tsv", warn = FALSE), collapse = "\n"))
form <- nrow(read.csv("quellen/anstiftung/kategorien.csv"))

n_before <- table(factor(before$class, levels = c("A", "B", "C")))
n_after <- table(factor(after$class, levels = c("A", "B", "C")))
share <- with(before, tapply(as.numeric(repairs_deu), class, sum))
share <- round(100 * share / sum(share))

nodes <- tribble(
  ~id,        ~col, ~n,                                  ~label,                                                   ~fill,
  "form",     1,    form,                                sprintf("Laufzettel\n%s Kategorien", format(form, big.mark = ".", decimal.mark = ",")), "s0",
  "catalog",  2,    nrow(before),                        sprintf("Katalog\n%s Einträge", format(nrow(before), big.mark = ".", decimal.mark = ",")), "s0",
  "merged1",  2,    form - nrow(before),                 sprintf("%d zusammengefasst", form - nrow(before)),       "grid",
  "A",        3,    n_before[["A"]],                     sprintf("A, %d\n%d %% der Reparaturen", n_before[["A"]], share[["A"]]), "s1",
  "B",        3,    n_before[["B"]],                     sprintf("B, %d\n%d %%", n_before[["B"]], share[["B"]]),   "s1b",
  "C",        3,    n_before[["C"]],                     sprintf("C, %d\n%d %%", n_before[["C"]], share[["C"]]),   "s0",
  "A2",       4,    n_after[["A"]],                      sprintf("A, %d", n_after[["A"]]),                         "s1",
  "B2",       4,    n_after[["B"]],                      sprintf("B, %d", n_after[["B"]]),                         "s1b",
  "merged2",  4,    nrow(before) - nrow(after),          sprintf("%d zusammengefasst", nrow(before) - nrow(after)), "grid",
  "C2",       4,    n_after[["C"]],                      sprintf("C, %d", n_after[["C"]]),                         "s0",
  "manuel",   5,    n_after[["A"]] + n_after[["B"]],     sprintf("MANUEL wählt aus\n%d Einträgen", n_after[["A"]] + n_after[["B"]]), "s1",
  "hand",     5,    n_after[["C"]],                      sprintf("nur von Hand\n%d Einträge", n_after[["C"]]),     "s0"
)

flows <- tribble(
  ~from,     ~to,       ~n,
  "form",    "catalog", nrow(before),
  "form",    "merged1", form - nrow(before),
  "catalog", "A",       n_before[["A"]],
  "catalog", "B",       n_before[["B"]],
  "catalog", "C",       n_before[["C"]],
  "A",       "A2",      n_after[["A"]],
  "A",       "merged2", n_before[["A"]] - n_after[["A"]],
  "B",       "B2",      n_after[["B"]],
  "B",       "merged2", n_before[["B"]] - n_after[["B"]],
  "C",       "merged2", n_before[["C"]] - n_after[["C"]],
  "C",       "C2",      n_after[["C"]],
  "A2",      "manuel",  n_after[["A"]],
  "B2",      "manuel",  n_after[["B"]],
  "C2",      "hand",    n_after[["C"]]
)

# Stack the nodes of each column from the top with a gap, in the order of the table
gap <- 60
width <- 0.06
nodes <- nodes |>
  group_by(col) |>
  mutate(y1 = form - (cumsum(n) - n) - (row_number() - 1) * gap, y0 = y1 - n) |>
  ungroup()
node <- function(id) nodes[nodes$id == id, ]

# Each band leaves its source and enters its target in the order of the table
flows <- flows |>
  group_by(from) |> mutate(out_top = node(from[1])$y1 - (cumsum(n) - n)) |> ungroup() |>
  group_by(to) |> mutate(in_top = node(to[1])$y1 - (cumsum(n) - n)) |> ungroup()

ribbon <- function(f, i) {
  a <- node(f$from); b <- node(f$to)
  x0 <- a$col + width / 2; x1 <- b$col - width / 2
  t <- seq(0, 1, length.out = 60)
  s <- t * t * (3 - 2 * t)
  x <- x0 + (x1 - x0) * t
  top <- f$out_top + (f$in_top - f$out_top) * s
  bottom <- top - f$n
  data.frame(id = i, x = c(x, rev(x)), y = c(top, rev(bottom)),
             fill = if (b$fill == "grid") "grid" else if (a$id %in% c("form", "catalog")) a$fill else b$fill)
}
bands <- bind_rows(lapply(seq_len(nrow(flows)), function(i) ribbon(flows[i, ], i)))

colours <- c(s0 = light[["s0"]], s1 = light[["s1"]], s1b = "#86B4EA", grid = light[["grid"]])
plot <- ggplot() +
  geom_polygon(data = bands, aes(x, y, group = id, fill = fill), alpha = 0.55, colour = NA) +
  geom_rect(data = nodes, aes(xmin = col - width / 2, xmax = col + width / 2, ymin = y0, ymax = y1, fill = fill)) +
  geom_text(data = nodes, aes(x = col + width / 2 + 0.04, y = (y0 + y1) / 2, label = label),
            hjust = 0, size = 3.3, lineheight = 0.95, colour = light[["primary"]]) +
  scale_fill_manual(values = colours, guide = "none") +
  scale_x_continuous(breaks = 1:5, labels = c("Laufzettel", "Katalog", "Klassen nach\nHäufigkeit",
                                              "nach der\nDurchsicht", "Auswahl"),
                     limits = c(0.95, 5.75), expand = c(0, 0)) +
  scale_y_continuous(NULL, breaks = NULL) +
  labs(title = "Aus 1.208 Kategorien werden 347, aus denen MANUEL wählt",
       subtitle = "Breite der Bänder ist die Zahl der Einträge. A und B decken 95 Prozent der Reparaturen ab.",
       caption = "Klassen nach den deutschen Open Repair Data vom Juli 2026, Durchsicht am 15.11.2026, siehe ADR 55.\nC-Einträge bleiben von Hand wählbar. Nach etwa einem Jahr Echtbetrieb kommen häufig gewählte in die Liste.",
       x = NULL) +
  theme_manuel() +
  theme(panel.grid.major.y = element_blank(), axis.line.x = element_blank())

print(save_chart(plot, "katalog-fluss", width = 880, height = 520))
