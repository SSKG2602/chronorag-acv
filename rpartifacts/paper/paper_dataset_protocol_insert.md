# Paper Dataset Protocol Insert

The current artifact records benchmark labels as fixed JSONL fields. Expected
evidence IDs, forbidden evidence IDs, and category-primary labels are
author-created and treated as fixed before method scoring. Large-scale
independent annotation is not included in this version and is listed as a
limitation. Standard comparisons use the same corpus, same queries, same
top-k=5, same evaluator, and same candidate corpus where applicable. Gold
expected evidence IDs were not included in LLM baseline prompts.
