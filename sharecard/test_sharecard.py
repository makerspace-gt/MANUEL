#!/usr/bin/env python3
"""Tests for sharecard.py with an invented spreadsheet, no real data.

Run in the repository root:
    python3 -m unittest sharecard/test_sharecard.py
"""

import datetime as dt
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

# Load the script by path, the folder of the same name would otherwise shadow it as a package.
_spec = importlib.util.spec_from_file_location("sharecard_script", Path(__file__).resolve().parent / "sharecard.py")
sharecard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sharecard)

HEADER = ["", "Datum", "Angemeldet", "bearbeitet", "gelungen", "teilweise gelungen", "vertagt", "nicht erfolgt",
          "abgebrochen", "keine Information", "no-show", "Spenden", "gelungen"]
NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"')


def cell(value):
    if value is None or value == "":
        return "<table:table-cell/>"
    if isinstance(value, dt.date):
        return (f'<table:table-cell office:value-type="date" office:date-value="{value.isoformat()}">'
                f"<text:p>{value:%d.%m.%y}</text:p></table:table-cell>")
    if isinstance(value, (int, float)):
        return f'<table:table-cell office:value-type="float" office:value="{value}"><text:p>{value}</text:p></table:table-cell>'
    return f'<table:table-cell office:value-type="string"><text:p>{value}</text:p></table:table-cell>'


def row(values, covered_first=False):
    cells = ["<table:covered-table-cell/>" if covered_first else cell(values[0])] + [cell(v) for v in values[1:]]
    return "<table:table-row>" + "".join(cells) + "</table:table-row>"


def event(date, registered, processed, fixed, partly, postponed, failed, no_show, donations, **extra):
    values = ["", date, registered, processed, fixed, partly, postponed, failed, 0, 0, no_show, donations, ""]
    for name, value in extra.items():
        values[HEADER.index(name)] = value
    return values


def build(path, header=HEADER, rows=None, grouped=None):
    badges = (f'<table:table table:name="Namensschilder">{row(["", "Datum", "Name"])}'
              f'{row(["", dt.date(2026, 11, 7), "Erika Beispiel"])}</table:table>')
    group = "<table:table-row-group>" + "".join(row(r) for r in grouped or []) + "</table:table-row-group>"
    body = row(header) + group + "".join(row(r, covered_first=i == 0) for i, r in enumerate(rows or []))
    content = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {NS}><office:body><office:spreadsheet>'
               f'{badges}<table:table table:name="Eingabe">{body}</table:table>'
               f"</office:spreadsheet></office:body></office:document-content>")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("content.xml", content)


class ShareCardTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "statistik.ods"
        old = [event(dt.date(2023, 3, 4), 50, 50, 25, 5, 10, 10, 0, 200.0),
               event(dt.date(2024, 3, 2), 10, 10, 5, 0, 3, 2, 0, 50.0),
               event(dt.date(2025, 1, 4), 0, 0, 0, 0, 0, 0, 0, 0)]
        rows = [event(dt.date(2025, 6, 7), 20, 19, 10, 1, 4, 4, 1, 120.0),
                event(dt.date(2026, 3, 7), 30, 28, 14, 2, 6, 6, 2, 210.0),
                event(dt.date(2026, 10, 17), 17, 17, 8, 1, 4, 4, 0, 99.5),
                event(dt.date(2026, 11, 7), 17, 16, 6, 1, 6, 3, 1, 100.46),
                event(dt.date(2026, 11, 21), 0, 0, 0, 0, "Winterpause", 0, 0, 0),
                event(dt.date(2026, 12, 5), 0, 0, 0, 0, 0, 0, 0, 0)]
        build(self.path, rows=rows, grouped=old)

    def tearDown(self):
        self.dir.cleanup()

    def summary(self, **kwargs):
        return sharecard.summarize(sharecard.read_events(self.path), dt.date(2026, 11, 7), **kwargs)

    def test_reads_only_the_input_sheet(self):
        events = sharecard.read_events(self.path)
        self.assertEqual(len(events), 9)
        self.assertEqual(len([e for e in events if e["date"] == dt.date(2026, 11, 7)]), 1)

    def test_numbers_and_donations(self):
        s = self.summary()
        self.assertEqual((s["registered"], s["processed"], s["no_show"]), (17, 16, 1))
        self.assertEqual(s["results"], {"fixed": 6, "partly": 1, "postponed": 6, "failed": 3, "unknown": 0})
        self.assertEqual(sharecard.euro(s["per_device"]), "6,28 €")
        self.assertIsNone(s["spontaneous"])

    def test_rank_uses_three_years_without_cancelled_dates(self):
        s = self.summary()
        self.assertEqual(sorted(s["values"]), [10, 17, 20, 30])
        self.assertEqual((s["at_most"], s["rank"]), (2, 50))

    def test_next_date_skips_cancelled(self):
        self.assertEqual(self.summary()["next"], dt.date(2026, 12, 5))

    def test_wrong_sum_stops(self):
        build(self.path, rows=[event(dt.date(2026, 11, 7), 18, 16, 6, 1, 6, 3, 1, 100.46)])
        with self.assertRaises(sharecard.DataError):
            self.summary()

    def test_spontaneous_column(self):
        header = HEADER + ["spontan"]
        rows = [event(dt.date(2026, 11, 7), 17, 16, 6, 1, 6, 3, 1, 100.46) + [6]]
        build(self.path, header=header, rows=rows)
        s = self.summary()
        self.assertEqual(s["spontaneous"], 6)
        self.assertIn("davon 6 spontan", sharecard.counts_line(s))

    def test_card_has_totals_but_no_names(self):
        s = self.summary()
        svg = sharecard.render(s, highlight="Ein Radio von 1985 spielt wieder")
        alt = sharecard.alt_text(s, "Ein Radio von 1985 spielt wieder")
        for content in (svg, alt):
            self.assertIn("17 angemeldet, 16 bearbeitet, 1 nicht erschienen", content)
            self.assertNotIn("Erika", content)
        self.assertIn("50 %", svg)
        self.assertIn("Nächster Termin Samstag, 5. Dezember 2026", alt)


if __name__ == "__main__":
    unittest.main()
