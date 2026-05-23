# ChronoRAG Operations Guide

## 1. Models & Execution Modes

- **Embeddings**: `BAAI/bge-base-en-v1.5` (CPU/GPU friendly; swaps via `config/models.yaml`).
- **Reranker**: `BAAI/bge-reranker-v2-m3` with fallback `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **LLM Answerer**: local Hugging Face `Qwen/Qwen1.5-0.5B-Chat` (deterministic, GPU-friendly).
  - For higher-quality generations, point the OpenAI-compatible slot at a stronger hosted model by setting `LLM_ENDPOINT` and `LLM_API_KEY`.
- **Mode selection**:
  - `HARD`: strict time window adherence, fewer candidates, most conservative.
  - `INTELLIGENT`: decays outside-window evidence to surface broader context.
  - `LIGHT`: set `CHRONORAG_LIGHT=1` to use stubbed models (unit tests, quick smoke checks).
  - `FULL`: unset `CHRONORAG_LIGHT` (or set to `0`) to download/run full models; enable for production-quality answers.
- **Quantization**: optional `load_in_4bit: true` in `config/models.yaml` lowers VRAM usage (requires `bitsandbytes`).

## 2. Kaggle / Colab Workflow

```python
!git clone https://github.com/SSKG2602/chronorag.git
%cd chronorag

!pip install -r requirements.txt

import sys, pathlib, os
repo = pathlib.Path(".").resolve()
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))
os.environ["PYTHONPATH"] = str(repo)
!touch storage/__init__.py storage/pvdb/__init__.py

%env CHRONORAG_LIGHT=1  # set to 0 for full model-backed mode

!bash install.sh

!python -m cli.chronorag_cli ingest \
  data/sample/docs/aihistory1.txt \
  data/sample/docs/aihistory2.txt \
  data/sample/docs/aihistory3.txt

!./checkllm.sh           # sanity-check that the LLM backend loads
!./query.sh              # run a sample scripted query

!python -m cli.chronorag_cli answer \
  --query "Europe GDP per capita in 1870 (1990 intl$)" \
  --mode INTELLIGENT \
  --axis valid

!python -m cli.chronorag_cli purge   # remove ingested artifacts when finished
```

Additional tips:
- Export `HF_TOKEN` if your selected Hugging Face model requires authentication.
- Install `bitsandbytes` (`pip install bitsandbytes`) when using GPU-based 4-bit loading.
- Persist `models_bin` to `/kaggle/working` or Google Drive if you need reuse across sessions.
- CLI/API responses now return minified JSON objects with `range` + 2 `bullets`
  when the LLM succeeds. Parse the JSON payload directly or inspect
  `controller_stats` to detect fallback digests.

## 3. macOS Workflow

```bash
git clone https://github.com/SSKG2602/chronorag.git
cd chronorag

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export HF_TOKEN=hf_xxx          # optional: for gated Hugging Face models
export CHRONORAG_LIGHT=1        # use 0 for full model-backed execution

bash install.sh                 # installs extra tooling (optional)

# Ingest sample docs
python -m cli.chronorag_cli ingest \
  data/sample/docs/aihistory1.txt \
  data/sample/docs/aihistory2.txt \
  data/sample/docs/aihistory3.txt

# Launch API server (new shell)
source .venv/bin/activate
python -m app.uvicorn_runner

# Ask questions via CLI
python -m cli.chronorag_cli answer \
  --query "Europe GDP per capita in 1870 (1990 intl$)" \
  --mode HARD --axis valid
# The answer field will be JSON when validated; evidence digests remain plain text.

# Purge ingested content when done
python -m cli.chronorag_cli purge
```

For Apple Silicon GPUs, install `torch` nightly wheels with Metal support if you
need hardware acceleration.

## 4. WSL Workflow

```bash
# Inside WSL (Ubuntu)
sudo apt update && sudo apt install -y build-essential python3.11 python3.11-venv git

git clone https://github.com/SSKG2602/chronorag.git
cd chronorag

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export HF_TOKEN=hf_xxx
export CHRONORAG_LIGHT=1

bash install.sh

# Optional GPU setup (if WSL has CUDA passthrough)
pip install bitsandbytes

python -m cli.chronorag_cli ingest \
  data/sample/docs/aihistory1.txt \
  data/sample/docs/aihistory2.txt \
  data/sample/docs/aihistory3.txt

python -m app.uvicorn_runner &

python -m cli.chronorag_cli answer \
  --query "Europe GDP per capita in 1870 (1990 intl$)" \
  --mode INTELLIGENT --axis valid
# Structured JSON answers can be decoded with `python -m json.tool` if desired.

python -m cli.chronorag_cli purge
```

Ensure the Windows host shares the Hugging Face cache directory if you want to
avoid re-downloading models between sessions. For GPU usage, install the NVIDIA
driver with WSL support and confirm `nvidia-smi` works inside the WSL shell.
