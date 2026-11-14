# Step 1 of import, tidy, transform for the fields of ORA, anstiftung and Restarters, see
# eval/fields/import_sources.py for the sources that are not tables.
#
# Reads the aggregate files of the Open Repair Data and writes one file per partner to
# docs/fields/import. Each row is a category of the partner together with the group the Open Repair
# Alliance assigned it to and the number of entries, separately for electrical items (eee) and
# unpowered items (non_eee). The rows of the partners themselves stay in the submodule.
#
#   ora_partner_anstiftung.csv     data_provider anstiftung
#   ora_partner_restarters.csv     data_provider The Restart Project, the data of Restarters.net
#
# Run in the repository root, see docs/adr/0049-daten-mit-r-auswerten.adoc:
#   toolbox run -c manuel-r Rscript eval/fields/import_partners.R

suppressPackageStartupMessages({
  library(dplyr)
  library(purrr)
  library(readr)
})
source("eval/r/lauf.R")

files <- c(
  eee = "quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_eee.csv",
  non_eee = "quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_non-eee.csv"
)
partners <- c(anstiftung = "anstiftung", restarters = "The Restart Project")

data <- imap(files, \(path, kind) {
  read_csv(path, col_types = cols(.default = col_character()), na = character(), progress = FALSE) |>
    filter(data_provider %in% partners) |>
    mutate(file = kind)
}) |>
  bind_rows()

dir.create("docs/fields/import", recursive = TRUE, showWarnings = FALSE)
outputs <- imap_chr(partners, \(provider, name) {
  path <- file.path("docs/fields/import", paste0("ora_partner_", name, ".csv"))
  data |>
    filter(data_provider == provider) |>
    count(file, partner_product_category, product_category, product_category_id, name = "entries") |>
    arrange(file, partner_product_category, desc(entries)) |>
    write_csv(path, na = "")
  cat(path, ":", nrow(read_csv(path, show_col_types = FALSE)), "Zeilen\n")
  path
})

write_run("docs/fields/import/ora_partner_anstiftung.csv", inputs = unname(files), outputs = unname(outputs))
