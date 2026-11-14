# Writes lauf.json next to the output of an R analysis, see docs/adr/0027-laeufe-reproduzierbar-festhalten.adoc
# and docs/adr/0049-daten-mit-r-auswerten.adoc. Same fields as eval/lauf.py where they apply, plus the
# version of R, the CRAN snapshot and the version of every attached or loaded package.
#
#   source("eval/r/lauf.R")
#   write_run("docs/grafiken/beispiel.svg", inputs = c("quellen/openrepair-data/..."), outputs = c("docs/grafiken/beispiel.svg"))

write_run <- function(target, inputs = character(), outputs = character(), extra = list()) {
  git <- function(...) tryCatch(system2("git", c(...), stdout = TRUE, stderr = FALSE), error = function(e) "")
  files <- function(paths) lapply(paths, function(p) list(path = p, sha256 = unname(digest_file(p))))
  info <- sessionInfo()
  pkgs <- c(info$otherPkgs, info$loadedOnly)
  run <- c(list(
    date = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z", tz = "Europe/Berlin"),
    command = paste(commandArgs(), collapse = " "),
    commit = paste(git("rev-parse", "HEAD"), collapse = ""),
    dirty = length(git("status", "--porcelain", "--untracked-files=no")) > 0,
    inputs = files(inputs),
    outputs = files(outputs),
    r = list(version = R.version.string, repos = unname(getOption("repos")),
             image = Sys.getenv("MANUEL_R_IMAGE", "localhost/manuel-r:4.6.1"),
             packages = lapply(pkgs[order(names(pkgs))], function(p) p$Version)),
    host = list(kernel = Sys.info()[["release"]], machine = Sys.info()[["machine"]])
  ), extra)
  path <- file.path(if (dir.exists(target)) target else dirname(target), "lauf.json")
  jsonlite::write_json(run, path, auto_unbox = TRUE, pretty = TRUE)
  invisible(path)
}

digest_file <- function(path) {
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  sub(" .*", "", out)
}
