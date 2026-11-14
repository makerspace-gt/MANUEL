# How many catalog entries cover how much of the German repairs in the Open Repair Data, for the
# work on the catalog and chapter 5 of the case study.
#
# Reads eval/categorizer/abc.tsv from eval/categorizer/abc.py, sorts the entries by their repairs and
# draws the number of entries needed against the cumulative share of repairs they cover. The marks
# show 80 percent, the limit of class A, and every percent from 90, also listed as a table.
# The numbers for the text go to docs/ora/catalog/coverage.tsv.
#
# Run in the repository root, see docs/adr/0049-daten-mit-r-auswerten.adoc:
#   toolbox run -c manuel-r Rscript eval/categorizer/coverage.R

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})
source("eval/r/lauf.R")
source("eval/r/theme.R")

input <- "eval/categorizer/abc.tsv"
entries <- read_tsv(input, col_types = cols(.default = col_character(), repairs_deu = col_integer())) |>
  arrange(desc(repairs_deu), key) |>
  mutate(rank = row_number(), share = cumsum(repairs_deu) / sum(repairs_deu))

de <- function(x, digits = 0) formatC(x, format = "f", digits = digits, big.mark = ".", decimal.mark = ",")
reach <- function(level) min(entries$rank[entries$share >= level])

# From 90 percent every percent, all of them in the table, the curve only labels 80, 90 and 100
marks <- tibble(level = c(0.80, seq(90, 100) / 100)) |>
  mutate(rank = vapply(level, reach, integer(1)),
         label = paste0(de(100 * level), " % mit ", de(rank), " Kategorien"))
curve_labels <- filter(marks, level %in% c(0.80, 0.90, 1))

# Examples so the chart reads without the text, the rare ones are checked to have one repair
top <- head(entries, 3)
rare <- c("Braukessel", "Marderschreck", "Schlafmaske", "Wagenheber, hydraulisch")
stopifnot(all(entries$repairs_deu[match(rare, entries$name)] == 1))
top_text <- paste0("Am häufigsten sind ", top$name[1], " mit ", de(top$repairs_deu[1]), ", ",
                   top$name[2], " mit ", de(top$repairs_deu[2]), "\nund ", top$name[3], " mit ",
                   de(top$repairs_deu[3]), " Reparaturen")
rare_text <- paste0(de(sum(entries$repairs_deu == 1)), " Kategorien kommen nur einmal vor,\netwa ",
                    paste(rare[-length(rare)], collapse = ", "), " und ", sub(",.*", "", rare[length(rare)]))
table <- filter(marks, level >= 0.90) |>
  mutate(y = 1000 - (row_number() - 1) * 62)

facts <- bind_rows(
  tibble(measure = c("entries", "repairs", "entries_without_repairs", "entries_below_10_repairs"),
         value = c(nrow(entries), sum(entries$repairs_deu), sum(entries$repairs_deu == 0),
                   sum(entries$repairs_deu < 10))),
  transmute(marks, measure = paste0("entries_for_", 100 * level, "_percent"), value = rank)
)
dir.create("docs/ora/catalog", recursive = TRUE, showWarnings = FALSE)
write_tsv(facts, "docs/ora/catalog/coverage.tsv")

plot <- ggplot(entries, aes(share, rank)) +
  geom_vline(xintercept = c(0.8, 0.9, 1), colour = light[["grid"]], linewidth = 0.4) +
  geom_step(colour = light[["s1"]], linewidth = 0.9, direction = "vh") +
  geom_point(data = marks, aes(level, rank), size = 2.2, colour = light[["s1"]], fill = light[["bg"]],
             shape = 21, stroke = 1.4) +
  geom_text(data = curve_labels, aes(level, rank, label = label), hjust = 1.06, vjust = -0.7, size = 3.6,
            colour = light[["secondary"]]) +
  annotate("rect", xmin = 0, xmax = 0.19, ymin = 330, ymax = 1110, fill = light[["bg"]]) +
  annotate("text", x = 0.06, y = 1075, label = "Anteil", hjust = 1, size = 3.6, colour = light[["primary"]],
           fontface = "bold") +
  annotate("text", x = 0.17, y = 1075, label = "Kategorien", hjust = 1, size = 3.6, colour = light[["primary"]],
           fontface = "bold") +
  geom_text(data = table, aes(0.06, y, label = paste0(de(100 * level), " %")), hjust = 1, size = 3.6,
            colour = light[["secondary"]]) +
  geom_text(data = table, aes(0.17, y, label = de(rank)), hjust = 1, size = 3.6, colour = light[["secondary"]]) +
  annotate("text", x = 0.03, y = 95, label = top_text, hjust = 0, vjust = 0, size = 3.6, lineheight = 1.1,
           colour = light[["primary"]]) +
  annotate("text", x = 0.975, y = 880, label = rare_text, hjust = 1, size = 3.6, lineheight = 1.1,
           colour = light[["primary"]]) +
  scale_x_continuous(labels = \(x) paste0(de(100 * x), " %"), breaks = seq(0, 1, 0.2),
                     limits = c(0, 1.01), expand = expansion(mult = c(0, 0))) +
  scale_y_continuous(breaks = seq(0, 1000, 200), labels = \(x) de(x),
                     limits = c(0, nrow(entries) * 1.06), expand = expansion(mult = c(0, 0))) +
  labs(title = "Wenige Kategorien decken fast alle Reparaturen ab",
       subtitle = paste0("Kategorien im Katalog, die nötig sind, um einen Anteil der ", de(sum(entries$repairs_deu)),
                         " deutschen Reparaturen abzudecken, die häufigsten zuerst. 1 % sind rund ",
                         de(round(sum(entries$repairs_deu) / 100, -1)), " Geräte.\n",
                         de(sum(entries$repairs_deu < 10)), " der ", de(nrow(entries)),
                         " Kategorien haben weniger als 10 Reparaturen, ", de(sum(entries$repairs_deu == 0)), " gar keine"),
       x = "Anteil der Reparaturen", y = "Kategorien im Katalog",
       caption = paste0("Gezählt sind die Reparaturen der anstiftung in Deutschland, die sich eindeutig einer Kategorie zuordnen lassen.\n",
                        "Quelle: Open Repair Data 0.3, Juli 2026, CC BY-SA 4.0")) +
  theme_manuel()
out <- save_chart(plot, "catalog-coverage")

write_run("docs/ora/catalog/coverage.tsv", inputs = input, outputs = c("docs/ora/catalog/coverage.tsv", out))
print(facts, width = Inf)
