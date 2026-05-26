from __future__ import annotations

import csv
import json
import re
import statistics
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


RAW_ROOT = Path("data/raw/temporal_eval_v2")
OUT_ROOT = Path("data/sample/temporal_eval_v2")
CORPUS_PATH = OUT_ROOT / "temporal_eval_v2_corpus.jsonl"
SOURCES_PATH = OUT_ROOT / "temporal_eval_v2_sources.json"
MANIFEST_PATH = OUT_ROOT / "temporal_eval_v2_manifest.json"

PREFERRED_YEARS = [1, 1000, 1500, 1600, 1700, 1820, 1870, 1913, 1950, 1973, 1998, 2018, 2022]
PREFERRED_ENTITIES = [
    "Western Europe",
    "Europe",
    "World",
    "India",
    "China",
    "Japan",
    "United Kingdom",
    "United States",
    "Netherlands",
    "France",
    "Brazil",
    "Latin America",
    "Africa",
]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def clean_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def display_value(value: Any) -> str:
    number = clean_number(value)
    if number is None:
        return str(value)
    if abs(number) >= 100:
        return f"{number:,.0f}"
    return f"{number:,.2f}"


def year_dates(year: int) -> tuple[str, str]:
    return f"{year:04d}-01-01", f"{year:04d}-12-31"


def make_row(
    *,
    row_id: str,
    source_family: str,
    source_file: str,
    source_kind: str,
    entity: str,
    metric: str,
    unit: str,
    raw_text: str,
    expected_use: str,
    value: Any = None,
    year: Optional[int] = None,
    valid_from: Optional[str] = None,
    valid_to: Optional[str] = None,
    transaction_time: Optional[str] = None,
    temporal_granularity: str = "year",
    temporal_type: str = "valid_time_exact",
    source_page: Optional[int] = None,
    source_table: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    if year is not None and not valid_from and not valid_to:
        valid_from, valid_to = year_dates(year)
    source_uri = f"file:///{source_file}"
    retrieval_text = (
        f"Document: Temporal Eval v2 {source_family}. Section: {source_table or metric}. "
        f"Entity: {entity}. Unit: {unit}. "
        f"Temporal scope: {year if year is not None else (valid_from[:4] + '-' + valid_to[:4] if valid_from and valid_to else temporal_type)}. "
        f"Original chunk: {raw_text}"
    )
    facets = {
        "domain": "world-economy",
        "source": source_family,
        "source_family": source_family,
        "region": region or entity,
        "unit": unit,
    }
    payload: Dict[str, Any] = {
        "id": row_id,
        "doc_id": f"temporal-eval-v2:{source_family}",
        "external_id": row_id,
        "source_family": source_family,
        "source_file": source_file,
        "source_kind": source_kind,
        "source_uri": source_uri,
        "source_page": source_page,
        "source_table": source_table,
        "entity": entity,
        "region": region,
        "metric": metric,
        "value": clean_number(value),
        "unit": unit,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "transaction_time": transaction_time,
        "temporal_granularity": temporal_granularity,
        "temporal_type": temporal_type,
        "raw_text": raw_text,
        "retrieval_text": retrieval_text,
        "expected_use": expected_use,
        "uri": source_uri,
        "text": raw_text,
        "section": source_table or metric,
        "facets": facets,
        "tags": ["temporal-eval-v2", "world-economy"],
        "provenance": {
            "uri": source_uri,
            "observed_at": f"{transaction_time or '2023'}-01-01T00:00:00Z",
        },
    }
    if year is not None:
        payload["year"] = year
    if valid_from and valid_to:
        payload["valid"] = {"from": valid_from, "to": valid_to, "granularity": temporal_granularity}
    if transaction_time:
        payload["tx"] = {"start": f"{transaction_time}-01-01"}
    return payload


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_xlsx_matrix(path: Path, sheet_name: str) -> List[List[str]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    office_r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(path) as archive:
        shared = []
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for si in shared_root.findall("m:si", ns):
            shared.append("".join((t.text or "") for t in si.iter(f"{{{ns['m']}}}t")))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("r:Relationship", rel_ns)}
        target = None
        for sheet in workbook.findall("m:sheets/m:sheet", ns):
            if sheet.attrib.get("name") == sheet_name:
                target = rel_map[sheet.attrib[office_r]]
                break
        if target is None:
            raise ValueError(f"Sheet not found: {sheet_name}")

        root = ET.fromstring(archive.read(f"xl/{target}"))
        rows: List[List[str]] = []
        for row in root.findall("m:sheetData/m:row", ns):
            values: Dict[int, str] = {}
            for cell in row.findall("m:c", ns):
                ref = cell.attrib.get("r", "")
                col = 0
                for char in ref:
                    if char.isalpha():
                        col = col * 26 + ord(char.upper()) - 64
                value_node = cell.find("m:v", ns)
                value = "" if value_node is None else value_node.text or ""
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                values[col - 1] = value
            if values:
                width = max(values) + 1
                rows.append([values.get(idx, "") for idx in range(width)])
        return rows


def load_xlsx_sheet(path: Path, sheet_name: str) -> List[Dict[str, str]]:
    rows = load_xlsx_matrix(path, sheet_name)
    header = rows[0]
    return [dict(zip(header, row + [""] * (len(header) - len(row)))) for row in rows[1:]]


def add_unique(rows: List[Dict[str, Any]], row: Dict[str, Any]) -> None:
    if row["id"] not in {item["id"] for item in rows}:
        rows.append(row)


def build_maddison_rows() -> List[Dict[str, Any]]:
    path = RAW_ROOT / "maddison/mpd2023_web.xlsx"
    full = load_xlsx_sheet(path, "Full data")
    regional_matrix = load_xlsx_matrix(path, "Regional data")
    rows: List[Dict[str, Any]] = []

    regional_entities = {
        "Western Europe": "Western Europe",
        "World": "World",
        "Latin America": "Latin America",
        "Africa": "Sub Saharan Africa",
    }
    regional_years = [1870, 1913, 1950, 1973, 1998, 1820, 1500, 1600, 1700]
    regional_indexes = {
        "East Asia": 1,
        "Eastern Europe": 2,
        "Latin America": 3,
        "Middle East and North Africa": 4,
        "South and South East Asia": 5,
        "Sub Saharan Africa": 6,
        "Western Europe": 7,
        "Western Offshoots": 8,
        "World": 9,
    }
    for values in regional_matrix[2:]:
        year = int(float(values[0] or 0))
        if year not in regional_years:
            continue
        for entity, column in regional_entities.items():
            if entity == "Western Europe" and year == 1820:
                continue
            value = clean_number(values[regional_indexes[column]] if len(values) > regional_indexes[column] else "")
            if value is None:
                continue
            row_id = f"e2:maddison:regional:gdp_pc:{slug(entity)}:{year}"
            text = f"{entity} GDP per capita was {display_value(value)} in {year}, measured in 2011 international dollars in Maddison Project 2023 regional data."
            add_unique(
                rows,
                make_row(
                    row_id=row_id,
                    source_family="maddison_project_2023",
                    source_file=str(path),
                    source_kind="structured_excel",
                    entity=entity,
                    region=entity,
                    metric="GDP per capita",
                    value=value,
                    unit="2011 international dollars",
                    year=year,
                    source_table="Regional data GDPpc",
                    raw_text=text,
                    expected_use="answer_evidence",
                ),
            )

    country_entities = ["India", "China", "Japan", "United Kingdom", "United States", "Netherlands", "France", "Brazil"]
    country_years = [1, 1000, 1500, 1600, 1700, 1870, 1913, 1950, 1973, 1998, 2018]
    for record in full:
        entity = record.get("country", "")
        year_raw = record.get("year", "")
        if entity not in country_entities or not year_raw:
            continue
        year = int(float(year_raw))
        if year not in country_years or (entity == "China" and year == 1820):
            continue
        value = clean_number(record.get("gdppc"))
        if value is None:
            continue
        row_id = f"e2:maddison:country:gdp_pc:{slug(entity)}:{year}"
        text = f"{entity} GDP per capita was {display_value(value)} in {year}, measured in 2011 international dollars in Maddison Project 2023 country data."
        add_unique(
            rows,
            make_row(
                row_id=row_id,
                source_family="maddison_project_2023",
                source_file=str(path),
                source_kind="structured_excel",
                entity=entity,
                region=record.get("region") or None,
                metric="GDP per capita",
                value=value,
                unit="2011 international dollars",
                year=year,
                source_table="Full data",
                raw_text=text,
                expected_use="answer_evidence",
            ),
        )
        if len(rows) >= 68:
            return rows[:68]
    return rows[:68]


def build_owid_gdppc_rows() -> List[Dict[str, Any]]:
    path = RAW_ROOT / "owid/gdp-per-capita-maddison-project-database.csv"
    source = load_csv_rows(path)
    wanted_entities = ["India", "China", "Japan", "United Kingdom", "United States", "Netherlands", "France", "Brazil"]
    wanted_years = [1870, 1913, 1950, 1973, 1998, 2018]
    rows: List[Dict[str, Any]] = []
    for record in source:
        entity = record["Entity"]
        year = int(record["Year"])
        if entity not in wanted_entities or year not in wanted_years:
            continue
        if entity == "China" and year == 1820:
            continue
        value = clean_number(record.get("GDP per capita"))
        if value is None:
            continue
        row_id = f"e2:owid_gdppc:gdp_pc:{slug(entity)}:{year}"
        text = f"OWID Maddison reports {entity} GDP per capita as {display_value(value)} in {year}."
        add_unique(
            rows,
            make_row(
                row_id=row_id,
                source_family="owid_maddison_gdppc",
                source_file=str(path),
                source_kind="structured_csv",
                entity=entity,
                metric="GDP per capita",
                value=value,
                unit="Maddison GDP per capita",
                year=year,
                source_table="OWID GDP per capita Maddison Project Database",
                raw_text=text,
                expected_use="answer_evidence",
            ),
        )
        if len(rows) >= 42:
            return rows
    return rows


def build_owid_gdp_rows() -> List[Dict[str, Any]]:
    path = RAW_ROOT / "owid/gdp-maddison-project-database.csv"
    source = load_csv_rows(path)
    wanted_entities = ["India", "China", "Japan", "United Kingdom", "United States", "France", "Brazil"]
    wanted_years = [1870, 1913, 1950, 1973, 1998, 2018]
    rows: List[Dict[str, Any]] = []
    for record in source:
        entity = record["Entity"]
        year = int(record["Year"])
        if entity not in wanted_entities or year not in wanted_years:
            continue
        value = clean_number(record.get("GDP"))
        if value is None:
            continue
        row_id = f"e2:owid_gdp:gdp_total:{slug(entity)}:{year}"
        text = f"OWID Maddison reports total GDP for {entity} as {display_value(value)} in {year}."
        add_unique(
            rows,
            make_row(
                row_id=row_id,
                source_family="owid_maddison_gdp",
                source_file=str(path),
                source_kind="structured_csv",
                entity=entity,
                metric="Total GDP",
                value=value,
                unit="Maddison GDP",
                year=year,
                source_table="OWID GDP Maddison Project Database",
                raw_text=text,
                expected_use="distractor",
            ),
        )
        if len(rows) >= 28:
            return rows
    return rows


def build_global_gdp_rows() -> List[Dict[str, Any]]:
    path = RAW_ROOT / "owid/global-gdp-over-the-long-run.csv"
    source = load_csv_rows(path)
    wanted_years = [1, 1000, 1500, 1600, 1700, 1820, 1870, 1913, 1950, 1973, 1998, 2018]
    rows: List[Dict[str, Any]] = []
    for record in source:
        year = int(record["Year"])
        if year not in wanted_years:
            continue
        value = clean_number(record.get("GDP"))
        if value is None:
            continue
        row_id = f"e2:owid_global:gdp_total:world:{year}"
        text = f"OWID global long-run data reports world GDP as {display_value(value)} in {year}."
        add_unique(
            rows,
            make_row(
                row_id=row_id,
                source_family="owid_global_gdp_long_run",
                source_file=str(path),
                source_kind="structured_csv",
                entity="World",
                region="World",
                metric="Total GDP",
                value=value,
                unit="international dollars",
                year=year,
                source_table="OWID global GDP over the long run",
                raw_text=text,
                expected_use="distractor",
            ),
        )
        if len(rows) >= 10:
            return rows
    return rows


def build_oecd_rows() -> List[Dict[str, Any]]:
    path = RAW_ROOT / "oecd/oecd3.pdf"
    rows: List[Dict[str, Any]] = []
    passages = [
        ("western_europe_exact_1870", "Western Europe", "GDP per capita", "OECD table-derived evidence reports Western Europe GDP per capita as 1,960 in 1870, measured in 1990 international dollars.", "1870-01-01", "1870-12-31", "year", "valid_time_exact", "answer_evidence"),
        ("western_europe_exact_1913", "Western Europe", "GDP per capita", "OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.", "1913-01-01", "1913-12-31", "year", "valid_time_exact", "answer_evidence"),
        ("western_europe_range_1870_1913", "Western Europe", "GDP per capita", "Table-derived OECD note: Western Europe GDP per capita increased between 1870 and 1913.", "1870-01-01", "1913-12-31", "range", "valid_time_range", "distractor"),
        ("western_europe_broad_1000_2006", "Western Europe", "GDP per capita", "OECD background passage discusses Western Europe GDP per capita across benchmark years from 1000 to 2006.", "1000-01-01", "2006-12-31", "range", "valid_time_range", "distractor"),
        ("world_broad_1_2006", "World", "GDP per capita", "OECD world economy summary covers long-run world GDP per capita benchmark years from year 1 to 2006.", "0001-01-01", "2006-12-31", "range", "valid_time_range", "distractor"),
        ("china_background_1820", "China", "GDP per capita", "OECD background note discusses China around 1820 without giving an exact GDP per capita value in this derived passage.", "1800-01-01", "1850-12-31", "range", "valid_time_range", "insufficient"),
        ("publication_2006", "OECD publication", "Publication metadata", "The OECD world economy publication was released in 2006.", None, None, "document", "transaction_time_only", "metadata_trap"),
        ("data_about_1870_pub_2006", "Western Europe", "Publication metadata", "The 2006 OECD publication contains historical benchmark data about 1870.", None, None, "document", "transaction_time_only", "metadata_trap"),
        ("methodology_unknown", "World", "Methodology", "OECD methodology notes explain that historical GDP estimates use purchasing power parity adjustments.", None, None, "unknown", "ambiguous_time", "metadata_trap"),
    ]
    for idx, (suffix, entity, metric, text, start, end, granularity, temporal_type, expected_use) in enumerate(passages):
        row_id = f"e2:oecd_pdf:{suffix}"
        rows.append(
            make_row(
                row_id=row_id,
                source_family="oecd_world_economy_pdf",
                source_file=str(path),
                source_kind="pdf_derived_passage",
                entity=entity,
                region=entity if entity in PREFERRED_ENTITIES else None,
                metric=metric,
                unit="1990 international dollars" if "GDP" in metric else "n/a",
                valid_from=start,
                valid_to=end,
                transaction_time="2006",
                temporal_granularity=granularity,
                temporal_type=temporal_type,
                source_page=idx + 1,
                source_table="Derived short passage",
                raw_text=text,
                expected_use=expected_use,
            )
        )
    # Repeat compact table-derived notes across entities/years without copying PDF text.
    for entity in ["Western Europe", "World", "India", "Japan", "Latin America", "Africa"]:
        for year in [1870, 1913, 1950, 1973]:
            if len(rows) >= 30:
                return rows
            text = f"OECD table-derived note references {entity} benchmark-year GDP per capita evidence for {year}."
            rows.append(
                make_row(
                    row_id=f"e2:oecd_pdf:table_note:{slug(entity)}:{year}",
                    source_family="oecd_world_economy_pdf",
                    source_file=str(path),
                    source_kind="pdf_derived_passage",
                    entity=entity,
                    region=entity,
                    metric="GDP per capita",
                    unit="1990 international dollars",
                    year=year,
                    transaction_time="2006",
                    source_page=2,
                    source_table="Benchmark year table note",
                    raw_text=text,
                    expected_use="distractor",
                )
            )
    return rows


def build_synthetic_rows() -> List[Dict[str, Any]]:
    path = "data/sample/temporal_eval_v2/synthetic_traps.jsonl"
    rows = [
        make_row(
            row_id="e2:synthetic:conflict:western_europe:gdp_pc:1913",
            source_family="synthetic_temporal_traps",
            source_file=path,
            source_kind="synthetic_trap",
            entity="Western Europe",
            region="Western Europe",
            metric="GDP per capita",
            value=3200,
            unit="2011 international dollars",
            year=1913,
            temporal_type="conflict_claim",
            raw_text="Synthetic conflict trap reports Western Europe GDP per capita as 3,200 in 1913, conflicting with source-backed records.",
            expected_use="conflict",
        ),
        make_row(
            row_id="e2:synthetic:conflict:western_europe:gdp_pc:1870",
            source_family="synthetic_temporal_traps",
            source_file=path,
            source_kind="synthetic_trap",
            entity="Western Europe",
            region="Western Europe",
            metric="GDP per capita",
            value=1800,
            unit="2011 international dollars",
            year=1870,
            temporal_type="conflict_claim",
            raw_text="Synthetic conflict trap reports Western Europe GDP per capita as 1,800 in 1870, conflicting with source-backed records.",
            expected_use="conflict",
        ),
    ]
    traps = [
        ("wrong_year_india_1870_for_1913", "India", 1870, "GDP per capita", "Wrong-year trap for India repeats 1870 GDP per capita language near a 1913 query.", "distractor"),
        ("wrong_year_japan_1913_for_1950", "Japan", 1913, "GDP per capita", "Wrong-year trap for Japan repeats 1913 GDP per capita language near a 1950 query.", "distractor"),
        ("western_europe_industrial_ambiguous", "Europe", None, "GDP per capita", "Around the industrial era, Europe GDP per capita changed substantially, but this trap gives no exact valid year.", "insufficient"),
        ("publication_year_trap_2006", "Western Europe", None, "Publication metadata", "Synthetic metadata trap says the source was imported in 2006 but gives no valid GDP year.", "metadata_trap"),
        ("metric_confusion_gdp_total", "Western Europe", 1870, "Total GDP", "Metric confusion trap mentions Western Europe total GDP in 1870, not GDP per capita.", "distractor"),
        ("broad_1870_1913_no_exact", "Western Europe", None, "GDP per capita", "Synthetic broad-range trap says Western Europe GDP per capita rose over 1870 to 1913 without giving either exact value.", "distractor"),
        ("unknown_background_ppp", "World", None, "Methodology", "Synthetic background says PPP adjustments matter for historical GDP comparisons but gives no valid year.", "metadata_trap"),
        ("china_partial_background", "China", None, "GDP per capita", "Synthetic China background mentions early nineteenth-century GDP per capita context but provides no exact 1820 value.", "insufficient"),
        ("same_entity_wrong_metric_india", "India", 1913, "Total GDP", "Metric trap gives India total GDP in 1913 rather than GDP per capita.", "distractor"),
        ("same_year_wrong_entity_1913", "Europe", 1913, "GDP per capita", "Wrong-entity trap gives Europe GDP per capita context in 1913 rather than Western Europe.", "distractor"),
    ]
    for suffix, entity, year, metric, text, use in traps:
        valid_from = valid_to = None
        granularity = "unknown"
        temporal_type = "ambiguous_time"
        if year is not None:
            valid_from, valid_to = year_dates(year)
            granularity = "year"
            temporal_type = "valid_time_exact"
        rows.append(
            make_row(
                row_id=f"e2:synthetic:{suffix}",
                source_family="synthetic_temporal_traps",
                source_file=path,
                source_kind="synthetic_trap",
                entity=entity,
                region=entity,
                metric=metric,
                unit="2011 international dollars" if "GDP" in metric else "n/a",
                year=year,
                valid_from=valid_from,
                valid_to=valid_to,
                temporal_granularity=granularity,
                temporal_type=temporal_type,
                raw_text=text,
                expected_use=use,
            )
        )
    rows.append(
        make_row(
            row_id="e2:synthetic:source_family_grounding_policy",
            source_family="synthetic_temporal_traps",
            source_file=path,
            source_kind="synthetic_trap",
            entity="India",
            region="India",
            metric="GDP per capita",
            unit="2011 international dollars",
            temporal_granularity="unknown",
            temporal_type="ambiguous_time",
            raw_text=(
                "Source-family grounding policy: when OWID and Maddison both provide GDP per capita records, "
                "cite source-backed evidence IDs and source family names separately, and avoid unsupported value mixing."
            ),
            expected_use="answer_evidence",
        )
    )
    return rows


def build_corpus() -> List[Dict[str, Any]]:
    rows = (
        build_maddison_rows()
        + build_owid_gdppc_rows()
        + build_owid_gdp_rows()
        + build_global_gdp_rows()
        + build_oecd_rows()
        + build_synthetic_rows()
    )
    if len(rows) < 150:
        raise SystemExit(f"Temporal Eval v2 corpus too small: {len(rows)} rows")
    return rows[:200]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    rows = build_corpus()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_jsonl(CORPUS_PATH, rows)
    family_counts = Counter(row["source_family"] for row in rows)
    sources = {
        family: sorted({row["source_file"] for row in rows if row["source_family"] == family})
        for family in family_counts
    }
    SOURCES_PATH.write_text(json.dumps(sources, indent=2), encoding="utf-8")
    manifest = {
        "benchmark": "temporal_eval_v2",
        "description": "Controlled multi-source temporal retrieval and grounding benchmark.",
        "row_count": len(rows),
        "source_family_counts": dict(sorted(family_counts.items())),
        "raw_root": str(RAW_ROOT),
        "generated_files": [str(CORPUS_PATH), str(SOURCES_PATH), str(MANIFEST_PATH)],
        "value_policy": "Source-backed rows use values present in the raw files. Synthetic rows are explicit traps/conflicts.",
        "oecd_policy": "PDF-derived rows use short derived passages and metadata only; no long copyrighted text is copied.",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
