# How many catalog entries cover how much of the German repairs in the Open Repair Data, for the
# work on the catalog and chapter 5 of the case study.
#
# Reads eval/categorizer/abc.tsv from eval/categorizer/abc.py, sorts the entries by their repairs and
# draws the number of entries needed against the cumulative share of repairs they cover. The marks
# show 80 percent, the limit of class A, and every percent from 90, also listed as a table. Besides
# the wide chart there is a square one for social media.
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
source("eval/r/coverage.R")

input <- "eval/categorizer/abc.tsv"
entries <- read_tsv(input, col_types = cols(.default = col_character(), repairs_deu = col_integer())) |>
  transmute(name, key, n = repairs_deu)
curve <- coverage_curve(entries)
marks <- coverage_marks(curve, "Kategorien")

# Examples so the chart reads without the text, the rare ones are checked to have one repair
rare <- c("Braukessel", "Marderschreck", "Schlafmaske", "Wagenheber, hydraulisch")
stopifnot(all(curve$n[match(rare, curve$name)] == 1))
top_text <- paste("Am häufigsten sind", coverage_list(head(curve, 3)), "Reparaturen")
rare_text <- paste0(de(sum(curve$n == 1)), " Kategorien kommen nur einmal vor, etwa ",
                    paste(rare[-length(rare)], collapse = ", "), " und ", sub(",.*", "", rare[length(rare)]))
subtitle <- c(paste0("Kategorien im Katalog, die nötig sind, um einen Anteil der ", de(sum(curve$n)),
                     " deutschen Reparaturen abzudecken, die häufigsten zuerst. 1 % sind rund ",
                     de(round(sum(curve$n) / 100, -1)), " Geräte."),
              paste0(de(sum(curve$n < 10)), " der ", de(nrow(curve)),
                     " Kategorien haben weniger als 10 Reparaturen, ", de(sum(curve$n == 0)), " gar keine"))
caption <- c("Gezählt sind die Reparaturen der anstiftung in Deutschland, die sich eindeutig einer Kategorie zuordnen lassen.",
             "Quelle: Open Repair Data 0.3, Juli 2026, CC BY-SA 4.0")

facts <- coverage_facts(curve, marks)
dir.create("docs/ora/catalog", recursive = TRUE, showWarnings = FALSE)
write_tsv(facts, "docs/ora/catalog/coverage.tsv")

# wide for the case study, square for sharing on social media
make_plot <- function(square) {
  coverage_plot(curve, marks, "Kategorien", "Wenige Kategorien decken fast alle Reparaturen ab", subtitle, caption,
                "Kategorien im Katalog", top_text, rare_text, square)
}
out <- c(save_chart(make_plot(FALSE), "catalog-coverage"),
         save_chart(make_plot(TRUE), "catalog-coverage-square", width = 720, height = 720))

write_run("docs/ora/catalog/coverage.tsv", inputs = input, outputs = c("docs/ora/catalog/coverage.tsv", out))
print(facts, width = Inf)
