# ChronoRAG Demo Plan

This document defines the minimum demo required to make ChronoRAG credible on GitHub, LinkedIn, and research-oriented applications.

## Demo Goal

Show that ChronoRAG can answer a time-sensitive question by retrieving evidence with valid-time metadata, ranking it through temporal fusion, and returning an attribution card plus controller stats.

## Required Demo Scenario

Question:

```text
Europe GDP per capita in 1870 (1990 intl$)
```

Expected behavior:

1. Ingest sample historical/world-economy documents.
2. Build chunk records with raw evidence, retrieval context, and temporal metadata.
3. Route the query into the world-economy domain.
4. Use valid-time axis.
5. Retrieve candidate passages through BM25 + ANN.
6. Apply temporal filtering around 1870.
7. Rerank candidates.
8. Produce an answer with source attribution.
9. Emit controller stats.

The intended chunking architecture is Temporal Contextual Chunking: ChronoRAG's
chunking strategy, inspired by contextual retrieval but extended for valid-time
retrieval, transaction-time tracking, temporal fusion, ChronoSanity, and
attribution. Demo claims should distinguish this implemented architecture from
the current smoke path and the benchmark result reports.

## Commands

```bash
git clone https://github.com/SSKG2602/chronorag.git
cd chronorag

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export CHRONORAG_LIGHT=1

python -m cli.chronorag_cli ingest data/sample/smoke/*

python -m cli.chronorag_cli answer \
  --query "Western Europe GDP per capita in 1870 1990 international dollars" \
  --mode INTELLIGENT \
  --axis valid
```

The larger `data/sample/docs/aihistory*.txt` files are optional full-demo inputs.
The smoke dataset is the default CI/laptop path.

## Screenshots to Capture

Store screenshots in:

```text
assets/demo/
```

Required images:

```text
api-health.png
cli-ingest.png
cli-answer.png
attribution-card.png
controller-stats.png
```

## Demo Transcript Template

```text
$ python -m cli.chronorag_cli ingest data/sample/smoke/*
{
  "ingested_chunks": 6,
  "source_files": [
    "data/sample/smoke/temporal_world_economy.jsonl"
  ],
  "chunk_ids": ["..."]
}

$ python -m cli.chronorag_cli answer --query "Europe GDP per capita in 1870 (1990 intl$)" --mode INTELLIGENT --axis valid
{
  "answer": "...",
  "attribution_card": {
    "sources": [
      {
        "uri": "...",
        "valid_window": {"from": "1870-01-01", "to": "1871-01-01"},
        "authority": 0.0
      }
    ],
    "confidence": {
      "level": "HIGH|MEDIUM|LOW",
      "reasons": []
    }
  },
  "controller_stats": {
    "hops_used": 1,
    "hop_plan": {"planned": 1, "executed": 1},
    "latency_ms": 0,
    "degraded": null
  },
  "evidence_only": false
}
```

## Evidence-Only Fallback Demo

Not committed yet as a separate screenshot. The current public demo assets focus on the
verified light-mode smoke path: health check, ingest, answer, attribution card, and
controller stats.

Expected behavior:

- The answer should not fabricate certainty.
- The system should return evidence-only mode or degraded confidence.
- The attribution card should show alternative windows or conflict/counterfactual traces.

## Public README Rule

Do not present the demo as production ready until this folder contains real screenshots and repeatable output.
