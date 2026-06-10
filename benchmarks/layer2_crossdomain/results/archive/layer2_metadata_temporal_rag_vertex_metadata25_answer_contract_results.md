# Layer 2 Results: metadata_temporal_rag

This is a controlled framework result, not a SOTA or publication-grade claim.

- Mode: `vertex`
- Corpus rows: 5000
- Questions: 25
- Top-k: 5
- Prompt truncation count: 0
- Estimated Vertex calls: 25
- Result suffix: `vertex_metadata25_answer_contract`
- Scored cases: 25
- Provider/infrastructure failures: 0
- Provider errors: 0
- Retry attempts: 1

| Metric | Score |
|---|---:|
| Overall Pass | 0.68 |
| Behavior Correct | 1.00 |
| Evidence Correct | 0.84 |
| Valid-Time Correct | 1.00 |
| Transaction-Time Trap Avoided | 1.00 |
| Conflict Warning Correct | 1.00 |
| Partial/Refusal Correct | 1.00 |
| Clarification Correct | 1.00 |
| Cross-Domain Dependency Correct | 1.00 |

## Failure Analysis

- `l2q:0016:exact_valid_time_retrieval` [completed]: forbidden_facts_absent
- `l2q:0018:exact_valid_time_retrieval` [completed]: forbidden_facts_absent
- `l2q:0019:exact_valid_time_retrieval` [completed]: forbidden_facts_absent
- `l2q:0020:same_entity_wrong_year_trap` [completed]: forbidden_facts_absent
- `l2q:0021:same_entity_wrong_year_trap` [completed]: required_facts_present, forbidden_facts_absent, evidence_correct
- `l2q:0022:same_entity_wrong_year_trap` [completed]: required_facts_present, forbidden_facts_absent, evidence_correct
- `l2q:0023:same_entity_wrong_year_trap` [completed]: required_facts_present, forbidden_facts_absent, evidence_correct
- `l2q:0024:same_entity_wrong_year_trap` [completed]: required_facts_present, forbidden_facts_absent, evidence_correct

## Limitations

- Fixture results only prove that the framework runs.
- Full Layer 2 claims require the future 5000-row / 200-question benchmark.
- No SOTA, production, or publication-grade claim is made here.

| Case | Status | Behavior | Selected Evidence | Cited Evidence | Pass | Failures |
|---|---|---|---|---|---:|---|
| l2q:0000:exact_valid_time_retrieval | completed | answer | l2:github_releases:kubernetes:181360153, l2:github_releases:kubernetes:190042332, l2:github_releases:kubernetes:181442196, l2:github_releases:kubernetes:186532670, l2:github_releases:kubernetes:190042097 | l2:github_releases:kubernetes:181360153 | True |  |
| l2q:0001:exact_valid_time_retrieval | completed | answer | l2:github_releases:pandas:6599258, l2:github_releases:pandas:6287033, l2:github_releases:pandas:6294696, l2:github_releases:pandas:6968275, l2:github_releases:pandas:8290248 | l2:github_releases:pandas:6599258 | True |  |
| l2q:0002:exact_valid_time_retrieval | completed | answer | l2:macro_fred:dgs10:1962-08-15, l2:macro_fred:dgs10:1962-05-15, l2:macro_fred:dgs10:1962-01-18, l2:macro_fred:dgs10:1962-02-09, l2:macro_fred:dgs10:1962-03-07 | l2:macro_fred:dgs10:1962-08-15 | True |  |
| l2q:0003:exact_valid_time_retrieval | completed | answer | l2:macro_fred:dgs10:1974-06-20, l2:macro_fred:dgs10:1974-03-20, l2:macro_fred:dgs10:1974-05-06, l2:macro_fred:dgs10:1974-08-06, l2:macro_fred:dgs10:1974-09-20 | l2:macro_fred:dgs10:1974-06-20 | True |  |
| l2q:0004:exact_valid_time_retrieval | completed | answer | l2:macro_fred:dgs10:1986-05-22, l2:macro_fred:dgs10:1986-08-22, l2:macro_fred:dgs10:1986-01-02, l2:macro_fred:dgs10:1986-01-27, l2:macro_fred:dgs10:1986-02-19 | l2:macro_fred:dgs10:1986-05-22 | True |  |
| l2q:0005:exact_valid_time_retrieval | completed | answer | l2:macro_fred:dgs10:1998-03-11, l2:macro_fred:dgs10:1998-04-03, l2:macro_fred:dgs10:1998-11-23, l2:macro_fred:dgs10:1998-01-23, l2:macro_fred:dgs10:1998-02-17 | l2:macro_fred:dgs10:1998-03-11 | True |  |
| l2q:0006:exact_valid_time_retrieval | completed | answer | l2:macro_fred:dgs10:2010-01-21, l2:macro_fred:dgs10:2010-07-01, l2:macro_fred:dgs10:2010-10-01, l2:macro_fred:dgs10:2010-02-12, l2:macro_fred:dgs10:2010-03-09 | l2:macro_fred:dgs10:2010-01-21 | True |  |
| l2q:0007:exact_valid_time_retrieval | completed | answer | l2:macro_fred:dgs10:2021-11-04, l2:macro_fred:dgs10:2021-04-12, l2:macro_fred:dgs10:2021-05-04, l2:macro_fred:dgs10:2021-08-04, l2:macro_fred:dgs10:2021-11-30 | l2:macro_fred:dgs10:2021-11-04 | True |  |
| l2q:0008:exact_valid_time_retrieval | completed | answer | l2:market_index:djia:2016-06-21, l2:market_index:djia:2016-05-27, l2:market_index:djia:2016-07-14, l2:market_index:djia:2016-08-05, l2:market_index:djia:2016-08-30 | l2:market_index:djia:2016-06-21 | True |  |
| l2q:0009:exact_valid_time_retrieval | completed | answer | l2:market_index:nasdaqcom:1972-12-26, l2:market_index:nasdaqcom:1972-04-12, l2:market_index:nasdaqcom:1972-12-01, l2:market_index:nasdaqcom:1972-01-11, l2:market_index:nasdaqcom:1972-02-02 | l2:market_index:nasdaqcom:1972-12-26 | True |  |
| l2q:0010:exact_valid_time_retrieval | completed | answer | l2:market_index:nasdaqcom:1984-10-24, l2:market_index:nasdaqcom:1984-09-10, l2:market_index:nasdaqcom:1984-10-02, l2:market_index:nasdaqcom:1984-01-19, l2:market_index:nasdaqcom:1984-02-13 | l2:market_index:nasdaqcom:1984-10-24 | True |  |
| l2q:0011:exact_valid_time_retrieval | completed | answer | l2:market_index:nasdaqcom:1996-07-30, l2:market_index:nasdaqcom:1996-07-08, l2:market_index:nasdaqcom:1996-10-30, l2:market_index:nasdaqcom:1996-01-03, l2:market_index:nasdaqcom:1996-01-25 | l2:market_index:nasdaqcom:1996-07-30 | True |  |
| l2q:0012:exact_valid_time_retrieval | completed | answer | l2:market_index:nasdaqcom:2008-06-16, l2:market_index:nasdaqcom:2008-01-03, l2:market_index:nasdaqcom:2008-01-29, l2:market_index:nasdaqcom:2008-02-21, l2:market_index:nasdaqcom:2008-03-14 | l2:market_index:nasdaqcom:2008-06-16 | True |  |
| l2q:0013:exact_valid_time_retrieval | completed | answer | l2:market_index:nasdaqcom:2020-04-06, l2:market_index:nasdaqcom:2020-04-30, l2:market_index:nasdaqcom:2020-06-16, l2:market_index:nasdaqcom:2020-01-03, l2:market_index:nasdaqcom:2020-01-28 | l2:market_index:nasdaqcom:2020-04-06 | True |  |
| l2q:0014:exact_valid_time_retrieval | completed | answer | l2:market_index:sp500:2022-02-22, l2:market_index:sp500:2022-05-02, l2:market_index:sp500:2022-01-04, l2:market_index:sp500:2022-01-27, l2:market_index:sp500:2022-03-16 | l2:market_index:sp500:2022-02-22 | True |  |
| l2q:0015:exact_valid_time_retrieval | completed | answer | l2:sec_submissions:aapl:0001193125-15-354756, l2:sec_submissions:aapl:0001193125-15-273023, l2:sec_submissions:aapl:0001193125-15-259935, l2:sec_submissions:aapl:0001181431-15-007653, l2:sec_submissions:aapl:0001209191-15-073531 | l2:sec_submissions:aapl:0001193125-15-354756 | True |  |
| l2q:0016:exact_valid_time_retrieval | completed | answer | l2:sec_submissions:googl:0000950170-24-080932, l2:sec_submissions:googl:0001209191-24-003063, l2:sec_submissions:googl:0000950170-24-081905, l2:sec_submissions:googl:0000950170-24-084027, l2:sec_submissions:googl:0000950170-24-094779 | l2:sec_submissions:googl:0001209191-24-003063 | False | forbidden_facts_absent |
| l2q:0017:exact_valid_time_retrieval | completed | answer | l2:sec_submissions:msft:0001193125-20-180036, l2:sec_submissions:msft:0001193125-20-128779, l2:sec_submissions:msft:0001193125-20-207517, l2:sec_submissions:msft:0001193125-20-278410, l2:sec_submissions:msft:0001193125-21-198810 | l2:sec_submissions:msft:0001193125-20-180036 | True |  |
| l2q:0018:exact_valid_time_retrieval | completed | answer | l2:sec_submissions:nvda:0001045810-26-000003, l2:sec_submissions:nvda:0001045810-26-000019, l2:sec_submissions:nvda:0001045810-26-000028, l2:sec_submissions:nvda:0001347842-26-000002, l2:sec_submissions:nvda:0001347842-26-000011 | l2:sec_submissions:nvda:0001045810-26-000003 | False | forbidden_facts_absent |
| l2q:0019:exact_valid_time_retrieval | completed | answer | l2:sec_submissions:tsla:0001972928-25-000003, l2:sec_submissions:tsla:0000950170-25-003585, l2:sec_submissions:tsla:0001104659-25-057932, l2:sec_submissions:tsla:0001104659-25-089693, l2:sec_submissions:tsla:0001104659-25-110597 | l2:sec_submissions:tsla:0001972928-25-000003 | False | forbidden_facts_absent |
| l2q:0020:same_entity_wrong_year_trap | completed | answer | l2:macro_fred:cpi:1948-05-01, l2:macro_fred:cpi:1947-01-01, l2:macro_fred:unrate:1948-09-01, l2:macro_fred:cpi:1949-09-01, l2:macro_fred:cpi:1951-01-01 | l2:macro_fred:cpi:1948-05-01 | False | forbidden_facts_absent |
| l2q:0021:same_entity_wrong_year_trap | completed | answer | l2:macro_fred:dgs10:1968-01-12, l2:macro_fred:dgs10:1968-02-05, l2:macro_fred:dgs10:1968-02-29, l2:macro_fred:dgs10:1968-03-22, l2:macro_fred:dgs10:1968-04-17 | l2:macro_fred:dgs10:1968-01-12 | False | required_facts_present, forbidden_facts_absent, evidence_correct |
| l2q:0022:same_entity_wrong_year_trap | completed | answer | l2:macro_fred:dgs10:1979-01-17, l2:macro_fred:dgs10:1979-02-08, l2:macro_fred:dgs10:1979-03-06, l2:macro_fred:dgs10:1979-03-28, l2:macro_fred:dgs10:1979-04-20 | l2:macro_fred:dgs10:1979-01-17 | False | required_facts_present, forbidden_facts_absent, evidence_correct |
| l2q:0023:same_entity_wrong_year_trap | completed | answer | l2:macro_fred:dgs10:1990-01-18, l2:macro_fred:dgs10:1990-02-09, l2:macro_fred:dgs10:1990-03-06, l2:macro_fred:dgs10:1990-03-28, l2:macro_fred:dgs10:1990-04-20 | l2:macro_fred:dgs10:1990-01-18 | False | required_facts_present, forbidden_facts_absent, evidence_correct |
| l2q:0024:same_entity_wrong_year_trap | completed | answer | l2:macro_fred:dgs10:2000-01-19, l2:macro_fred:dgs10:2000-02-10, l2:macro_fred:dgs10:2000-03-06, l2:macro_fred:dgs10:2000-03-28, l2:macro_fred:dgs10:2000-04-19 | l2:macro_fred:dgs10:2000-01-19 | False | required_facts_present, forbidden_facts_absent, evidence_correct |
