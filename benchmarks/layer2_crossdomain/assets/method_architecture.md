# Method Architecture

Layer 2A now treats `chronorag_gsm` as the ChronoRAG retrieval method under
test. `chronorag_full` remains available as an ablation of TCC plus temporal
precision and monotone temporal fusion without GSM.

```text
Question
  -> Temporal query analyzer
  -> GSM gate
       simple exact valid-time query: existing ChronoRAG path
       hard temporal query: deterministic GSM plan
  -> plan-aware filters, demotions, and slot retrieval
  -> ChronoRAG TCC retrieval_text and temporal metadata
  -> temporal precision scoring
  -> monotone temporal fusion
  -> evidence cards
  -> answer synthesis
```

GSM is not a replacement for TCC. TCC represents evidence; GSM plans retrieval.
GSM is deterministic and does not use an LLM planner. It activates for hard
temporal intent: wrong-year traps, transaction-time vs valid-time traps,
conflict/disagreement, source/domain restriction, metric/form restriction,
cross-domain comparison, missing exact evidence, and ambiguous temporal
language.

TCC solves temporal evidence representation. GSM solves temporal query intent.
Embeddings improve semantic candidate quality. ChronoRAG-GSM combines all
three: temporally contextualized evidence, stronger semantic retrieval, and
deterministic temporal retrieval planning.

Default serious Layer 2A comparison:

```text
metadata_temporal_rag  vs  chronorag_gsm
```

`direct_llm_full_context` is deprecated for 5,000-row Layer 2A because it is not
a retrieval baseline and can truncate heavily. Keep it only for historical
small-context diagnostics.
