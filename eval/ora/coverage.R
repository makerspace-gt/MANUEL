# How many categories cover how much of the repairs in the Open Repair Data, for every partner, for
# Restarters on its own and for the ORA groups as a whole. Companion to eval/categorizer/coverage.R,
# which does the same for our catalog.
#
# A category of a partner is the part of partner_product_category that comes from a fixed list, as
# counted in docs/ora/partner.tsv. With two fixed levels, like the anstiftung, it is top category and
# category, with one level, like Restarters, the category before the free text, without a fixed level
# the free text itself. The split of the Open Repair Data into electrical and unpowered files is made
# by the Alliance and does not follow the categories of the partners, so both files count together.
# Restarters writes its unpowered Misc as Misc Unpowered. Restarters categories are shown with their
# German names from docs/fields/import/restarters_translations.csv.
#
# Writes to docs/ora/coverage
#   partners.tsv     per partner the number of categories needed for 80 and 90 to 100 percent, and how
#                    many groups use a category. A category only one group uses is mostly free text,
#                    for example in the second level of Repair Café International
#   restarters.tsv   and groups.tsv, the same measures as docs/ora/catalog/coverage.tsv
# and the charts ora-coverage-partners, ora-coverage-restarters and ora-coverage-groups in docs/grafiken.
#
# Run in the repository root, see docs/adr/0049-daten-mit-r-auswerten.adoc:
#   toolbox run -c manuel-r Rscript eval/ora/coverage.R

suppressPackageStartupMessages({
  library(dplyr)
  library(purrr)
  library(readr)
  library(stringr)
  library(tidyr)
})
source("eval/r/lauf.R")
source("eval/r/theme.R")
source("eval/r/coverage.R")

files <- c(
  eee = "quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_eee.csv",
  non_eee = "quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_non-eee.csv"
)
partner_file <- "docs/ora/partner.tsv"
translations_file <- "docs/fields/import/restarters_translations.csv"
source_note <- "Quelle: Open Repair Data 0.3, Juli 2026, CC BY-SA 4.0"

data <- imap(files, \(path, kind) {
  read_csv(path, col_types = cols(.default = col_character()), na = character(), progress = FALSE) |>
    select(data_provider, group_identifier, partner_product_category, product_category) |>
    mutate(file = kind)
}) |>
  bind_rows()
levels <- read_tsv(partner_file, col_types = cols(.default = col_character())) |>
  transmute(data_provider = partner, fixed_level = as.integer(fixed_level), partner_entries = as.integer(entries))

# The fixed part of the category, the free text where there is no fixed level
fixed_part <- function(value, level) {
  if (level == 0) return(str_squish(value))
  map_chr(str_split(value, "~"), \(p) {
    p <- str_squish(head(p, level))
    paste(p[p != ""], collapse = " ~ ")
  })
}

named <- data |>
  inner_join(levels, by = "data_provider") |>
  group_by(data_provider, fixed_level) |>
  group_modify(\(d, k) mutate(d, name = fixed_part(d$partner_product_category, k$fixed_level))) |>
  ungroup()
partner_counts <- count(named, data_provider, fixed_level, name)

# How many groups use each category. Partners without group_identifier get NA
spread <- named |>
  group_by(data_provider) |>
  mutate(groups = n_distinct(group_identifier[group_identifier != ""])) |>
  group_by(data_provider, groups, name) |>
  summarise(n = n(), users = n_distinct(group_identifier), .groups = "drop") |>
  group_by(data_provider) |>
  summarise(groups = first(groups),
            values_one_group = sum(users == 1), entries_one_group = sum(n[users == 1]),
            values_10_groups = sum(users >= 10), share_10_groups = round(sum(n[users >= 10]) / sum(n), 3)) |>
  mutate(across(c(values_one_group, entries_one_group, values_10_groups, share_10_groups),
                \(x) if_else(groups > 1, x, NA)))

dir.create("docs/ora/coverage", recursive = TRUE, showWarnings = FALSE)
outputs <- character()

# 1. All partners side by side, number of categories for each share
partners <- partner_counts |>
  group_by(data_provider, fixed_level) |>
  group_modify(\(d, k) {
    curve <- coverage_curve(select(d, name, n))
    marks <- coverage_marks(curve, "Kategorien")
    tibble(categories = nrow(curve), entries = sum(curve$n), one_entry = sum(curve$n == 1),
           level = marks$level, needed = marks$rank)
  }) |>
  ungroup()
partners |>
  mutate(level = paste0("for_", 100 * level, "_percent")) |>
  pivot_wider(names_from = level, values_from = needed) |>
  arrange(desc(entries)) |>
  left_join(spread, by = "data_provider") |>
  rename(partner = data_provider) |>
  write_tsv("docs/ora/coverage/partners.tsv", na = "")
outputs <- c(outputs, "docs/ora/coverage/partners.tsv")

kind_of <- c("0" = "nur Freitext", "1" = "eine feste Stufe", "2" = "zwei feste Stufen")
order <- partners |> distinct(data_provider, entries) |> arrange(desc(entries)) |> pull(data_provider)
curves <- partner_counts |>
  group_by(data_provider, fixed_level) |>
  group_modify(\(d, k) coverage_curve(select(d, name, n))) |>
  ungroup() |>
  mutate(panel = factor(paste0(data_provider, ", ", kind_of[as.character(fixed_level)]),
                        levels = paste0(order, ", ", kind_of[as.character(levels$fixed_level[match(order, levels$data_provider)])])))
mark90 <- partners |>
  filter(level == 0.9) |>
  left_join(distinct(curves, data_provider, panel), by = "data_provider") |>
  mutate(label = paste0("90 % mit ", de(needed)))
top_of <- curves |> group_by(panel) |> summarise(top = max(rank) * 1.15)

plot_partners <- ggplot(curves, aes(share, rank)) +
  geom_vline(xintercept = 0.9, colour = light[["grid"]], linewidth = 0.4) +
  geom_step(colour = light[["s1"]], linewidth = 0.8, direction = "vh") +
  geom_blank(data = top_of, aes(x = 0, y = top)) +
  geom_point(data = mark90, aes(level, needed), size = 2, colour = light[["s1"]], fill = light[["bg"]],
             shape = 21, stroke = 1.3) +
  geom_text(data = mark90, aes(level, needed, label = label), hjust = 1.08, vjust = -0.6, size = 3.3,
            colour = light[["secondary"]]) +
  facet_wrap(vars(panel), ncol = 3, scales = "free_y") +
  scale_x_continuous(labels = \(x) paste0(de(100 * x), " %"), breaks = c(0, 0.5, 1),
                     limits = c(0, 1.02), expand = expansion(mult = c(0, 0))) +
  scale_y_continuous(labels = \(x) de(x), breaks = scales::breaks_pretty(3),
                     expand = expansion(mult = c(0, 0))) +
  labs(title = "Feste Listen brauchen wenige Kategorien, Freitext sehr viele",
       subtitle = "Kategorien je Partner, die nötig sind, um einen Anteil seiner Einträge abzudecken, die häufigsten zuerst. Achsen je Partner verschieden",
       x = "Anteil der Einträge", y = "Kategorien",
       caption = paste0("Kategorie ist der Teil aus einer festen Liste, ohne feste Liste der Freitext. ", source_note)) +
  theme_manuel() +
  theme(panel.spacing.x = unit(24, "pt"), panel.spacing.y = unit(16, "pt"),
        strip.text = element_text(size = 10))
outputs <- c(outputs, save_chart(plot_partners, "ora-coverage-partners", height = 620))

# 2. Restarters with its German category names
german <- read_csv(translations_file, col_types = cols(.default = col_character())) |>
  filter(file == "de.json") |>
  select(en, de)
restarters <- partner_counts |>
  filter(data_provider == "The Restart Project") |>
  left_join(german, by = c("name" = "en")) |>
  transmute(name = case_when(name == "Misc Unpowered" ~ "Verschiedenes, ohne Strom", !is.na(de) ~ de, TRUE ~ name), n)
curve <- coverage_curve(restarters)
marks <- coverage_marks(curve, "Kategorien")
facts <- coverage_facts(curve, marks)
write_tsv(facts, "docs/ora/coverage/restarters.tsv")
plot_restarters <- coverage_plot(
  curve, marks, "Kategorien",
  paste("Bei Restarters decken", marks$rank[marks$level == 0.9], "Kategorien 90 Prozent ab"),
  c(paste0("Kategorien von Restarters, die nötig sind, um einen Anteil der ", de(sum(curve$n)),
           " Einträge von The Restart Project abzudecken, die häufigsten zuerst."),
    paste0("1 % sind rund ", de(round(sum(curve$n) / 100, -1)), " Geräte")),
  c("Namen der Kategorien in der deutschen Fassung von restarters.net.", source_note),
  "Kategorien bei Restarters",
  paste("Am häufigsten sind", coverage_list(head(curve, 3)), "Einträgen"),
  paste("Am seltensten sind", coverage_list(arrange(tail(curve, 3), n)), "Einträgen"))
outputs <- c(outputs, "docs/ora/coverage/restarters.tsv", save_chart(plot_restarters, "ora-coverage-restarters"))

# 3. The ORA groups over all partners
groups <- data |> count(product_category) |> rename(name = product_category)
curve <- coverage_curve(transmute(groups, name, n))
marks <- coverage_marks(curve, "Gruppen")
write_tsv(coverage_facts(curve, marks), "docs/ora/coverage/groups.tsv")
plot_groups <- coverage_plot(
  curve, marks, "Gruppen",
  "Auch bei den ORA-Gruppen tragen wenige den Großteil",
  c(paste0("ORA-Gruppen, die nötig sind, um einen Anteil aller ", de(sum(curve$n)),
           " Einträge der Open Repair Data abzudecken, die häufigsten zuerst."),
    paste0("1 % sind rund ", de(round(sum(curve$n) / 100, -1)), " Geräte, gezählt über alle neun Partner")),
  c("Gruppen mit Strom nach dem Open Repair Data Standard, ohne Strom wie in den Daten.", source_note),
  "ORA-Gruppen",
  paste("Am häufigsten sind", coverage_list(head(curve, 3)), "Einträgen"),
  paste("Am seltensten sind", coverage_list(arrange(tail(curve, 3), n)), "Einträgen"))
outputs <- c(outputs, "docs/ora/coverage/groups.tsv", save_chart(plot_groups, "ora-coverage-groups"))

write_run("docs/ora/coverage/partners.tsv", inputs = c(unname(files), partner_file, translations_file),
          outputs = outputs)
print(read_tsv("docs/ora/coverage/partners.tsv", show_col_types = FALSE), width = Inf)
print(facts, width = Inf)
print(coverage_facts(curve, marks), width = Inf)
