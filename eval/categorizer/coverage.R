# How many catalog entries cover how much of the German repairs in the Open Repair Data, for the
# work on the catalog and chapter 5 of the case study.
#
# Reads eval/categorizer/abc.tsv from eval/categorizer/abc.py, sorts the entries by their repairs and
# draws the number of entries needed against the cumulative share of repairs they cover. The marks
# show the limits of the ABC classes at 80 and 95 percent and the 90 percent used for the catalog
# work. The numbers for the text go to docs/ora/catalog/coverage.tsv.
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

marks <- tibble(level = c(0.80, 0.90, 0.95, 1)) |>
  mutate(rank = vapply(level, reach, integer(1)),
         label = paste0(de(100 * level), " % mit ", de(rank), " Einträgen"))

facts <- bind_rows(
  tibble(measure = c("entries", "repairs", "entries_without_repairs", "entries_below_10_repairs"),
         value = c(nrow(entries), sum(entries$repairs_deu), sum(entries$repairs_deu == 0),
                   sum(entries$repairs_deu < 10))),
  transmute(marks, measure = paste0("entries_for_", 100 * level, "_percent"), value = rank)
)
dir.create("docs/ora/catalog", recursive = TRUE, showWarnings = FALSE)
write_tsv(facts, "docs/ora/catalog/coverage.tsv")

plot <- ggplot(entries, aes(share, rank)) +
  geom_vline(data = marks, aes(xintercept = level), colour = light[["grid"]], linewidth = 0.4) +
  geom_step(colour = light[["s1"]], linewidth = 0.9, direction = "vh") +
  geom_point(data = marks, aes(level, rank), size = 2.6, colour = light[["s1"]], fill = light[["bg"]],
             shape = 21, stroke = 1.6) +
  geom_text(data = marks, aes(level, rank, label = label), hjust = 1.06, vjust = -0.7, size = 3.6,
            colour = light[["secondary"]]) +
  scale_x_continuous(labels = \(x) paste0(de(100 * x), " %"), breaks = seq(0, 1, 0.2),
                     limits = c(0, 1.01), expand = expansion(mult = c(0, 0))) +
  scale_y_continuous(breaks = seq(0, 1000, 200), labels = \(x) de(x),
                     limits = c(0, nrow(entries) * 1.06), expand = expansion(mult = c(0, 0))) +
  labs(title = "Wenige Einträge decken fast alle Reparaturen ab",
       subtitle = paste0("Einträge, die nötig sind, um einen Anteil der ", de(sum(entries$repairs_deu)),
                         " deutschen Reparaturen abzudecken, die häufigsten zuerst.\n",
                         de(sum(entries$repairs_deu < 10)), " der ", de(nrow(entries)),
                         " Einträge haben weniger als 10 Reparaturen, ", de(sum(entries$repairs_deu == 0)), " gar keine"),
       x = "Anteil der Reparaturen", y = "Einträge im Katalog",
       caption = paste0("Gezählt sind die Reparaturen der anstiftung in Deutschland, die sich eindeutig einem Eintrag zuordnen lassen.\n",
                        "Quelle: Open Repair Data 0.3, Juli 2026, CC BY-SA 4.0")) +
  theme_manuel()
out <- save_chart(plot, "catalog-coverage")

write_run("docs/ora/catalog/coverage.tsv", inputs = input, outputs = c("docs/ora/catalog/coverage.tsv", out))
print(facts, width = Inf)
