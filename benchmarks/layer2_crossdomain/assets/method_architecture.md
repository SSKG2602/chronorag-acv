# Method Architecture

Layer 2A compares `metadata_temporal_rag` against `chronorag_full`.
Historical experimental paths are outside the active benchmark direction.

```text
Question
  -> ChronoRAG TCC retrieval_text and temporal metadata
  -> temporal precision scoring
  -> monotone temporal fusion
  -> evidence cards
  -> answer synthesis
```

TCC represents evidence with raw text, retrieval text, global context, and
valid-time/transaction-time metadata. Temporal precision scoring and monotone
fusion control the active ChronoRAG retrieval path.

Default serious Layer 2A comparison:

```text
metadata_temporal_rag  vs  chronorag_full
```

`direct_llm_full_context` is still available only for historical small-context
diagnostics. It is not a retrieval baseline and can truncate heavily on the
5,000-row Layer 2A corpus.
