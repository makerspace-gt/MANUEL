# Baseline of the indicators before MANUEL, see docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc.
#
# Reads the monthly sums of eval/indicators/statistics.py (statistics of the team since 2019) and
# eval/indicators/indicators.py --monthly (owners from the Zammad export since 2025) and writes
#   baseline.csv                       each indicator for three windows: all months, 36 and 12 months
#   docs/grafiken/indikatoren-*.svg    repair rate per month, devices per appointment, repairers per month
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
events_file <- file.path(dir, "statistics_events.tsv")
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

# Milestones of the Repair Café, marked in the charts since 2019
milestones <- tibble(date = as.Date(c("2019-03-01", "2022-11-01", "2025-08-01")),
                     label = c("Start", "Zammad", "zwei Termine im Monat"))
corona <- c(as.Date("2020-04-01"), as.Date("2022-11-01"))
marks <- function(top) {
  list(
    annotate("rect", xmin = corona[1], xmax = corona[2], ymin = -Inf, ymax = Inf, fill = light[["grid"]], alpha = 0.6),
    annotate("text", x = corona[1] + (corona[2] - corona[1]) / 2, y = top, label = "Coronapause",
             colour = light[["secondary"]], size = 3.3, vjust = 1),
    geom_vline(data = milestones, aes(xintercept = date), colour = light[["axis"]], linetype = "dashed", linewidth = 0.4),
    geom_label(data = milestones, aes(x = date, y = top, label = label), colour = light[["secondary"]],
               fill = light[["bg"]], size = 3.3, hjust = 0, vjust = 1, linewidth = 0, label.padding = unit(2, "pt"))
  )
}

p1 <- ggplot(rolling, aes(date)) +
  marks(0.99) +
  geom_point(aes(y = month_rate, colour = "je Monat"), size = 1.6) +
  geom_line(aes(y = year_rate, colour = "über 12 Monate", group = segment), linewidth = 0.9) +
  scale_colour_manual(values = c("je Monat" = "#732982", "über 12 Monate" = "#004CFF")) +
  scale_y_continuous(labels = \(x) paste0(round(100 * x), " %"), limits = c(0, 1), expand = c(0, 0)) +
  scale_x_date(date_breaks = "1 year", date_labels = "%Y") +
  labs(title = "Reparaturquote vor MANUEL",
       subtitle = "Gelungen und teilweise gelungen unter allen Geräten mit Ergebnis",
       x = NULL, y = NULL, caption = "Quelle Statistik des Repair Café Gütersloh, ohne nicht erschienene Gäste") +
  theme_manuel()

# Devices per appointment stacked by result, behind them the running total since 2019 stacked the same way
# on a second axis. The six results take the colours of the pride flag in its order from top to bottom,
# red for not repaired and green for fixed.
pride <- c(red = "#E40303", orange = "#FF8C00", yellow = "#FFED00", green = "#008026", blue = "#004CFF",
           violet = "#732982")
results <- c(failed = "nicht erfolgt", aborted = "abgebrochen", partly = "teilweise gelungen", fixed = "gelungen",
             postponed = "vertagt", unknown = "keine Information")
result_colours <- setNames(unname(pride), results)
events <- read_tsv(events_file, col_types = cols(date = "D", .default = "i")) |>
  pivot_longer(-date, names_to = "result", values_to = "n") |>
  mutate(result = factor(unname(results[result]), levels = unname(results)))
running <- events |>
  arrange(date) |>
  group_by(result) |>
  mutate(total = cumsum(n)) |>
  ungroup()
per_event_max <- events |> group_by(date) |> summarise(n = sum(n)) |> pull(n) |> max()
total_max <- running |> group_by(date) |> summarise(total = sum(total)) |> pull(total) |> max()
k <- per_event_max / total_max

# Bars as rectangles, each as wide as the gap to its neighbours allows, at most 16 days
gaps <- events |> distinct(date) |> arrange(date) |>
  mutate(half = pmin(8, 0.42 * pmin(as.numeric(date - lag(date, default = date[1] - 40)),
                                    as.numeric(lead(date, default = date[n()] + 40) - date))))
bars <- events |>
  left_join(gaps, by = "date") |>
  arrange(date, desc(as.integer(result))) |>
  group_by(date) |>
  mutate(ymax = cumsum(n), ymin = ymax - n) |>
  ungroup()

p2 <- ggplot() +
  marks(per_event_max * 1.12) +
  geom_area(data = running, aes(date, total * k, fill = result), alpha = 0.22, position = "stack",
            outline.type = "upper", colour = NA) +
  geom_rect(data = bars, aes(xmin = date - half, xmax = date + half, ymin = ymin, ymax = ymax, fill = result)) +
  scale_fill_manual(values = result_colours, breaks = unname(results)) +
  guides(fill = guide_legend(nrow = 1)) +
  scale_y_continuous(name = "Geräte je Termin", expand = expansion(mult = c(0, 0.02)),
                     sec.axis = sec_axis(~ . / k, name = "Geräte seit 2019, Fläche im Hintergrund",
                                         labels = \(x) format(x, big.mark = ".", decimal.mark = ","))) +
  scale_x_date(date_breaks = "1 year", date_labels = "%Y") +
  labs(title = "Bearbeitete Geräte je Termin",
       subtitle = "Balken je Termin nach Ergebnis, dahinter die Summe seit März 2019",
       x = NULL, caption = "Quelle Statistik des Repair Café Gütersloh, ohne nicht erschienene Gäste") +
  theme_manuel() +
  theme(axis.title.y.left = element_text(margin = margin(r = 8)),
        axis.title.y.right = element_text(margin = margin(l = 8)))

people <- owners |>
  transmute(date, `bekannt` = repairers - new_repairers, `zum ersten Mal` = new_repairers) |>
  pivot_longer(-date, names_to = "who", values_to = "n") |>
  mutate(who = factor(who, levels = c("zum ersten Mal", "bekannt")))
p3 <- ggplot(people, aes(date, n, fill = who)) +
  geom_col(width = 24, colour = light[["bg"]], linewidth = 0.4) +
  scale_fill_manual(values = c("bekannt" = "#004CFF", "zum ersten Mal" = "#FF8C00")) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.05))) +
  scale_x_date(date_breaks = "3 months", date_labels = "%m/%y") +
  labs(title = "Reparierende je Monat",
       subtitle = "Personen, die eine Reparatur abgeschlossen haben, und wer davon zum ersten Mal",
       x = NULL, y = NULL, caption = "Quelle Owner der Tickets in Zammad seit 2025, 2024 nur zum Kennenlernen der Personen") +
  theme_manuel()

charts <- c(save_chart(p1, "indikatoren-reparaturquote"), save_chart(p2, "indikatoren-geraete"),
            save_chart(p3, "indikatoren-reparierende"))
write_run(target, inputs = c(stats_file, owners_file, events_file, "eval/indicators/baseline.R"), outputs = c(target, charts))
