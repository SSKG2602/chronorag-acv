# ChronoRAG Provider Mode

ChronoRAG has two answer synthesis modes:

- Light mode: `CHRONORAG_LIGHT=1`. This is deterministic, CI-safe, and uses the evidence digest fallback. It does not import Vertex AI libraries or require Google credentials.
- Provider mode: `CHRONORAG_LIGHT=0` with `CHRONORAG_PROVIDER=vertex`. Retrieval still runs first, then Gemini synthesizes an answer from the retrieved evidence only.

Provider mode only moves answer synthesis to remote Gemini/Vertex. Local
retrieval still uses the local embedding stack and therefore still needs memory
for embedding-based retrieval.

Provider answer quality depends on retrieved evidence quality. Temporal
Contextual Chunking is intended to improve evidence precision before
Gemini/Vertex synthesis by keeping raw evidence separate from retrieval context
and by attaching valid-time and transaction-time metadata to each chunk. The
provider is not used to invent missing timestamps; uncertain or missing temporal
metadata should stay uncertain.

The default local embedding model is `BAAI/bge-small-en-v1.5` with 384
dimensions for laptop-friendly runs. If you change the embedding model or
dimension, purge and reingest because old vectors are incompatible with the new
dimension.

## Vertex AI Gemini

Vertex mode uses Gemini through Google Cloud Vertex AI, not the Gemini Developer API key flow. Local development should use Application Default Credentials or a service account configured outside the repository. Do not commit credentials, key files, or token output.

Install the optional dependency:

```bash
pip install -r requirements-provider.txt
```

Authenticate and select the project:

```bash
gcloud auth application-default login
gcloud config set project ginkgo-2026
gcloud services enable aiplatform.googleapis.com
```

Set provider environment variables:

```bash
export CHRONORAG_LIGHT=0
export CHRONORAG_PROVIDER=vertex
export GOOGLE_CLOUD_PROJECT=ginkgo-2026
export GOOGLE_CLOUD_LOCATION=us-central1
export VERTEX_MODEL_ID=gemini-2.5-flash
```

Optional experimental local embedding fp16 mode:

```bash
export CHRONORAG_EMBED_FP16=1
```

When enabled, ChronoRAG attempts to call `.half()` on the local
SentenceTransformer embedding model after loading it. If that fails, it logs a
warning and continues in normal precision. This flag is not required for Vertex
provider mode and should be treated as a local laptop tuning option.

## Smoke Test

Run retrieval data setup first:

```bash
python -m cli.chronorag_cli purge
python -m cli.chronorag_cli ingest data/sample/smoke/*
```

Then run the provider smoke script:

```bash
python -m benchmarks.run_provider_smoke
```

The script prints five small QA examples with the question, retrieved evidence summary, provider answer, fallback/debug fields, and latency. The larger `data/sample/docs/aihistory*.txt` files are optional full-demo inputs, not the default smoke path.

## Failure Behavior

Provider mode fails closed. If the Vertex SDK is missing, credentials are not available, project/model settings are wrong, quota is exhausted, or the API call fails, ChronoRAG returns the deterministic evidence digest with a `Provider debug:` note. It does not crash and it does not allow the model to answer without retrieved evidence.

## Cost And Quota

Provider mode calls Vertex AI and may incur cost or quota usage. Keep the smoke test small, avoid putting provider mode in CI, and prefer light mode for repeatable tests.

Retrieval ablation numbers remain controlled sanity results, not an external
benchmark or broad performance claim.

The Layer 1B answer-validation benchmark has a full Vertex mode:

```bash
python benchmarks/run_temporal_answer_validation_v2.py --mode vertex --top-k 5
```

Vertex mode is explicit and does not silently fall back to the light harness. It
uses BGE/vector retrieval by default; pass `--skip-vector` only when intentionally
downgrading retrieval for a constrained local machine.
