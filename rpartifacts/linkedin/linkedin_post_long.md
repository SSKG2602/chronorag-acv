ChronoRAG is a temporal-validity retrieval and grounded answer-validation framework for RAG over messy multi-role evidence corpora.

The problem: standard retrieval can find passages that are semantically close but valid at the wrong time. In temporal QA, a filing date, publication date, release date, or nearby date can look relevant while failing the actual valid-time contract.

What this artifact package adds:

- paper-ready figures and tables
- Layer 2A standard baselines: BM25, Dense-only, Date-filter RAG, Metadata Temporal RAG, ChronoRAG Full
- score-only ablation showing that broad Hit@5 and temporal-validity retrieval are different objectives
- QA50 LLM post-filtering baselines showing that prompting alone does not replace retrieval-layer grounding
- explicit limitations and threats to validity

No SOTA claim. The claim is narrower: temporally valid evidence selection and answer-contract validation matter before evidence reaches generation.

GitHub: https://github.com/SSKG2602/chronorag
