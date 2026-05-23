# ChronoRAG Repo Polish Audit

## Verdict

ChronoRAG has a strong research idea and a real multi-layer code scaffold. The public presentation needs tighter claim discipline, a single clean README, demo evidence, screenshots, and benchmark framing.

## Strong Signals

- Clear project identity: temporal RAG, not generic RAG.
- App/service/core/storage separation.
- Ingestion handles structured JSONL and text fallback.
- Retrieval combines lexical, vector, temporal filtering, reranking, and temporal fusion.
- Answer path includes temporal routing, ChronoSanity conflict handling, attribution, and telemetry.
- YAML-driven policy/model configuration.
- Tests directory exists with unit/e2e/fixture organization.
- Apache-2.0 license is appropriate for public open-source positioning.

## Weak Signals

- README reads more like an internal architecture note than a polished public project page.
- No screenshots or demo assets are visible.
- No benchmark table.
- No “what works / what does not work” honesty section.
- No minimal quickstart path at the top.
- `howtorunme.md` contains notebook command typos like spaced shell commands. This weakens trust.
- Makefile is too minimal for a research repo.
- No Dockerfile or deployment story.
- Claims can sound stronger than proof currently shown.

## Priority Fixes

### P0: Public credibility

- Replace README with the polished README in this pack.
- Add Mermaid architecture diagram.
- Add honest limitations section.
- Add demo screenshot placeholders and then commit real screenshots.
- Add one command-tested smoke demo.

### P1: Developer trust

- Fix `howtorunme.md` command typos.
- Expand Makefile:

```makefile
.PHONY: setup run test ingest demo purge

setup:
	pip install -r requirements.txt

run:
	python -m app.uvicorn_runner --host 0.0.0.0 --port 8000

test:
	CHRONORAG_LIGHT=1 pytest -q

ingest:
	python -m cli.chronorag_cli ingest data/sample/docs

demo:
	python -m cli.chronorag_cli answer --query "Europe GDP per capita in 1870 (1990 intl$$)" --mode INTELLIGENT --axis valid

purge:
	python -m cli.chronorag_cli purge
```

### P2: Research trust

- Add a small benchmark CSV/JSONL.
- Add ablation script.
- Add `docs/FUTURE_RESEARCH.md`.
- Add `docs/TECHNICAL_LIMITATIONS.md`.

## Suggested Git Commit Plan

```bash
git checkout -b polish/public-readme

mkdir -p docs assets/demo
cp README.md README.old.md
# Replace README.md with polished version
# Add docs from this pack

git add README.md docs assets
git commit -m "Polish ChronoRAG public README and research docs"
```
