# Baseline of the indicators before MANUEL, see docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc.
#
# Reads the monthly sums of eval/indicators/statistics.py (statistics of the team since 2019) and
# eval/indicators/indicators.py --monthly (owners from the Zammad export since 2025) and writes
#   baseline.csv                       each indicator for three windows: all months, 36 and 12 months
#   docs/grafiken/indikatoren-*.svg    repair rate, devices and repairers per month
# The repair rate is fixed, including partly fixed, among fixed, postponed and not repaired.
#
# Run in the repository root, see docs/adr/0049-daten-mit-r-auswerten.adoc:
#   toolbox run -c manuel-r Rscript eval/indicators/baseline.R eval/results/indicators/baseline-2026-11-22

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(tidyr)
})
source("eval/r/lauf.R")
source("eval/r/theme.R")

dir <- commandArgs(trailingOnly = TRUE)[1]
stats_file <- file.path(dir, "statistics_monthly.tsv")
owners_file <- file.path(dir, "repairers_monthly.tsv")
stats <- read_tsv(stats_file, col_types = cols(month = "c", .default = "i")) |>
  mutate(date = as.Date(paste0(month, "-01")))
owners <- read_tsv(owners_file, col_types = cols(month = "c", .default = "i")) |>
  mutate(date = as.Date(paste0(month, "-01")))

last <- max(stats$date)
windows <- tibble(
  window = c("all", "36 months", "12 months"),
  from = c(min(stats$date), seq(last, by = "-35 months", length.out = 2)[2], seq(last, by = "-11 months", length.out = 2)[2])
)

rate <- function(fixed, postponed, not_repaired) round(sum(fixed) / sum(fixed + postponed + not_repaired), 3)

baseline <- windows |>
  rowwise() |>
  mutate(
    s = list(filter(stats, date >= from)),
    o = list(filter(owners, date >= from)),
    months = nrow(s),
    events = sum(s$events),
    devices = sum(s$processed),
    devices_per_event = round(devices / events, 1),
    repair_rate = rate(s$fixed, s$postponed, s$not_repaired),
    partly_share = round(sum(s$partly) / sum(s$fixed), 3),
    no_show_share = round(sum(s$no_show) / sum(s$processed + s$no_show), 3),
    owner_months = nrow(o),
    repairers_per_month = if (nrow(o) > 0) round(mean(o$repairers), 1) else NA_real_,
    new_repairers_per_month = if (nrow(o) > 0) round(mean(o$new_repairers), 1) else NA_real_,
    by_guest = sum(o$by_guest),
    from = format(from, "%Y-%m")
  ) |>
  ungroup() |>
  select(-s, -o) |>
  # Indicators without a monthly series: share of devices reported to Restarters (ADR 32) and wrong device
  # types in the pre-test of the categorizer (ADR 40), both the same in every window
  mutate(reported_share = round(30 / 1485, 3), wrong_device_type_pretest = 0.175, feedback_tags = 0L)

target <- file.path(dir, "baseline.csv")
write_csv(baseline, target, na = "")
print(as.data.frame(baseline), row.names = FALSE)

# Repair rate per month with the rate of the 12 months before, as points and line
rolling <- stats |>
  arrange(date) |>
  mutate(
    month_rate = fixed / (fixed + postponed + not_repaired),
    r_fixed = sapply(seq_along(date), \(i) sum(fixed[date > date[i] - 365 & date <= date[i]])),
    r_done = sapply(seq_along(date), \(i) sum((fixed + postponed + not_repaired)[date > date[i] - 365 & date <= date[i]])),
    year_rate = r_fixed / r_done,
    # A new segment after more than three months without an event, so the line does not bridge gaps
    segment = cumsum(c(TRUE, diff(date) > 100))
  )

p1 <- ggplot(rolling, aes(date)) +
  geom_point(aes(y = month_rate, colour = "je Monat"), size = 1.6) +
  geom_line(aes(y = year_rate, colour = "über 12 Monate", group = segment), linewidth = 0.9) +
  scale_colour_manual(values = c("je Monat" = light[["s0"]], "über 12 Monate" = light[["s1"]])) +
  scale_y_continuous(labels = \(x) paste0(round(100 * x), " %"), limits = c(0, 1), expand = c(0, 0)) +
  scale_x_date(date_breaks = "1 year", date_labels = "%Y") +
  labs(title = "Reparaturquote vor MANUEL",
       subtitle = "Gelungen und teilweise gelungen unter allen Geräten mit Ergebnis",
       x = NULL, y = NULL, caption = "Quelle Statistik des Repair Café Gütersloh, ohne nicht erschienene Gäste") +
  theme_manuel()

p2 <- ggplot(stats, aes(date, processed)) +
  geom_col(fill = light[["s1"]], width = 24) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.05))) +
  scale_x_date(date_breaks = "1 year", date_labels = "%Y") +
  labs(title = "Bearbeitete Geräte je Monat", subtitle = "Ein oder zwei Termine im Monat, Monate ohne Termin ohne Balken",
       x = NULL, y = NULL, caption = "Quelle Statistik des Repair Café Gütersloh") +
  theme_manuel()

people <- owners |>
  transmute(date, `bekannt` = repairers - new_repairers, `zum ersten Mal` = new_repairers) |>
  pivot_longer(-date, names_to = "who", values_to = "n") |>
  mutate(who = factor(who, levels = c("zum ersten Mal", "bekannt")))
p3 <- ggplot(people, aes(date, n, fill = who)) +
  geom_col(width = 24, colour = light[["bg"]], linewidth = 0.4) +
  scale_fill_manual(values = c("bekannt" = light[["s0"]], "zum ersten Mal" = light[["s1"]])) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.05))) +
  scale_x_date(date_breaks = "3 months", date_labels = "%m/%y") +
  labs(title = "Reparierende je Monat",
       subtitle = "Personen, die eine Reparatur abgeschlossen haben, und wer davon zum ersten Mal",
       x = NULL, y = NULL, caption = "Quelle Owner der Tickets in Zammad seit 2025, 2024 nur zum Kennenlernen der Personen") +
  theme_manuel()

charts <- c(save_chart(p1, "indikatoren-reparaturquote"), save_chart(p2, "indikatoren-geraete"),
            save_chart(p3, "indikatoren-reparierende"))
write_run(target, inputs = c(stats_file, owners_file, "eval/indicators/baseline.R"), outputs = c(target, charts))
