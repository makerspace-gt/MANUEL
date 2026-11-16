# Counts the rows of score.py per run and field, see docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc
# and docs/adr/0049-daten-mit-r-auswerten.adoc. The result holds numbers only and may go into the repo.
#
#   filled_human   tickets in which volunteers kept the field
#   filled_model   tickets in which the model filled it
#   gained         tickets the model filled where volunteers left it empty, the gain of the data set
#   filled_after   tickets with the field filled by volunteers or the model
#   hits, compared share of hits where both filled it, with 95 % Wilson interval
#   top_hits       same ORA group for the device type, yes or partly for the solution
#   similarity     median cosine similarity of the defect with bge-m3
# Where a run has energy/energy.tsv from eval/strom/energy.py, energy.csv holds seconds, watt hours at
# the plug and the GPU per ticket and the idle power per run.
#
# Run in the repository root, OUT is a folder in eval/results/enrich:
#   toolbox run -c manuel-r Rscript eval/enrich/summary.R OUT RUN_DIR [RUN_DIR ...]

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})
source("eval/r/lauf.R")

args <- commandArgs(trailingOnly = TRUE)
out <- args[1]
runs <- args[-1]
files <- file.path(runs, "score", "scores.tsv")

scores <- bind_rows(lapply(seq_along(runs), function(i) {
  read_tsv(files[i], col_types = cols(.default = "c")) |>
    mutate(run = basename(normalizePath(runs[i])))
})) |>
  mutate(across(c(human, model, error), as.integer),
         across(c(hit, top_hit, similarity), as.numeric))

wilson <- function(k, n, bound) {
  ifelse(n > 0, binom::binom.confint(k, pmax(n, 1), methods = "wilson")[[bound]], NA_real_)
}

summary <- scores |>
  group_by(task, run, field) |>
  summarise(tickets = n_distinct(ticket),
            errors = sum(error),
            filled_human = sum(human),
            filled_model = sum(model),
            gained = sum(model == 1 & human == 0),
            filled_after = sum(model == 1 | human == 1),
            compared = sum(!is.na(hit)),
            hits = sum(hit, na.rm = TRUE),
            top_hits = if (all(is.na(top_hit))) NA_integer_ else as.integer(sum(top_hit, na.rm = TRUE)),
            similarity = if (all(is.na(similarity))) NA_real_ else round(median(similarity, na.rm = TRUE), 3),
            .groups = "drop") |>
  mutate(hit_rate = round(ifelse(compared > 0, hits / compared, NA_real_), 3),
         hit_lower = round(wilson(hits, compared, "lower"), 3),
         hit_upper = round(wilson(hits, compared, "upper"), 3),
         .after = hits)

dir.create(out, recursive = TRUE, showWarnings = FALSE)
target <- file.path(out, "summary.csv")
write_csv(summary, target, na = "")
outputs <- target
print(as.data.frame(summary), row.names = FALSE)

# Energy per run from eval/strom/energy.py, where a recording exists
energy_files <- file.path(runs, "energy", "energy.tsv")
energy_files <- energy_files[file.exists(energy_files)]
if (length(energy_files) > 0) {
  energy <- bind_rows(lapply(energy_files, function(f) {
    read_tsv(f, col_types = cols(.default = "d", task = "c")) |>
      mutate(run = basename(dirname(dirname(normalizePath(f)))))
  })) |>
    group_by(task, run) |>
    summarise(tickets = n(),
              seconds_median = round(median(seconds), 1),
              plug_mwh_per_ticket = round(1000 * mean(plug_wh, na.rm = TRUE), 1),
              extra_mwh_per_ticket = round(1000 * mean(plug_extra_wh, na.rm = TRUE), 1),
              gpu_mwh_per_ticket = round(1000 * mean(gpu_wh, na.rm = TRUE), 1),
              idle_w = round(median(idle_w, na.rm = TRUE), 1),
              tokens_per_ticket = round(mean(eval_count, na.rm = TRUE)),
              plug_wh_total = round(sum(plug_wh, na.rm = TRUE), 2),
              .groups = "drop")
  energy_target <- file.path(out, "energy.csv")
  write_csv(energy, energy_target, na = "")
  outputs <- c(outputs, energy_target)
  files <- c(files, energy_files)
  print(as.data.frame(energy), row.names = FALSE)
}
write_run(target, inputs = c(files, "eval/enrich/summary.R"), outputs = outputs)
