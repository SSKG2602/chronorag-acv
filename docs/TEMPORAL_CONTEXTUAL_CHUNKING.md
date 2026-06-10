# Temporal Contextual Chunking

## Abstract

Temporal Contextual Chunking is ChronoRAG's chunking strategy, inspired by
contextual retrieval but extended for valid-time retrieval, transaction-time
tracking, temporal fusion, ChronoSanity, and attribution.

The method keeps raw evidence unchanged while adding an indexing surface and
explicit temporal metadata. The goal is to make each chunk easier to retrieve
without letting generated or inherited context overwrite the source text.

This is a ChronoRAG architecture definition. It is not a broad benchmark claim
and should not be described as Anthropic's method.

## Why Normal Chunking Fails For Temporal RAG

Normal chunking splits a document into small text fragments. Those fragments are
then embedded and retrieved independently. This works poorly when the answer
depends on time because a chunk can lose:

- the document title or source family
- the section or table heading
- the unit attached to a numeric claim
- the entity or region being measured
- the valid-time range of the claim
- the difference between publication time and claim-valid time

For temporal RAG, a passage can be topically relevant but temporally wrong. A
chunk about GDP per capita may mention Western Europe and 1990 international
dollars, but if it lacks the year or inherits a broad document window, it is weak
evidence for an exact-year query.

## Method Overview

Temporal Contextual Chunking creates two text surfaces and one structured
metadata envelope for each chunk:

- `raw_text`: unchanged source evidence.
- `retrieval_text`: short global context plus `raw_text`, used for BM25/vector
  indexing.
- `global_context`: document and section metadata that helps retrieval.
- temporal metadata: valid-time and transaction-time fields used by temporal
  filtering, fusion, ChronoSanity, and attribution.

The core rule is simple: generated or global context must not overwrite raw
evidence. Raw evidence remains the source for attribution and grounding.
Context is used only for retrieval and metadata reasoning.

## Raw Text vs Retrieval Text

`raw_text` is the original evidence text. It should be preserved exactly enough
for attribution, quote display, and answer grounding.

`retrieval_text` is an indexing surface. It may prepend a compact context prefix:

```text
Document: Maddison/OECD world economy dataset.
Section: Western Europe GDP per capita.
Unit: 1990 international dollars.
Temporal scope: 1870.
Original chunk: GDP per capita in Western Europe was 1,960 in 1870.
```

BM25 and vector search should use `retrieval_text`. Attribution cards and answer
grounding should cite `raw_text`.

When a precise temporal expression is detected, `retrieval_text` may also carry
a compact normalized hint while `raw_text` remains unchanged, for example:

```text
Temporal hint: [valid_time=1962-08-15 precision=day]. Original chunk: United States 10-year Treasury yield was 3.98 percent on 1962-08-15.
```

## Global Context

`global_context` stores structured metadata that can be inherited from the
document, section, table, row, or extraction pipeline:

```json
{
  "document_title": "The World Economy",
  "source_family": "Maddison/OECD",
  "section": "Western Europe GDP per capita",
  "unit": "1990 international dollars",
  "entity": "Western Europe",
  "region": "Europe"
}
```

Global context should be short and conservative. It should improve candidate
recall, not become a second source of truth.

## Temporal Metadata Schema

Each chunk should carry temporal fields alongside provenance:

```json
{
  "valid_from": "1870-01-01",
  "valid_to": "1870-12-31",
  "tx_start": "2006-01-01",
  "tx_end": null,
  "granularity": "year",
  "temporal_source": "chunk_explicit",
  "temporal_confidence": 0.95,
  "temporal_ambiguity": false
}
```

Field meanings:

- `valid_from`: when the claim starts being valid in the real world.
- `valid_to`: when the claim stops being valid in the real world.
- `tx_start`: when the system or source observed/published/stored the claim.
- `tx_end`: when that transaction-time record is superseded, if known.
- `granularity`: `day`, `month`, `year`, `range`, `document`, or `unknown`.
- `temporal_source`: where the time signal came from.
- `temporal_confidence`: confidence in the valid-time assignment.
- `temporal_ambiguity`: whether the time signal may apply to multiple facts or
  only broad context.

Layer 1 mostly exercises year/window discrimination. A Layer 2 diagnostic pilot
exposed a dense daily exact-date retrieval failure: reducing time to year
granularity caused wrong same-year FRED rows to outrank the exact requested
date. Adapter-side precision fixed the 5-case ChronoRAG pilot from 2/5 to 5/5,
and the reusable parser now lives in `core/ingestion/temporal_precision.py` so
core TCC preserves multi-granularity metadata too.

The precision parser supports year, month, day, hour, minute, second, ranges,
quarters, dayparts, and fuzzy phrases while still separating valid time from
transaction/publication/filing/release time. TCC now preserves
`normalized_start`, `normalized_end`, `precision`, `temporal_role`,
`original_temporal_expression`, `ambiguous_parse`, `temporal_constraints`, and
`interval_confidence` alongside the older valid-time and transaction-time
fields.

## Temporal Inference Hierarchy

1. `chunk_explicit`
   - A timestamp/year/date appears directly in the chunk text.
   - Strongest claim-valid signal.
   - High confidence.

2. `row_metadata`
   - A structured record contains year/date fields.
   - Strong signal, especially for table and JSONL data.

3. `section_range`
   - A section, table header, or document context gives a range such as
     `1870-1913`.
   - Broad valid-time range.
   - Medium confidence.

4. `document_tx_time`
   - Publication, import, or revision time.
   - Transaction time only.
   - Must not be treated as valid time unless explicitly supported.

5. `unknown`
   - No reliable timestamp.
   - `valid_from` and `valid_to` remain null.
   - The chunk may still be useful for non-temporal queries.
   - Penalize it for temporal queries.

## Risk Analysis

One timestamp exists:

- Use it only if it clearly applies to the claim.
- If it is only a publication date, store it as transaction time.

Multiple timestamps exist:

- If different years support different facts, split into smaller temporal claim
  chunks.
- If splitting is unsafe, set `temporal_ambiguity=true` and lower confidence.

Broad range exists:

- Preserve the broad range.
- Do not convert a range into an exact year.
- Exact-year chunks should outrank broad-range chunks for exact-year queries.

No timestamp exists:

- Do not invent time.
- Set `temporal_source="unknown"`, `temporal_confidence=0.0`, and
  `temporal_ambiguity=true`.

Global context suggests time:

- Treat it as context-inferred only.
- Give it lower confidence than explicit text or row metadata.
- It must never override explicit timestamp or row metadata.

Publication year exists:

- Store it as transaction time.
- Do not confuse publication year with claim-valid year.

Broad windows such as `1000-01-01` to `2006-12-31`:

- Treat them as weak for exact temporal retrieval.
- Penalize them when exact-year evidence exists.

## Examples

### Example 1: Explicit Year Claim

Raw chunk:

```text
GDP per capita in Western Europe was 1,960 in 1870.
```

Retrieval text:

```text
Document: Maddison/OECD world economy dataset. Section: Western Europe GDP per capita. Unit: 1990 international dollars. Temporal scope: 1870. Original chunk: GDP per capita in Western Europe was 1,960 in 1870.
```

Temporal metadata:

```yaml
valid_from: 1870-01-01
valid_to: 1870-12-31
granularity: year
temporal_source: chunk_explicit
temporal_confidence: 0.95
temporal_ambiguity: false
```

### Example 2: Explicit Range

Raw chunk:

```text
Between 1870 and 1913, GDP per capita increased.
```

Temporal metadata:

```yaml
valid_from: 1870-01-01
valid_to: 1913-12-31
granularity: range
temporal_source: chunk_explicit_range
temporal_confidence: 0.70
temporal_ambiguity: false
```

### Example 3: Publication Time Only

Raw chunk:

```text
This OECD publication was released in 2006.
```

Temporal metadata:

```yaml
valid_from: null
valid_to: null
tx_start: 2006-01-01
tx_end: null
granularity: document
temporal_source: document_tx_time
temporal_confidence: 0.30
temporal_ambiguity: true
```

### Example 4: No Time Signal

Raw chunk:

```text
Historical GDP estimates use purchasing power parity adjustments.
```

Temporal metadata:

```yaml
valid_from: null
valid_to: null
temporal_source: unknown
temporal_confidence: 0.0
temporal_ambiguity: true
```

## Retrieval Scoring Implications

Temporal Contextual Chunking is intended to improve retrieval before temporal
filtering:

- BM25 can match document title, section, unit, entity, and temporal scope.
- Vector retrieval embeds the chunk with compact source context.
- Temporal filtering can distinguish exact-year, range, transaction-time-only,
  and unknown-time chunks.
- Temporal fusion can reward exact valid-time evidence over broad windows.
- Unknown or ambiguous valid-time chunks can remain searchable but receive a
  penalty for time-sensitive queries.

Exact-year chunks should outrank broad-range chunks for exact-year questions
when source authority and relevance are comparable. Broad windows remain useful
as background evidence but should not dominate precise temporal answers.

## Interaction With ChronoSanity

ChronoSanity depends on trustworthy time windows. Temporal Contextual Chunking
feeds it better metadata:

- explicit valid-time chunks reduce false conflicts from broad document windows
- ambiguous chunks can be treated as lower-confidence evidence
- overlapping claims with incompatible values can be detected at the claim level
- transaction-time-only chunks are not mistaken for claim-valid evidence

If a chunk carries broad or ambiguous temporal metadata, ChronoSanity should use
that uncertainty when deciding whether to warn, degrade, or produce
evidence-only output.

## Interaction With Attribution Cards

Attribution cards should cite `raw_text`, source URI, valid window, transaction
window, confidence, and ambiguity. They should not display generated context as
if it were quoted evidence.

Recommended attribution behavior:

- quote from `raw_text`
- show `valid_from` and `valid_to`
- show `tx_start` and `tx_end` when relevant
- include `temporal_source`
- expose ambiguity or broad-window warnings

## Limitations

- Temporal Contextual Chunking does not make weak source data strong.
- It depends on extractor quality for titles, sections, units, and rows.
- Multiple timestamps in dense table text may require smaller claim chunks.
- Context prefixes can improve retrieval but may also bias retrieval if too long
  or too speculative.
- Ablation results should be read as controlled evidence, not broad proof of
  measurable improvement.
- It is not an answer-quality evaluation and not a broad benchmark claim.

## Implementation Checklist

1. Extend chunk records with `raw_text`, `retrieval_text`, `global_context`, and
   temporal confidence fields.
2. Build a deterministic context-prefix generator from source metadata.
3. Use `retrieval_text` for BM25 and vector indexing.
4. Preserve `raw_text` for answer grounding and attribution cards.
5. Add temporal inference rules for `chunk_explicit`, `row_metadata`,
   `section_range`, `document_tx_time`, and `unknown`.
6. Split multi-year/multi-fact chunks when the source text supports safe claim
   separation.
7. Penalize broad, ambiguous, and unknown windows in temporal fusion.
8. Add tests for publication-time versus valid-time handling.
9. Add ablations comparing normal chunking and Temporal Contextual Chunking.

## Reproducibility Notes

Changing chunking or temporal precision rules changes retrieval behavior and
invalidates old persisted vectors. Purge and reingest after changing those
settings:

```bash
python -m cli.chronorag_cli purge
python -m cli.chronorag_cli ingest data/sample/smoke/*
```

Benchmarks should report the chunking mode, embedding model, embedding
dimension, candidate count, and whether provider mode was used. Provider-backed
answer synthesis should be evaluated separately from retrieval quality.

Temporal Eval v2 includes cases for exact-year evidence, broad ranges, unknown
timestamps, publication-time-only evidence, and conflicting evidence. It is
intended to test whether Temporal Contextual Chunking changes temporal retrieval
behavior before answer synthesis. It is not an external benchmark and not a
broad performance claim.
