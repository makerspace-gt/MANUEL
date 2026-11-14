# Repair data of Makerspace Gütersloh e.V. in ORDS format

Manifest for the export produced by [ords_export.R](../../eval/ora/ords_export.R), following the section "Data format" of the [Open Repair Data Standard v0.3](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L637-L665), which asks for a manifest where data differs from or adds to the standard. The data itself is not public yet. It will be published in the folder `Statistik/ords` of [makerspace-gt/repair-cafe](https://github.com/makerspace-gt/repair-cafe), see [ADR 51](../adr/0051-reparaturdaten-nach-ords-oeffentlich-bereitstellen.adoc). Which data we record is set in [ADR 52](../adr/0052-erfasste-daten-festlegen.adoc).

## Source

The Repair Café of Makerspace Gütersloh e.V. in Gütersloh, Germany, records every request and repair as a ticket in Zammad. A ticket stands for one item. Items that come back to later events keep their ticket.

## Rows

One row per repair attempt, as the standard asks. An item that was at several events has one row per event. The earlier attempts have the status Repairable, the last one carries the final result.

## Standard columns

The descriptions are quoted from the [field details](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L118-L377) of the standard. Required and optional follow its [overview](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L62-L117), names and types its [field reference](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L383-L478).

| Column | Standard | Description in the standard | Our values |
|---|---|---|---|
| id | required | "Unique record identifier" | `msg_<ticket>_<event date as YYYYMMDD>`, unique per repair attempt and stable across exports |
| data_provider | required | "Uniquely identifies the partner providing the data." | Makerspace Gütersloh e.V. |
| country | required | "This is the country where the repair event (and thus the repair attempt) took place." | DEU |
| partner_product_category | required | "The original product categorisation supplied within the partner dataset i.e. the categories used to map to the ORDS product categories." | English name of the item from our open [catalogue](../../katalog/README.md), the German name where the English one is still missing |
| product_category | optional | "A value drawn from a list of ORDS category strings." | ORDS product category as mapped in our catalogue. Unpowered groups use the names of the published data |
| product_category_id | optional | "Unique identifier associated with each product_category." | id of that category, 0 for unpowered groups as in the published data |
| brand | optional | "Name of the item’s “brand” if it is identifiable." | as recorded. Generic for items without a brand, as the standard calls them, Unknown if nobody recorded it |
| year_of_manufacture | optional | "The year, or approximate year, that the item was made." | from the rating plate or the visitor, empty for now |
| product_age | optional | "The estimated age of the product when seen." | age in whole years at the event, empty for now. See product_age_qualifier |
| repair_status | required | "This is the outcome of the repair attempt that was undertaken on the device at the event." | Fixed, Repairable, End of life or Unknown, mapped from our result as in [result_mapping.tsv](../../eval/ora/result_mapping.tsv), which follows the anstiftung. Partly successful repairs count as Fixed |
| repair_barrier_if_end_of_life | optional | "A value that can be ascribed when a repair status is designated as “End of life”." | values of the standard where our result names a reason, Item too worn out written as "Product too worn out" |
| group_identifier | optional | "Unique group identification name, number or code." | 17503, the id of our initiative on reparatur-initiativen.org, the same id the anstiftung rows already use |
| event_date | required | "Date on which the repair event took place." | YYYY-MM-DD |
| problem | required | "A description of the problem identified with the device during the repair." | English translation of problem_de. Empty until the descriptions are anonymised |

## Additional columns

| Column | Description |
|---|---|
| repair_attempt | number of the attempt for this item, 1 for the first event, 2 for the second and so on |
| product_age_qualifier | how sure product_age is, exact, about or at least. The standard treats every age as an estimate, this column says which kind |
| problem_de | the problem in German as recorded, in three parts: the defect reported or suspected before the event, the defect found during the repair and the solution |
| knowledge_base_url | link to the article in our knowledge base on this kind of repair, where there is one |
| anstiftung_event_uid | `event_uid` of the event on reparatur-initiativen.org |
| anstiftung_category_id | `category_id` of the category in the run sheet form of the anstiftung |
| anstiftung_category | German name of that category |
| anstiftung_parent_category | German name of its parent category, `parent_id` in the database of the anstiftung, Oberkategorie in its form |
| catalog_key | key of the item in our catalogue, `ORDS group.Restarters category.anstiftung category[.own]` |

The columns of the anstiftung use the names of its own database, so the anstiftung could take over the same rows for its statistics without a second recording.

## Personal data

No names, contact details or free text from visitors are exported as they are. The free text columns brand, problem and problem_de are reviewed and anonymised before each release.

## Licence

CC BY-SA 4.0, like the Open Repair Data.
