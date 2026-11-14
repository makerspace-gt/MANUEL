# Age of the items in the Open Repair Data, for chapter 2 and appendix C of the case study.
#
# product_age and year_of_manufacture are always filled together and agree with the year of the
# event, so one is derived from the other and only the age is drawn. Ages with a fraction are
# rounded down to whole years. The first chart shows the share of items per year of age up to 60,
# split into electrical items and unpowered items, and marks multiples of 5. The second shows
# for each partner how many entries carry an age. The numbers for the text go to docs/ora/age/age.tsv.
#
# Run in the repository root, see docs/adr/0049-daten-mit-r-auswerten.adoc:
#   toolbox run -c manuel-r Rscript eval/ora/age.R

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(purrr)
  library(tidyr)
})
source("eval/r/lauf.R")
source("eval/r/theme.R")

files <- c(
  eee = "quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_eee.csv",
  non_eee = "quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_non-eee.csv"
)
kinds <- c(eee = "Elektrogeräte", non_eee = "Gegenstände ohne Strom")
limit <- 60

data <- imap(files, \(path, kind) {
  read_csv(path, col_types = cols(.default = col_character()), na = character(), progress = FALSE) |>
    mutate(file = kind)
}) |>
  bind_rows() |>
  mutate(age = suppressWarnings(as.numeric(product_age)),
         year = suppressWarnings(as.integer(year_of_manufacture)),
         event_year = as.integer(substr(event_date, 1, 4)),
         years = floor(age))

aged <- filter(data, !is.na(age))
de <- function(x, digits = 1) formatC(x, format = "f", digits = digits, big.mark = ".", decimal.mark = ",")
pct <- function(x, digits = 1) paste0(de(100 * x, digits), " %")

facts <- tibble(
  measure = c("rows", "with_age", "age_and_year_together", "age_matches_year",
              "with_fraction", "older_than_100", "older_than_limit", "median_age",
              "share_multiple_of_5_from_5_to_60", "expected_share_multiple_of_5"),
  value = c(nrow(data), nrow(aged),
            mean(is.na(data$age) == is.na(data$year)),
            mean(abs(aged$event_year - aged$year - aged$age) <= 1, na.rm = TRUE),
            sum(aged$age != floor(aged$age)), sum(aged$age > 100), sum(aged$years > limit),
            median(aged$age),
            with(filter(aged, years >= 5, years <= limit), mean(years %% 5 == 0)), 12 / 56)
)
dir.create("docs/ora/age", showWarnings = FALSE)
write_tsv(facts, "docs/ora/age/age.tsv")

per_year <- aged |>
  filter(years <= limit) |>
  count(file, years) |>
  group_by(file) |>
  mutate(share = n / sum(n)) |>
  ungroup() |>
  mutate(kind = factor(kinds[file], levels = kinds),
         round = if_else(years > 0 & years %% 5 == 0, "Vielfache von 5 Jahren", "übrige Jahre"))

heaping <- facts$value[facts$measure == "share_multiple_of_5_from_5_to_60"]
plot_age <- ggplot(per_year, aes(years, share, fill = round)) +
  geom_col(width = 0.8) +
  facet_wrap(vars(kind), ncol = 1) +
  scale_fill_manual(values = c("übrige Jahre" = light[["s1"]], "Vielfache von 5 Jahren" = light[["s2"]]),
                    breaks = c("übrige Jahre", "Vielfache von 5 Jahren")) +
  scale_x_continuous(breaks = seq(0, limit, 5), expand = expansion(add = 0.6)) +
  scale_y_continuous(labels = \(x) paste0(de(100 * x, 0), " %"), expand = expansion(mult = c(0, 0.05))) +
  labs(title = "Alter der Gegenstände in den Open Repair Data",
       subtitle = paste0(de(nrow(aged), 0), " von ", de(nrow(data), 0), " Einträgen haben ein Alter. ",
                         "Von 5 bis ", limit, " Jahren fallen ", pct(heaping, 0),
                         " auf Vielfache von 5, gleichmäßig verteilt wären es 21 %"),
       x = "Alter in Jahren, abgerundet", y = "Anteil je Art",
       caption = paste0("Älter als ", limit, " Jahre und nicht gezeigt: ", de(facts$value[facts$measure == "older_than_limit"], 0),
                        " Einträge. Quelle: Open Repair Data 0.3, Juli 2026, CC BY-SA 4.0")) +
  theme_manuel() +
  theme(panel.spacing.y = unit(18, "pt"))
out_age <- save_chart(plot_age, "ora-age", height = 560)

partners <- data |>
  group_by(data_provider) |>
  summarise(n = n(), filled = mean(!is.na(age)), .groups = "drop") |>
  arrange(filled, n) |>
  mutate(data_provider = factor(data_provider, levels = data_provider))

plot_partner <- ggplot(partners, aes(filled, data_provider)) +
  # Bars of width 0 break the PDF, partners without any age only get their label
  geom_col(data = \(d) filter(d, filled > 0), width = 0.7, fill = light[["s1"]]) +
  geom_text(aes(label = paste0(pct(filled, 0), " von ", de(n, 0))), hjust = -0.08,
            colour = light[["secondary"]], size = 3.6) +
  scale_x_continuous(labels = \(x) paste0(de(100 * x, 0), " %"), limits = c(0, 1.2),
                     breaks = seq(0, 1, 0.25), expand = expansion(mult = c(0, 0))) +
  labs(title = "Einträge mit Alter je Partner",
       subtitle = "Drei Partner liefern nie ein Alter, die übrigen bei 31 bis 44 Prozent, iFixit mit 76 Einträgen bei 86 Prozent",
       x = NULL, y = NULL, caption = "Quelle: Open Repair Data 0.3, Juli 2026, CC BY-SA 4.0") +
  theme_manuel() +
  theme(panel.grid.major.y = element_blank(),
        panel.grid.major.x = element_line(colour = light[["grid"]], linewidth = 0.4),
        axis.line.x = element_blank(), axis.text.y = element_text(colour = light[["primary"]]))
out_partner <- save_chart(plot_partner, "ora-age-partner", height = 400)

write_run("docs/ora/age/age.tsv", inputs = unname(files),
          outputs = c("docs/ora/age/age.tsv", out_age, out_partner))
print(facts, width = Inf)
print(partners)
