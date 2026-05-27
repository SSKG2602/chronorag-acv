from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.layer2_crossdomain.methods.chronorag_full.adapter import retrieve_with_chronorag_adapter
from benchmarks.layer2_crossdomain.schemas import QuestionCase, load_corpus, load_questions


DEFAULT_CORPUS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_corpus.jsonl"
DEFAULT_QUESTIONS = ROOT / "benchmarks/layer2_crossdomain/data/layer2_questions.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Print no-Vertex ChronoRAG Layer 2 retrieval diagnostics.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--first-n", type=int, default=5)
    args = parser.parse_args()

    corpus = load_corpus(args.corpus)
    questions = load_questions(args.questions)
    selected = [case for case in questions if not args.case_id or case.id in set(args.case_id)]
    if not args.case_id:
        selected = selected[: args.first_n]

    for case in selected:
        rows, metadata = retrieve_with_chronorag_adapter(case, corpus, top_k=args.top_k)
        print(f"\n{case.id}")
        print(f"question: {case.question}")
        print(f"expected: {', '.join(case.expected_evidence_ids) or '(none)'}")
        print(f"temporal_granularity: {metadata.get('temporal_granularity')}")
        print(f"temporal_role: {metadata.get('temporal_role_detected')}")
        for index, row in enumerate(rows, start=1):
            score = metadata["selected_scores"].get(row.id)
            marker = "*" if row.id in case.expected_evidence_ids else " "
            print(f"{index}. {marker} {row.id} score={score} valid={row.valid_from} value={row.value}")


if __name__ == "__main__":
    main()
