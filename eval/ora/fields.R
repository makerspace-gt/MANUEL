# Distinct values of every field in the Open Repair Data, with counts.
#
# Loads both aggregate files of quellen/openrepair-data, the one for electrical and electronic
# equipment (eee) and the one for unpowered items (non-eee). Every value stays as it is in the file,
# all columns are read as text and an empty field stays empty. For each field the script writes a
# table with every distinct value and how often it occurs in each file, sorted by the total. A
# summary lists for each field the number of rows, distinct values and empty values.
# At the end values.csv has the same columns in the same order as the input files. Each column lists
# the distinct values of its field from the most to the least common, so the columns have different
# lengths and shorter ones end in empty cells. The empty value itself is left out, it cannot be told
# apart from the padding. The column id stays empty because every id occurs once.
# The tables for id and problem and values.csv are large, so docs/ora/fields/.gitignore keeps them
# out of the repo.
#
# Run in the repository root, see docs/adr/0049-daten-mit-r-auswerten.adoc:
#   toolbox run -c manuel-r Rscript eval/ora/fields.R [quellen/openrepair-data] [docs/ora/fields]

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(tidyr)
  library(purrr)
})
source("eval/r/lauf.R")

args <- commandArgs(trailingOnly = TRUE)
source_dir <- if (length(args) >= 1) args[[1]] else "quellen/openrepair-data"
out_dir <- if (length(args) >= 2) args[[2]] else "docs/ora/fields"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

files <- c(
  eee = file.path(source_dir, "OpenRepairData_v0.3_aggregate_202607_eee.csv"),
  non_eee = file.path(source_dir, "OpenRepairData_v0.3_aggregate_202607_non-eee.csv")
)

read_ords <- function(path) {
  read_csv(path, col_types = cols(.default = col_character()), na = character(),
           trim_ws = FALSE, progress = FALSE)
}

data <- imap(files, \(path, kind) mutate(read_ords(path), file = kind)) |> bind_rows()
fields <- setdiff(names(data), "file")

count_field <- function(field) {
  data |>
    count(value = .data[[field]], file) |>
    pivot_wider(names_from = file, values_from = n, values_fill = 0) |>
    mutate(total = eee + non_eee, share = round(total / nrow(data), 6)) |>
    select(value, eee, non_eee, total, share) |>
    arrange(desc(total), value)
}

outputs <- character()
all_values <- list()
summary <- map(fields, \(field) {
  counts <- count_field(field)
  all_values[[field]] <<- if (field == "id") character() else counts$value[counts$value != ""]
  path <- file.path(out_dir, paste0(field, ".tsv"))
  write_tsv(counts, path, na = "")
  outputs <<- c(outputs, path)
  tibble(
    field = field,
    rows = nrow(data),
    distinct = nrow(counts),
    empty = sum(counts$total[counts$value == ""]),
    distinct_eee = sum(counts$eee > 0),
    distinct_non_eee = sum(counts$non_eee > 0),
    most_common = counts$value[[1]],
    most_common_n = counts$total[[1]]
  )
}) |> bind_rows()

summary_path <- file.path(out_dir, "summary.tsv")
write_tsv(summary, summary_path)
values_path <- file.path(out_dir, "values.csv")
longest <- max(lengths(all_values))
wide <- as_tibble(lapply(all_values[fields], \(v) c(v, rep(NA_character_, longest - length(v)))))
write_csv(wide, values_path, na = "")
outputs <- c(outputs, values_path)
write_run(summary_path, inputs = unname(files), outputs = c(summary_path, outputs))
print(summary, n = Inf, width = Inf)
