# Export of our repairs in the format of the Open Repair Data, see docs/adr/0049-daten-mit-r-auswerten.adoc
# and the request to the Open Repair Alliance in PLAN.md, phase 5.
#
# Reads the local preview of eval/restarters/backfill.py and writes one row per device that is ready
# to report and per event it was at, with the 14 columns of the aggregate files in quellen/openrepair-data
# in the same order. A reused ticket, for example a postponed device, gets one row per event. The earlier
# events count as Repairable, the last one carries the result of the ticket.
#   id                            msg_, ticket number and date of the event, unique per repair attempt
#   data_provider, group          Makerspace Gütersloh e.V.
#   partner_product_category      English name of the catalog entry
#   product_category(_id)         ORA group of the catalog entry, 0 for unpowered groups as in the data
#   brand                         as recorded, Unknown if empty as in the data
#   year_of_manufacture, age      empty, the tickets do not carry them yet
#   repair_status, barrier        from the result, "Abnutzung zu groß" becomes Product too worn out,
#                                 which the standard knows even though Restarters does not
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

columns <- names(read_csv("quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_eee.csv",
                          n_max = 0, show_col_types = FALSE))
category_ids <- read_csv("quellen/openrepair-data/OpenRepairData_v0.3_Product_Categories_eee.csv",
                         col_types = cols(.default = col_character()))

preview <- read_tsv(preview_path, col_types = cols(.default = col_character()), na = character())

attempts <- preview |>
  filter(action == "melden") |>
  mutate(dates = if_else(earlier_dates == "", event_date, paste(earlier_dates, event_date, sep = ","))) |>
  separate_longer_delim(dates, ",") |>
  mutate(final = dates == event_date,
         repair_status = if_else(final, repair_status, "Repairable"),
         barrier = if_else(final, barrier, ""),
         result = if_else(final, result, ""),
         event_date = dates)

ords <- attempts |>
  left_join(category_ids, by = c("ora_group" = "product_category")) |>
  transmute(
    id = paste0("msg_", ticket, "_", gsub("-", "", event_date)),
    data_provider = "Makerspace Gütersloh e.V.",
    country = "DEU",
    partner_product_category = item_type,
    product_category = ora_group,
    product_category_id = if_else(startsWith(ora_group, "Unpowered"), "0", product_category_id),
    brand = if_else(brand == "", "Unknown", brand),
    year_of_manufacture = "",
    product_age = "",
    repair_status = repair_status,
    repair_barrier_if_end_of_life = case_when(
      barrier != "" ~ barrier,
      result == "nicht erfolgt::Abnutzung zu groß" ~ "Product too worn out",
      .default = ""
    ),
    group_identifier = "Makerspace Gütersloh e.V.",
    event_date = event_date,
    problem = ""
  ) |>
  arrange(event_date, id)

stopifnot(identical(names(ords), columns), !anyNA(ords$product_category_id), !anyDuplicated(ords$id))
write_csv(ords, out_path, na = "")
cat(nrow(ords), "Zeilen nach", out_path, "\n")
print(count(ords, repair_status))
print(count(ords, product_category, sort = TRUE), n = 12)
