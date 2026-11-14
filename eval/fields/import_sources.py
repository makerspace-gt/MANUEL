#!/usr/bin/env python3
"""Step 1 of import, tidy, transform for the fields of ORA, anstiftung and Restarters.

Reads the sources that are not tables yet and writes each of them as a table to docs/fields/import,
as close to the source as possible. Nothing is joined or renamed here, that happens in the next
steps in R. Sources that are tables already, like the categories of the run sheet of the anstiftung
in quellen/anstiftung or the aggregate files of the Open Repair Data, are read there directly.

    ora_codes.csv                       codes and texts of repair status and barrier in standard.rst
    anstiftung_<table>.csv              tables of database.sql of mapped-repair-events, as in the dump
    restarters_device_fields.csv        fields of a device in the API with format, description and enum
    restarters_category_fields.csv      fields of a category in the API, among them powered
    restarters_ords.csv                 how the ORDS export of Restarters maps categories and barriers
    restarters_translations.csv         every text of the German language files of Restarters

When a source is updated, for example a new commit of a submodule, running this script again
refreshes the import.

Run in the repository root:
    python3 eval/fields/import_sources.py
"""

import csv
import html
import json
import re
from pathlib import Path

OUT = Path("docs/fields/import")
STANDARD = Path("quellen/openrepair-datastandard/standard.rst")
ANSTIFTUNG_SQL = Path("mapped-repair-events/config/sql/init/database.sql")
ANSTIFTUNG_TABLES = ("categories", "ords_categories", "form_fields", "form_field_options",
                     "form_field_options_extra_infos")
RESTARTERS = Path("quellen/restarters.net")


def write(name, header, rows):
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{path}: {len(rows)} Zeilen")


def ora_codes():
    """The two tables of codes at the end of the field reference in standard.rst."""
    text = STANDARD.read_text(encoding="utf-8")
    rows = []
    for field, heading in (("repair_status", "Repair status values"),
                           ("repair_barrier_if_end_of_life", "Repair barrier values")):
        table = text.split(heading, 1)[1].split("\n\n", 2)[1]
        rows += [[field, *line.split(None, 1)] for line in table.splitlines() if re.match(r"^\d+\s+\S", line)]
    write("ora_codes.csv", ["field", "code", "text"], rows)


def anstiftung_tables():
    """Selected tables of the MySQL dump, columns and values as in the INSERT, NULL as empty."""
    sql = ANSTIFTUNG_SQL.read_text(encoding="utf-8")
    for table in ANSTIFTUNG_TABLES:
        match = re.search(r"INSERT INTO `%s` \(([^)]*)\) VALUES\n(.*?);\n" % table, sql, re.S)
        header = [c.strip("` ") for c in match.group(1).split(",")]
        rows = []
        for line in re.findall(r"^\((.*)\)[,;]?$", match.group(2), re.M):
            values = next(csv.reader([line], quotechar="'", escapechar="\\", skipinitialspace=True))
            rows.append(["" if v == "NULL" else html.unescape(v) for v in values])
        write(f"anstiftung_{table}.csv", header, rows)


def openapi_properties(path):
    """Properties of the OpenAPI annotation of an API resource of Restarters."""
    source = path.read_text(encoding="utf-8")
    rows = []
    for block in source.split("@OA\\Property(")[1:]:
        def attribute(name):
            match = re.search(r'\b%s="([^"]*)"' % name, block)
            return match.group(1) if match else ""
        enum = re.search(r"enum=\{([^}]*)\}", block)
        values = re.findall(r'"([^"]+)"', enum.group(1)) if enum else [""]
        rows += [[attribute("property"), attribute("format"), attribute("description"), value] for value in values]
    return rows


def restarters_fields():
    header = ["field", "format", "description", "enum"]
    write("restarters_device_fields.csv", header, openapi_properties(RESTARTERS / "app/Http/Resources/Device.php"))
    write("restarters_category_fields.csv", header, openapi_properties(RESTARTERS / "app/Http/Resources/Category.php"))


def restarters_ords():
    """The maps of config/ords.php, one row per value of Restarters."""
    text = (RESTARTERS / "config/ords.php").read_text(encoding="utf-8")

    def block(name):
        return text.split(f"'{name}' => [", 1)[1].split("\n    ],", 1)[0]

    rows = [["categories_powered", k, v, i]
            for k, v, i in re.findall(r"'([^']+)' => \['([^']+)', (\d+)\]", block("categories_powered"))]
    rows += [["categories_unpowered", k, v, ""] for k, v in re.findall(r"'([^']+)' => '([^']+)'", block("categories_unpowered"))]
    rows += [["barriers", k, v, ""] for k, v in re.findall(r"'([^']+)' => '([^']+)'", block("barriers"))]
    write("restarters_ords.csv", ["map", "restarters", "ords", "ords_id"], rows)


def php_strings(path):
    """Flat 'key' => 'text' pairs of a Laravel language file, nested arrays as key.subkey."""
    rows, stack = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        nested = re.match(r"^\s*'([^']+)'\s*=>\s*\[\s*$", line)
        pair = re.match(r"^\s*'([^']+)'\s*=>\s*'((?:[^'\\]|\\.)*)',?\s*$", line)
        if nested:
            stack.append(nested.group(1))
        elif pair:
            rows.append([".".join(stack + [pair.group(1)]), pair.group(2).replace("\\'", "'")])
        elif re.match(r"^\s*\],?\s*$", line) and stack:
            stack.pop()
    return rows


def restarters_translations():
    """English and German of every text, from lang/<locale>.json and lang/<locale>/*.php.

    In the JSON files the English text is the key. In the PHP files the key is a name like
    partials.more_time, which joins English and German."""
    rows = []
    english = json.loads((RESTARTERS / "lang/en.json").read_text(encoding="utf-8"))
    german = json.loads((RESTARTERS / "lang/de.json").read_text(encoding="utf-8"))
    for key in sorted(set(english) | set(german)):
        rows.append(["de.json", key, english.get(key, key), german.get(key, "")])
    for path in sorted((RESTARTERS / "lang/en").glob("*.php")):
        en = dict(php_strings(path))
        de_path = RESTARTERS / "lang/de" / path.name
        de = dict(php_strings(de_path)) if de_path.exists() else {}
        for key in en:
            rows.append([path.name, f"{path.stem}.{key}", en[key], de.get(key, "")])
    write("restarters_translations.csv", ["file", "key", "en", "de"], rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ora_codes()
    anstiftung_tables()
    restarters_fields()
    restarters_ords()
    restarters_translations()


if __name__ == "__main__":
    main()
