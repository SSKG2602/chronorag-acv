from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER_DIR = Path("docs/paper_assets")
TABLE_DIR = Path("chronorag/stdcomp/results/paper_tables")

TABLE_METRICS = {
    "table1_layer2a_retrieval_standard_comparison": [
        "hit_at_1",
        "hit_at_5",
        "forbidden_absent_at_5",
        "category_primary_pass",
    ],
    "table3_qa50_llm_post_filter_baselines": [
        "retrieval_hit_at_1",
        "retrieval_hit_at_5",
        "strict_combined_pass",
        "deterministic_hard_contract_pass",
        "llm_judge_overall_pass",
        "llm_judge_semantic_pass",
        "valid_time_used_correct",
        "expected_evidence_cited",
    ],
    "table4_qa50_answer_level_comparison": [
        "retrieval_hit5_or_evidence_available",
        "strict_combined_pass",
        "deterministic_hard_contract_pass",
        "llm_judge_overall_pass",
        "llm_judge_semantic_pass",
        "expected_evidence_cited",
        "valid_time_used_correct",
    ],
}


def main() -> None:
    generated = []
    for table_id, metrics in TABLE_METRICS.items():
        source = TABLE_DIR / f"{table_id}.json"
        if source.exists():
            generated.append(add_ci_for_table(source, metrics))
    for source in sorted(TABLE_DIR.glob("topk_sensitivity*.json")):
        generated.append(add_ci_for_table(source, ["hit_at_k", "forbidden_absent_at_k", "category_primary_pass"]))
    update_index(generated)
    for item in generated:
        print(f"Wrote {item['markdown_path']}")
        print(f"Wrote {item['csv_path']}")
        print(f"Wrote {item['json_path']}")


def add_ci_for_table(source: Path, proportion_keys: list[str]) -> dict[str, Any]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    table_id = payload["metadata"]["table_id"]
    out_id = f"{table_id}_with_ci"
    rows = []
    for row in payload.get("rows") or []:
        enriched = dict(row)
        cases = int(row.get("cases") or 0)
        for key in proportion_keys:
            value = row.get(key)
            if not isinstance(value, (int, float)) or value < 0.0 or value > 1.0 or cases <= 0:
                continue
            count = int(round(float(value) * cases))
            low, high = wilson_interval(count, cases)
            enriched[f"{key}_count"] = count
            enriched[f"{key}_denominator"] = cases
            enriched[f"{key}_ci95_low"] = low
            enriched[f"{key}_ci95_high"] = high
        rows.append(enriched)

    meta = dict(payload["metadata"])
    meta["table_id"] = out_id
    meta["title"] = f"{meta['title']} with Wilson 95% CI"
    meta["generated_at"] = datetime.now(timezone.utc).isoformat()
    meta["wilson_ci"] = {
        "z": 1.959963984540054,
        "count_source": "Counts inferred by round(metric * cases) when explicit counts were not present.",
        "mrr_note": "MRR values do not receive Wilson CIs.",
    }
    columns = payload.get("columns") or []
    notes = list(payload.get("notes") or [])
    notes.append("Wilson 95% confidence intervals are shown for proportion metrics only; counts are inferred from ratio times cases where needed.")
    output = {"metadata": meta, "columns": columns, "rows": rows, "notes": notes}
    json_path = TABLE_DIR / f"{out_id}.json"
    md_path = PAPER_DIR / f"{out_id}.md"
    csv_path = PAPER_DIR / f"{out_id}.csv"
    write_json(json_path, output)
    write_markdown(md_path, meta["title"], rows, columns, notes, proportion_keys)
    write_csv(csv_path, rows, columns, proportion_keys)
    return {
        "id": out_id,
        "title": meta["title"],
        "markdown_path": str(md_path),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
    }


def wilson_interval(count: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (math.nan, math.nan)
    phat = count / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2.0 * n)) / denom
    margin = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def write_markdown(
    path: Path,
    title: str,
    rows: list[dict[str, Any]],
    columns: list[dict[str, str]],
    notes: list[str],
    proportion_keys: list[str],
) -> None:
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(column["label"] for column in columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in rows:
        cells = [format_cell(row, column["key"], proportion_keys) for column in columns]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "Notes:"])
    lines.extend(f"- {note}" for note in notes)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[dict[str, str]], proportion_keys: list[str]) -> None:
    base_fields = [column["key"] for column in columns]
    ci_fields = [
        field
        for key in proportion_keys
        for field in (f"{key}_count", f"{key}_denominator", f"{key}_ci95_low", f"{key}_ci95_high")
    ]
    extra = sorted({key for row in rows for key in row if key not in set(base_fields) | set(ci_fields)})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*base_fields, *ci_fields, *extra], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def format_cell(row: dict[str, Any], key: str, proportion_keys: list[str]) -> str:
    value = row.get(key)
    if value is None:
        return "n/a"
    if key in proportion_keys and isinstance(value, (int, float)):
        low = row.get(f"{key}_ci95_low")
        high = row.get(f"{key}_ci95_high")
        count = row.get(f"{key}_count")
        den = row.get(f"{key}_denominator")
        if isinstance(low, float) and isinstance(high, float):
            return f"{float(value):.4f} ({count}/{den}; 95% CI {low:.4f}-{high:.4f})"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def update_index(generated: list[dict[str, Any]]) -> None:
    index_path = PAPER_DIR / "chrono_tables_index.md"
    existing = index_path.read_text(encoding="utf-8") if index_path.exists() else "# ChronoRAG Paper Tables Index\n"
    lines = [existing.rstrip(), "", "## Wilson CI Variants", ""]
    for item in generated:
        lines.append(f"- [{item['title']}]({Path(item['markdown_path']).name})")
        lines.append(f"  - CSV: `{Path(item['csv_path']).name}`")
        lines.append(f"  - JSON: `{item['json_path']}`")
    lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
