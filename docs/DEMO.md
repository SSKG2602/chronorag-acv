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
2. Route the query into the world-economy domain.
3. Use valid-time axis.
4. Retrieve candidate passages through BM25 + ANN.
5. Apply temporal filtering around 1870.
6. Rerank candidates.
7. Produce an answer with source attribution.
8. Emit controller stats.

## Commands

```bash
git clone https://github.com/SSKG2602/chronorag.git
cd chronorag

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export CHRONORAG_LIGHT=1

python -m cli.chronorag_cli ingest data/sample/docs

python -m cli.chronorag_cli answer \
  --query "Europe GDP per capita in 1870 (1990 intl$)" \
  --mode INTELLIGENT \
  --axis valid
```

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
evidence-only-fallback.png
```

## Demo Transcript Template

```text
$ python -m cli.chronorag_cli ingest data/sample/docs
Ingested: <N> chunks

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

Add one test case where retrieved evidence conflicts or falls outside the requested window.

Expected behavior:

- The answer should not fabricate certainty.
- The system should return evidence-only mode or degraded confidence.
- The attribution card should show alternative windows or conflict/counterfactual traces.

## Public README Rule

Do not write “fully production-ready” until this demo folder contains real screenshots and repeatable output.
