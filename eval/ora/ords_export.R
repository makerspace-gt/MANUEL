# Export of our repairs in the format of the Open Repair Data, see docs/adr/0049-daten-mit-r-auswerten.adoc,
# docs/adr/0051-reparaturdaten-nach-ords-oeffentlich-bereitstellen.adoc and docs/adr/0052-erfasste-daten-festlegen.adoc.
#
# Reads the local preview of eval/restarters/backfill.py and writes one row per repair attempt. A reused
# ticket, for example a postponed device, gets one row per event. The earlier events count as Repairable,
# the last one carries the result of the ticket. The first 14 columns are those of the aggregate files in
# quellen/openrepair-data in the same order, the additional columns follow. docs/ora/ords-export.md
# describes every column.
#   id                            msg_, ticket number and date of the event, unique per repair attempt
#   data_provider                 Makerspace Gütersloh e.V.
#   partner_product_category      English name of the catalog entry, the German name where it is missing
#   product_category(_id)         ORA group of the catalog entry, 0 for unpowered groups as in the data
#   brand                         as recorded, Unknown if empty as in the data
#   repair_status, barrier        from eval/ora/result_mapping.tsv, which follows the anstiftung
#   group_identifier              17503, our initiative on reparatur-initiativen.org
#   problem                       empty until the tickets are anonymised, see docs/adr/0038
# The output is derived from real tickets and stays local like the preview.
#
# Run in the repository root:
#   toolbox run -c manuel-r Rscript eval/ora/ords_export.R PREVIEW.tsv OUT.csv

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(tidyr)
})

args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2)
preview_path <- args[[1]]
out_path <- args[[2]]

text <- cols(.default = col_character())
columns <- names(read_csv("quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_eee.csv",
                          n_max = 0, show_col_types = FALSE))
category_ids <- read_csv("quellen/openrepair-data/OpenRepairData_v0.3_Product_Categories_eee.csv", col_types = text)
results <- read_tsv("eval/ora/result_mapping.tsv", col_types = text, na = character())
events <- read_tsv("docs/ora/anstiftung/events.tsv", col_types = text)
form <- read_csv("quellen/anstiftung/kategorien.csv", col_types = text) |>
  distinct(id, .keep_all = TRUE)
catalog <- read_tsv("katalog/kategorien.tsv", col_types = text, na = character(), quote = "") |>
  select(catalog_key = key, name)

preview <- read_tsv(preview_path, col_types = text, na = character())

attempts <- preview |>
  filter(action != "auslassen", event_date != "", catalog_key != "", result %in% results$result) |>
  left_join(select(results, result, final_status = repair_status, final_barrier = repair_barrier_if_end_of_life),
            by = "result") |>
  mutate(dates = if_else(earlier_dates == "", event_date, paste(earlier_dates, event_date, sep = ","))) |>
  separate_longer_delim(dates, ",") |>
  group_by(ticket) |>
  mutate(repair_attempt = rank(dates)) |>
  ungroup() |>
  mutate(final = dates == event_date,
         repair_status = if_else(final, final_status, "Repairable"),
         barrier = if_else(final, final_barrier, ""),
         event_date = dates)

ords <- attempts |>
  left_join(catalog, by = "catalog_key") |>
  left_join(category_ids, by = c("ora_group" = "product_category")) |>
  mutate(anstiftung_category_id = sapply(strsplit(catalog_key, ".", fixed = TRUE), `[`, 3)) |>
  left_join(select(form, anstiftung_category_id = id, anstiftung_category = category,
                   anstiftung_parent_category = top_category), by = "anstiftung_category_id") |>
  left_join(select(events, event_date, anstiftung_event_uid = event_id), by = "event_date") |>
  transmute(
    id = paste0("msg_", ticket, "_", gsub("-", "", event_date)),
    data_provider = "Makerspace Gütersloh e.V.",
    country = "DEU",
    partner_product_category = if_else(item_type != "", item_type, name),
    product_category = ora_group,
    product_category_id = if_else(startsWith(ora_group, "Unpowered"), "0", product_category_id),
    brand = if_else(brand == "", "Unknown", brand),
    year_of_manufacture = "",
    product_age = "",
    repair_status,
    repair_barrier_if_end_of_life = barrier,
    group_identifier = "17503",
    event_date,
    problem = "",
    repair_attempt = as.character(repair_attempt),
    product_age_qualifier = "",
    problem_de = "",
    knowledge_base_url = "",
    anstiftung_event_uid = coalesce(anstiftung_event_uid, ""),
    anstiftung_category_id,
    anstiftung_category = coalesce(anstiftung_category, ""),
    anstiftung_parent_category = coalesce(anstiftung_parent_category, ""),
    catalog_key
  ) |>
  arrange(event_date, id)

stopifnot(identical(names(ords)[seq_along(columns)], columns), !anyNA(ords$product_category_id),
          !anyDuplicated(ords$id), !anyNA(ords$repair_status))
write_csv(ords, out_path, na = "")
cat(nrow(ords), "Zeilen nach", out_path, "\n")
cat("Event der anstiftung bei", sum(ords$anstiftung_event_uid != ""), "von", nrow(ords), "Zeilen,",
    "Kategorie der anstiftung bei", sum(ords$anstiftung_category != ""), "\n")
print(count(ords, repair_status))
print(count(ords, repair_attempt))
