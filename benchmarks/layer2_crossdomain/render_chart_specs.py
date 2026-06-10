from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RESULTS = Path("benchmarks/layer2_crossdomain/results")
DEFAULT_ASSETS = Path("benchmarks/layer2_crossdomain/assets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Layer 2 chart-spec markdown from real result JSON files.")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS))
    parser.add_argument("--assets-dir", default=str(DEFAULT_ASSETS))
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    assets_dir = Path(args.assets_dir)
    payloads = _load_results(results_dir)
    if not payloads:
        print(f"No Layer 2 result JSON files found in {results_dir}. Nothing generated.")
        return

    assets_dir.mkdir(parents=True, exist_ok=True)
    _write_comparison_metrics(payloads, assets_dir / "comparison_metrics.md")
    _write_failure_breakdown(payloads, assets_dir / "failure_breakdown.md")
    print(f"Wrote chart specs to {assets_dir}")


def _load_results(results_dir: Path) -> list[dict[str, Any]]:
    payloads = []
    for path in sorted(results_dir.glob("layer2_*_results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "summary" in payload and "method" in payload:
            payload["_result_file"] = str(path)
            payloads.append(payload)
    return payloads


def _write_comparison_metrics(payloads: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Comparison Metrics Chart Spec",
        "",
        "Generated from real Layer 2 result JSON files. Do not edit values by hand.",
        "",
        "| Method | Result file | Corpus rows | Questions | Overall | Evidence | Valid-time | Transaction trap | Conflict | Refusal/partial |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for payload in payloads:
        summary = payload["summary"]
        lines.append(
            "| {method} | {file} | {rows} | {questions} | {overall:.2f} | {evidence:.2f} | {valid:.2f} | {tx:.2f} | {conflict:.2f} | {partial:.2f} |".format(
                method=payload["method"],
                file=payload["_result_file"],
                rows=payload.get("corpus_rows", 0),
                questions=payload.get("question_count", 0),
                overall=summary.get("overall_pass", 0.0),
                evidence=summary.get("evidence_correct", 0.0),
                valid=summary.get("valid_time_correct", 0.0),
                tx=summary.get("transaction_time_not_misused", 0.0),
                conflict=summary.get("conflict_warning_correct", 0.0),
                partial=summary.get("partial_refusal_correct", 0.0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_failure_breakdown(payloads: list[dict[str, Any]], path: Path) -> None:
    counts: dict[str, int] = {}
    for payload in payloads:
        for row in payload.get("results", []):
            for reason in row.get("validation", {}).get("failure_reasons", []):
                counts[reason] = counts.get(reason, 0) + 1
    lines = [
        "# Failure Breakdown Chart Spec",
        "",
        "Generated from real Layer 2 result JSON files. Empty means no failures in the scanned result files.",
        "",
        "| Failure reason | Count |",
        "|---|---:|",
    ]
    for reason, count in sorted(counts.items()):
        lines.append(f"| {reason} | {count} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
