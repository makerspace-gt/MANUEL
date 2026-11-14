#!/usr/bin/env python3
"""Writes one CSV per platform with its field names as header and all possible values below.

Each column lists the values a field can take, one per row, in the order of the source. Free text
and numbers have no fixed values, their column stays empty. Where two columns belong together, like
a category and its id or top category, they share the row. Values are written as text, the
platforms that store numbers instead (anstiftung, ORDS codes) are listed in docs/fields/README.md.

* docs/fields/ora.csv: columns of the aggregate files of the Open Repair Data, values from
  standard.rst, the unpowered groups from the non-eee file, which the standard does not list
* docs/fields/anstiftung.csv: fields of the run sheet on reparatur-initiativen.org with the names of
  the table info_sheets, values from the saved form in quellen/anstiftung
* docs/fields/restarters.csv: fields of a device in the API of Restarters.net, values from the
  OpenAPI description in quellen/restarters/Device.php and the categories in kategorien.csv

Run in the repository root:
    python3 eval/fields/platform_values.py
"""

import csv
import re
from itertools import zip_longest
from pathlib import Path

OUT = Path("docs/fields")
ORA = Path("quellen/openrepair-data")
STANDARD = Path("quellen/openrepair-datastandard/standard.rst")
ANSTIFTUNG = Path("quellen/anstiftung")
RESTARTERS = Path("quellen/restarters")


def unique(values):
    return list(dict.fromkeys(v for v in values if v))


def write(name, columns):
    """columns is a dict of field name to list of values."""
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(zip_longest(*columns.values(), fillvalue=""))
    print(f"{path}: {len(columns)} Felder, {sum(len(v) for v in columns.values())} Werte")


def code_table(text, heading):
    """Rows of a simple reST table of codes and texts under the given heading."""
    section = text.split(heading, 1)[1].split("\n\n", 2)[1]
    return [line.split(None, 1)[1] for line in section.splitlines()
            if re.match(r"^\d+\s+\S", line)]


def ora():
    eee = ORA / "OpenRepairData_v0.3_aggregate_202607_eee.csv"
    non_eee = ORA / "OpenRepairData_v0.3_aggregate_202607_non-eee.csv"
    header = next(csv.reader(eee.open(encoding="utf-8")))
    text = STANDARD.read_text(encoding="utf-8")
    groups = list(csv.DictReader((ORA / "OpenRepairData_v0.3_Product_Categories_eee.csv").open(encoding="utf-8")))
    unpowered = sorted({row["product_category"] for row in csv.DictReader(non_eee.open(encoding="utf-8"))})
    columns = {field: [] for field in header}
    columns["product_category"] = [g["product_category"] for g in groups] + unpowered
    columns["product_category_id"] = [g["product_category_id"] for g in groups] + ["0"] * len(unpowered)
    columns["repair_status"] = code_table(text, "Repair status values")
    columns["repair_barrier_if_end_of_life"] = code_table(text, "Repair barrier values")
    write("ora.csv", columns)


def anstiftung():
    form = list(csv.DictReader((ANSTIFTUNG / "felder.csv").open(encoding="utf-8")))
    categories = list(csv.DictReader((ANSTIFTUNG / "kategorien.csv").open(encoding="utf-8")))
    brands = list(csv.DictReader((ANSTIFTUNG / "marken.csv").open(encoding="utf-8")))

    def options(field):
        return unique(row["text"] for row in form if row["field"] == f"InfoSheets[{field}]")

    # Order of the run sheet, names of the table info_sheets in database.sql, the power supply is
    # stored in info_sheets_form_field_options, the top category in categories.parent_id
    write("anstiftung.csv", {
        # Category and top category stay in one row, some names like Sonstiges exist under several
        "parent_id": [row["top_category"] for row in categories],
        "category_id": [row["category"] for row in categories],
        "brand_id": unique(row[next(iter(row))] for row in brands),
        "device_name": [],
        "device_age": [],
        "form_field_options": options("form_field_options][_ids]["),
        "defect_description": [],
        "defect_found_reason": options("defect_found_reason"),
        "repair_postponed_reason": options("repair_postponed_reason"),
        "no_repair_reason": options("no_repair_reason"),
        "no_repair_reason_text": [],
        "device_must_not_be_used_anymore": options("device_must_not_be_used_anymore"),
    })


def restarters():
    source = (RESTARTERS / "Device.php").read_text(encoding="utf-8")
    columns = {}
    for block in source.split("@OA\\Property(")[1:]:
        name = re.search(r'property="([^"]+)"', block).group(1)
        enum = re.search(r"enum=\{([^}]*)\}", block)
        columns[name] = re.findall(r'"([^"]+)"', enum.group(1)) if enum else []
    categories = list(csv.DictReader((RESTARTERS / "kategorien.csv").open(encoding="utf-8")))
    columns["category"] = [row["category"] for row in categories]
    write("restarters.csv", columns)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ora()
    anstiftung()
    restarters()


if __name__ == "__main__":
    main()
