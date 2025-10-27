# TimeGuard ChronoRAG

TimeGuard ChronoRAG is a research-grade retrieval-augmented generation (RAG)
stack designed for time-sensitive knowledge bases. The scaffold emphasizes
deterministic temporality, auditable provenance, and modular experimentation
with retrieval and large language models (LLMs). ChronoGuard policies enforce
temporal compliance from ingest through answer synthesis, enabling analysts to
trace every statement back to overlapping validity windows.

## Architecture Overview

ChronoRAG is organized as a service-oriented Python 3.11 application:

- **API layer** (`app/`): FastAPI endpoints exposed by `uvicorn_runner`,
  dependency-injection helpers (`deps.py`), and orchestration services.
- **Core pipeline** (`core/`): Retrieval heuristics, fusion strategies,
  generator utilities, and LLM backends.
- **Storage layer** (`storage/`): Persistent vector database (PVDB) adapters,
  Postgres/pgvector schemas, and ORM models.
- **CLI tooling** (`cli/`): Operational workflows for ingesting corpora,
  issuing queries, and performing smoke tests.
- **Configuration** (`config/` + `environment.yml`): Model selection, policy
  tuning, and environment pinning.
- **Notebooks & scripts** (`notebooks/`, `scripts/`): Colab integration,
  lightweight benchmarking, and developer automation.

The system operates on three pillars—**ingest**, **retrieve**, and **answer**—
with ChronoGuard controls gating each phase.

## Data Flow

1. **Ingest**  
   Documents arrive through the CLI or API and are chunked, normalized, and
   written to PVDB with temporal metadata (valid window, transaction window,
   authority, units, region). Chrono fingerprints prevent drift between updates.

2. **Retrieve**  
   The hybrid retrieval service fans out across BM25 lexical search, ANN
   embeddings, and temporal filters before reranking with a cross-encoder and
   optional LLM judge. Monotone temporal fusion ensures relevance never improves
   when time compliance worsens.

3. **Answer**  
   The generator fuses ChronoPassages into a structured prompt, selects an LLM
   backend (local Hugging Face, llama.cpp, Ollama, or OpenAI-compatible), and
   renders an attribution card. When models fail or evidence conflicts,
   deterministic fallbacks provide evidence-only digests.

## Key Components

- `app/services/ingest_service.py`  
  Handles ingestion pipelines, chunking, and metadata enrichment. Supports
  authoritative source tagging and Chrono fingerprinting.

- `app/services/retrieve_service.py`  
  Orchestrates hybrid retrieval with domain-aware weight profiles, time
  filtering, and ranking via cross-encoder/LLM judge. Emits observability
  metadata (coverage, fan-out, hop execution count).

- `app/services/answer_service.py`  
  Runs ChronoGuard controller planning, conflict detection, and answer
  generation. Tracks planned vs. executed hops, ChronoSanity degradation, and
  attribution assembly.

- `core/generator/*`  
  Provides prompts, backend loaders, and structured fallbacks. Supports remote
  Hugging Face models, 4-bit loading hints, and deterministic generation with
  stop tokens.

- **Answer JSON Envelope**  
  The generator enforces a strict JSON schema for numeric timelines and range
  estimates: `{ "range": {low, high, most_likely, unit}, "bullets": [...] }`.
  Validation ensures the LLM supplies plausible values, two evidence bullets
  with year references, and 1990 international dollar units before the payload
  is returned downstream.

- `core/dhqc/*`  
  Implements the Domain Heuristic Query Controller (DHQC) for hop planning and
  candidate budgets based on coverage signals.

- `storage/pvdb/*`  
  Defines data access objects and models for the Postgres + pgvector backing
  store, including entity/unit extraction and temporal filters.

## Temporal Safety & ChronoGuard

- **Temporal pre-mask** trims candidates outside the requested window before
  reranking.
- **Monotone temporal fusion** penalizes misaligned evidence so time-respecting
  passages dominate the final ranking.
- **ChronoSanity** detects overlapping claims and can degrade responses to
  evidence-only outputs when conflicts exceed configurable thresholds.
- **Attribution cards** embed source URIs, windows, authority scores, and
  counterfactual timelines to explain conflicting evidence.
- **Structured validation** rejects malformed LLM output; on failure the system
  retries with a narrower prompt and ultimately reverts to an evidence digest.

## Model Strategy

`config/models.yaml` describes the ensemble:

- Embeddings default to `BAAI/bge-base-en-v1.5`.
- Reranking uses `BAAI/bge-reranker-v2-m3` with fallback cross-encoders.
- LLM strategy now targets the Lightning AI hosted `openai/gpt-5` endpoint
  configured in `config/models.yaml`. Optional llama.cpp and Ollama backends
  remain supported, but you must install their dependencies manually if you
  enable them.
- Prompt limits cap per-pass passage counts and snippet sizes to keep context
  within GPU memory constraints while preserving determinism.

## Policy & Configuration

- `config/policy.yaml` (and related policy sets) control authority weighting,
  ChronoSanity overlap thresholds, and domain-specific fusion parameters.
- `config/models.yaml` toggles model backends, prompt limits, and generation
  temperatures (default 0.0 for repeatability).
- Environment variables:
  - `LIGHTNING_API_KEY` overrides the baked-in API key for the Lightning AI endpoint.
  - `LLM_ENDPOINT` / `LLM_API_KEY` remain available for custom OpenAI-compatible providers.
  - `HF_TOKEN` is only needed when you re-enable gated Hugging Face models.
  - `CHRONORAG_LIGHT` to switch between stubbed light mode and full models.

## Observability & Telemetry

- `controller_stats` emitted by the API exposes hop plans (planned vs executed),
  coverage signals, latency, token counts, and degradation reasons.
- `audit_trail` records ChronoSanity conflict traces and policy overrides.
- Logging surfaces backend failures, fallback activations, and prompt trimming.

## Extensibility Roadmap

- Swap embeddings or rerankers by editing `config/models.yaml`.
- Add new temporal policies or domains by extending `policy_sets`.
- Integrate additional backends (e.g., custom inference endpoints) by
  subclassing `LLMBackend` in `core/generator/llm_loader.py`.
- Implement multi-hop retrieval plans by re-invoking `retrieve` when
  `hop_shortfall` is detected in controller statistics.

## Running ChronoRAG

Operational setup, environment preparation, CLI workflows, and testing commands
are documented in [`howtorunme.md`](howtorunme.md). Refer to that guide for
platform-specific instructions (macOS, Linux, Kaggle, Colab).

## License

ChronoRAG inherits its licensing from the original repo. See `LICENSE` for full
terms and attribution requirements.
