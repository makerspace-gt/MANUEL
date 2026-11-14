# Repair data of Makerspace Gütersloh e.V. in ORDS format

Manifest for the export produced by [ords_export.R](../../eval/ora/ords_export.R), following the section "Data format" of the [Open Repair Data Standard v0.3](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L637-L665). It describes where our data differs from or adds to the standard. The data itself is not public yet, see [ADR 51](../adr/0051-reparaturdaten-nach-ords-in-einem-eigenen-repo-veroeffentlichen.adoc).

## Source

The Repair Café of Makerspace Gütersloh e.V. in Gütersloh, Germany, records every request and repair as a ticket in Zammad. A ticket stands for one item. Items that come back to later events keep their ticket.

## Rows

One row per repair attempt, as the standard asks. An item that was at several events has one row per event. The earlier attempts have the status Repairable, the last one carries the final result.

## Standard columns

| Column | Our values |
|---|---|
| id | `msg_<ticket>_<event date as YYYYMMDD>`, unique per repair attempt and stable across exports |
| data_provider | Makerspace Gütersloh e.V. |
| country | DEU |
| partner_product_category | English name of the item from our open [catalogue](../../katalog/README.md), one fixed value per item type |
| product_category, product_category_id | ORDS product category as mapped in our catalogue. Unpowered groups use the names of the published data and id 0 |
| brand | as recorded, Unknown if empty. Not normalised, typos are kept |
| year_of_manufacture, product_age | empty for now, our tickets do not record them yet |
| repair_status | Fixed, Repairable or End of life. Partly successful repairs are not exported until the team decides |
| repair_barrier_if_end_of_life | values of the standard, including Item too worn out, written as "Product too worn out" |
| group_identifier | 17503, the id of our initiative on reparatur-initiativen.org, the same id the anstiftung rows already use |
| event_date | YYYY-MM-DD |
| problem | empty until the descriptions are anonymised. It will hold the fault found during the repair, not the visitor's description |

## Additional columns

| Column | Meaning |
|---|---|
| anstiftung_event_id | id of the event on reparatur-initiativen.org, empty where we do not know it yet |
| anstiftung_category_id | id of the category in the run sheet form of the anstiftung |
| anstiftung_category | top category and category of that form, as "top category ~ category" in German, the same form the anstiftung rows in the Open Repair Data use |
| catalog_key | key of the item in our catalogue, `ORDS group.Restarters category.anstiftung category[.own]` |

The additional columns let the anstiftung take over the same rows for its own statistics without a second recording, and they keep our mapping traceable.

## Personal data

No names, contact details or free text from visitors are exported. The only free text columns are brand and, once anonymised, problem. A person reviews new rows before each release.

## Licence

CC BY-SA 4.0, like the Open Repair Data.
