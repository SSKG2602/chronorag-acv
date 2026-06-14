# Paper Result Narrative

Layer 2A is the primary retrieval-quality benchmark. BM25 and Date-filter RAG
achieve higher broad Hit@5 than ChronoRAG Full, but ChronoRAG Full is strongest
on Hit@1, MRR@5, Forbidden Absent@5, and Category Primary Pass. This supports
temporal-validity retrieval, not generic retrieval superiority.

The score-only ablation shows why broad retrieval score optimization is not the
same objective: Score-only reaches 0.9850 Hit@5 while falling to 0.6500
Forbidden Absent@5 and 0.5625 Category Primary Pass.

QA50 LLM post-filtering baselines show that downstream prompting does not
replace retrieval-layer grounding. Standard retrieval plus the same LLM prompt
reaches 0.3200-0.4000 strict combined pass, while ChronoRAG reaches 0.7000 in
the prior post-injection answer setting.
