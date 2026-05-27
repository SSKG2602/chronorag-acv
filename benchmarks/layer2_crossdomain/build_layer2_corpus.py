from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_ROOT = Path("data/raw/layer2_crossdomain")
DEFAULT_OUT = Path("benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl")

DOMAIN_ORDER = ["macro_fred", "market_index", "sec_submissions", "federal_register", "github_releases"]
CSV_LABELS = {
    "cpi": ("United States CPI", "CPI index", "index_1982_84"),
    "dgs10": ("United States 10-year Treasury", "10-year Treasury yield", "percent"),
    "fedfunds": ("Federal Funds Rate", "effective federal funds rate", "percent"),
    "unrate": ("United States unemployment rate", "unemployment rate", "percent"),
    "djia": ("Dow Jones Industrial Average", "index close", "index_points"),
    "nasdaqcom": ("NASDAQ Composite", "index close", "index_points"),
    "sp500": ("S&P 500", "index close", "index_points"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the real Layer 2 processed corpus from local raw files.")
    parser.add_argument("--raw-root", default=str(RAW_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--target-rows", type=int, default=5000)
    args = parser.parse_args()

    raw_root = Path(args.raw_root)
    rows_by_domain = {
        "macro_fred": _read_csv_domain(raw_root / "fred", "macro_fred"),
        "market_index": _read_csv_domain(raw_root / "stocks", "market_index"),
        "sec_submissions": _read_sec(raw_root / "sec"),
        "federal_register": _read_regulations(raw_root / "regulations"),
        "github_releases": _read_software(raw_root / "software"),
    }
    quotas = _balanced_quotas({domain: len(rows) for domain, rows in rows_by_domain.items()}, args.target_rows)
    selected: list[dict[str, Any]] = []
    for domain in DOMAIN_ORDER:
        selected.extend(_even_sample(rows_by_domain[domain], quotas[domain]))
    selected.sort(key=lambda row: row["id"])
    _write_jsonl(Path(args.out), selected)
    print(f"Wrote {len(selected)} rows to {args.out}")
    print("Domain distribution:")
    for domain in DOMAIN_ORDER:
        print(f"- {domain}: {sum(1 for row in selected if row['domain'] == domain)}")


def _read_csv_domain(path: Path, domain: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for csv_path in sorted(path.glob("*.csv")):
        series = csv_path.stem.lower()
        entity, metric, unit = CSV_LABELS.get(series, (series.upper(), series.upper(), "value"))
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            value_col = next((field for field in reader.fieldnames or [] if field != "observation_date"), None)
            if not value_col:
                continue
            for idx, record in enumerate(reader):
                date = record.get("observation_date")
                value = record.get(value_col)
                if not date or value in {None, ""}:
                    continue
                rows.append(
                    _row(
                        evidence_id=f"l2:{domain}:{series}:{date}",
                        domain=domain,
                        source_family=domain,
                        source_file=str(csv_path),
                        source_kind="time_series",
                        entity=entity,
                        related_entities=[series.upper(), value_col],
                        metric_or_claim=metric,
                        value=value,
                        unit=unit,
                        valid_from=date,
                        valid_to=date,
                        transaction_time=None,
                        temporal_type="valid_time_exact",
                        raw_text=f"{entity} {metric} was {value} {unit} on {date}.",
                        metadata={"source_id": value_col, "row_index": idx, "source_path": str(csv_path)},
                        tags=[domain, "raw_pool", "exact_valid_time"],
                    )
                )
    return rows


def _read_sec(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for json_path in sorted(path.glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        company = data.get("name") or json_path.stem
        ticker = (data.get("tickers") or [json_path.stem.upper()])[0]
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocDescription", [])
        for idx, form in enumerate(forms):
            filing_date = _list_get(filing_dates, idx)
            report_date = _list_get(report_dates, idx)
            accession = _list_get(accession_numbers, idx) or f"{idx}"
            description = _list_get(descriptions, idx) or "SEC filing"
            if not filing_date:
                continue
            valid_from = report_date or None
            temporal_type = "valid_time_exact" if report_date else "transaction_time_only"
            clean_accession = re.sub(r"[^A-Za-z0-9_-]+", "-", accession)
            rows.append(
                _row(
                    evidence_id=f"l2:sec_submissions:{ticker.lower()}:{clean_accession}",
                    domain="sec_submissions",
                    source_family="sec_submissions",
                    source_file=str(json_path),
                    source_kind="sec_submission",
                    entity=company,
                    related_entities=[ticker, str(data.get("cik", "")), str(data.get("sicDescription", ""))],
                    metric_or_claim=f"{form} filing",
                    value=form,
                    unit=None,
                    valid_from=valid_from,
                    valid_to=valid_from,
                    transaction_time=filing_date,
                    temporal_type=temporal_type,
                    raw_text=(
                        f"{company} filed {form} on {filing_date}"
                        + (f" for report date {report_date}" if report_date else "")
                        + f"; primary document description: {description}."
                    ),
                    metadata={
                        "source_id": accession,
                        "source_name": company,
                        "filing_time": filing_date,
                        "report_date": report_date,
                        "source_path": str(json_path),
                    },
                    tags=["sec", "filing", "raw_pool"],
                )
            )
    return rows


def _read_regulations(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for json_path in sorted(path.glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for idx, item in enumerate(data.get("results", [])):
            publication_date = item.get("publication_date")
            effective_on = item.get("effective_on")
            document_number = item.get("document_number") or f"{idx}"
            agency = _agency_name(item)
            title = _clean(item.get("title") or "Federal Register document")
            abstract = _clean(item.get("abstract") or title)
            temporal_type = "valid_time_exact" if effective_on else "transaction_time_only"
            rows.append(
                _row(
                    evidence_id=f"l2:federal_register:{document_number}",
                    domain="federal_register",
                    source_family="federal_register",
                    source_file=str(json_path),
                    source_kind=item.get("type") or "federal_register_document",
                    entity=agency,
                    related_entities=[item.get("type") or "", document_number],
                    metric_or_claim=title[:120],
                    value=item.get("type"),
                    unit=None,
                    valid_from=effective_on,
                    valid_to=effective_on,
                    transaction_time=publication_date,
                    temporal_type=temporal_type,
                    raw_text=f"{agency} published {item.get('type', 'document')} {document_number} on {publication_date}: {abstract[:420]}",
                    metadata={
                        "source_id": document_number,
                        "source_name": agency,
                        "publication_time": publication_date,
                        "html_url": item.get("html_url"),
                        "source_path": str(json_path),
                    },
                    tags=["federal_register", "regulation", "raw_pool"],
                )
            )
    return rows


def _read_software(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for json_path in sorted(path.glob("*.json")):
        repo = json_path.stem.replace("_releases", "")
        data = json.loads(json_path.read_text(encoding="utf-8"))
        for item in data:
            published = (item.get("published_at") or item.get("created_at") or "")[:10]
            if not published:
                continue
            tag = item.get("tag_name") or item.get("name") or str(item.get("id"))
            body = _clean(item.get("body") or item.get("name") or tag)
            release_id = str(item.get("id") or tag)
            rows.append(
                _row(
                    evidence_id=f"l2:github_releases:{repo}:{release_id}",
                    domain="github_releases",
                    source_family="github_releases",
                    source_file=str(json_path),
                    source_kind="github_release",
                    entity=repo,
                    related_entities=[tag, item.get("target_commitish") or ""],
                    metric_or_claim=f"release {tag}",
                    value=tag,
                    unit=None,
                    valid_from=published,
                    valid_to=published,
                    transaction_time=published,
                    temporal_type="revision" if item.get("prerelease") else "valid_time_exact",
                    raw_text=f"{repo} released {tag} on {published}. {body[:420]}",
                    metadata={
                        "source_id": release_id,
                        "source_name": repo,
                        "release_time": published,
                        "html_url": item.get("html_url"),
                        "source_path": str(json_path),
                    },
                    tags=["github", "release", "raw_pool"],
                )
            )
    return rows


def _row(**kwargs: Any) -> dict[str, Any]:
    evidence_id = kwargs.pop("evidence_id")
    return {
        "id": evidence_id,
        "domain": kwargs["domain"],
        "source_family": kwargs["source_family"],
        "source_file": kwargs.get("source_file"),
        "source_kind": kwargs.get("source_kind"),
        "entity": kwargs["entity"],
        "related_entities": [item for item in kwargs.get("related_entities", []) if item],
        "metric_or_claim": kwargs["metric_or_claim"],
        "value": kwargs.get("value"),
        "unit": kwargs.get("unit"),
        "valid_from": kwargs.get("valid_from"),
        "valid_to": kwargs.get("valid_to"),
        "transaction_time": kwargs.get("transaction_time"),
        "temporal_type": kwargs["temporal_type"],
        "raw_text": kwargs["raw_text"],
        "metadata": kwargs.get("metadata") or {},
        "tags": kwargs.get("tags") or [],
    }


def _balanced_quotas(available: dict[str, int], target: int) -> dict[str, int]:
    quotas = {domain: 0 for domain in DOMAIN_ORDER}
    remaining = target
    active = set(DOMAIN_ORDER)
    while active and remaining > 0:
        share = max(1, remaining // len(active))
        progressed = False
        for domain in list(active):
            can_take = available[domain] - quotas[domain]
            take = min(share, can_take, remaining)
            quotas[domain] += take
            remaining -= take
            progressed = progressed or take > 0
            if quotas[domain] >= available[domain]:
                active.remove(domain)
        if not progressed:
            break
    if sum(quotas.values()) < target:
        raise SystemExit(f"Raw pool has only {sum(available.values())} usable rows, cannot build {target}.")
    return quotas


def _even_sample(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda row: row["id"])
    if count >= len(rows):
        return rows
    if count <= 0:
        return []
    if count == 1:
        return [rows[0]]
    indexes = [round(idx * (len(rows) - 1) / (count - 1)) for idx in range(count)]
    return [rows[idx] for idx in indexes]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _list_get(values: list[Any], idx: int) -> str:
    if idx >= len(values) or values[idx] in {None, ""}:
        return ""
    return str(values[idx])


def _agency_name(item: dict[str, Any]) -> str:
    agencies = item.get("agencies") or []
    if agencies and isinstance(agencies[0], dict):
        return agencies[0].get("name") or agencies[0].get("raw_name") or "Federal Register"
    return "Federal Register"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


if __name__ == "__main__":
    main()
