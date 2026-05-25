# Temporal Answer Validation v2 Dry-Run Prompts

```bash
benchmarks/run_temporal_answer_validation_v2.py --mode light --dry-run-prompts --limit 2
```

## av2_q01_western_europe_1870_exact

Evidence IDs: e2:oecd_pdf:western_europe_exact_1870, e2:maddison:regional:gdp_pc:western_europe:1870, e2:maddison:regional:gdp_pc:western_europe:1950, e2:oecd_pdf:western_europe_exact_1913, e2:synthetic:conflict:western_europe:gdp_pc:1870

```text
You are ChronoRAG's grounded temporal answer synthesizer.
Use only the TCC-enriched evidence cards.
Do not use outside knowledge.
Do not invent values.
Do not treat transaction_time as valid_time.
Prefer exact valid-time evidence over broad-window evidence.
Use broad-window evidence only as context unless no exact evidence exists.
If exact valid-time evidence is missing, answer partial/insufficient or refuse exact answer.
If evidence cards disagree for same entity + metric + valid time, return conflict_warning.
If the question has ambiguous temporal phrase, return clarify.
Always cite evidence IDs.
Return one compact strict JSON object only.
Do not wrap the JSON in markdown and do not include literal newlines inside string values.

Question: What was Western Europe GDP per capita in 1870 using exact valid-year evidence only?
Expected behavior label for evaluation: answer

TCC-enriched evidence cards:
Evidence ID: e2:oecd_pdf:western_europe_exact_1870
Source family: oecd_world_economy_pdf
Source file: data/raw/temporal_eval_v2/oecd/oecd3.pdf
Entity: Western Europe
Metric: GDP per capita
Value: None
Unit: 1990 international dollars
Valid time: 1870-01-01 to 1870-12-31
Transaction time: 2006
Temporal type: valid_time_exact
Source kind: pdf_derived_passage
Raw evidence: OECD table-derived evidence reports Western Europe GDP per capita as 1,960 in 1870, measured in 1990 international dollars.
Retrieval context: Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Derived short passage. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1870-1870. Original chunk: OECD table-derived evidence reports Western Europe GDP per capita as 1,960 in 1870, measured in 1990 international dollars.
TCC context: evidence_id=e2:oecd_pdf:western_europe_exact_1870; source_family=oecd_world_economy_pdf; valid_time=1870-01-01 to 1870-12-31; transaction_time=2006; temporal_type=valid_time_exact; source_kind=pdf_derived_passage; raw_evidence=OECD table-derived evidence reports Western Europe GDP per capita as 1,960 in 1870, measured in 1990 international dollars.; retrieval_context=Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Derived short passage. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1870-1870. Original chunk: OECD table-derived evidence reports Western Europe GDP per capita as 1,960 in 1870, measured in 1990 international dollars.

---

Evidence ID: e2:maddison:regional:gdp_pc:western_europe:1870
Source family: maddison_project_2023
Source file: data/raw/temporal_eval_v2/maddison/mpd2023_web.xlsx
Entity: Western Europe
Metric: GDP per capita
Value: 3287.760602333366
Unit: 2011 international dollars
Valid time: 1870-01-01 to 1870-12-31
Transaction time: None
Temporal type: valid_time_exact
Source kind: structured_excel
Raw evidence: Western Europe GDP per capita was 3,288 in 1870, measured in 2011 international dollars in Maddison Project 2023 regional data.
Retrieval context: Document: Temporal Eval v2 maddison_project_2023. Section: Regional data GDPpc. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1870. Original chunk: Western Europe GDP per capita was 3,288 in 1870, measured in 2011 international dollars in Maddison Project 2023 regional data.
TCC context: evidence_id=e2:maddison:regional:gdp_pc:western_europe:1870; source_family=maddison_project_2023; valid_time=1870-01-01 to 1870-12-31; transaction_time=None; temporal_type=valid_time_exact; source_kind=structured_excel; raw_evidence=Western Europe GDP per capita was 3,288 in 1870, measured in 2011 international dollars in Maddison Project 2023 regional data.; retrieval_context=Document: Temporal Eval v2 maddison_project_2023. Section: Regional data GDPpc. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1870. Original chunk: Western Europe GDP per capita was 3,288 in 1870, measured in 2011 international dollars in Maddison Project 2023 regional data.

---

Evidence ID: e2:maddison:regional:gdp_pc:western_europe:1950
Source family: maddison_project_2023
Source file: data/raw/temporal_eval_v2/maddison/mpd2023_web.xlsx
Entity: Western Europe
Metric: GDP per capita
Value: 7239.914295569185
Unit: 2011 international dollars
Valid time: 1950-01-01 to 1950-12-31
Transaction time: None
Temporal type: valid_time_exact
Source kind: structured_excel
Raw evidence: Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.
Retrieval context: Document: Temporal Eval v2 maddison_project_2023. Section: Regional data GDPpc. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1950. Original chunk: Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.
TCC context: evidence_id=e2:maddison:regional:gdp_pc:western_europe:1950; source_family=maddison_project_2023; valid_time=1950-01-01 to 1950-12-31; transaction_time=None; temporal_type=valid_time_exact; source_kind=structured_excel; raw_evidence=Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.; retrieval_context=Document: Temporal Eval v2 maddison_project_2023. Section: Regional data GDPpc. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1950. Original chunk: Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.

---

Evidence ID: e2:oecd_pdf:western_europe_exact_1913
Source family: oecd_world_economy_pdf
Source file: data/raw/temporal_eval_v2/oecd/oecd3.pdf
Entity: Western Europe
Metric: GDP per capita
Value: None
Unit: 1990 international dollars
Valid time: 1913-01-01 to 1913-12-31
Transaction time: 2006
Temporal type: valid_time_exact
Source kind: pdf_derived_passage
Raw evidence: OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.
Retrieval context: Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Derived short passage. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1913-1913. Original chunk: OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.
TCC context: evidence_id=e2:oecd_pdf:western_europe_exact_1913; source_family=oecd_world_economy_pdf; valid_time=1913-01-01 to 1913-12-31; transaction_time=2006; temporal_type=valid_time_exact; source_kind=pdf_derived_passage; raw_evidence=OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.; retrieval_context=Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Derived short passage. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1913-1913. Original chunk: OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.

---

Evidence ID: e2:synthetic:conflict:western_europe:gdp_pc:1870
Source family: synthetic_temporal_traps
Source file: data/sample/temporal_eval_v2/synthetic_traps.jsonl
Entity: Western Europe
Metric: GDP per capita
Value: 1800.0
Unit: 2011 international dollars
Valid time: 1870-01-01 to 1870-12-31
Transaction time: None
Temporal type: conflict_claim
Source kind: synthetic_trap
Raw evidence: Synthetic conflict trap reports Western Europe GDP per capita as 1,800 in 1870, conflicting with source-backed records.
Retrieval context: Document: Temporal Eval v2 synthetic_temporal_traps. Section: GDP per capita. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1870. Original chunk: Synthetic conflict trap reports Western Europe GDP per capita as 1,800 in 1870, conflicting with source-backed records.
TCC context: evidence_id=e2:synthetic:conflict:western_europe:gdp_pc:1870; source_family=synthetic_temporal_traps; valid_time=1870-01-01 to 1870-12-31; transaction_time=None; temporal_type=conflict_claim; source_kind=synthetic_trap; raw_evidence=Synthetic conflict trap reports Western Europe GDP per capita as 1,800 in 1870, conflicting with source-backed records.; retrieval_context=Document: Temporal Eval v2 synthetic_temporal_traps. Section: GDP per capita. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1870. Original chunk: Synthetic conflict trap reports Western Europe GDP per capita as 1,800 in 1870, conflicting with source-backed records.

Required JSON output schema:
{
  "answer": "...",
  "behavior": "answer | compare | prefer_exact | partial | refuse | conflict_warning | clarify",
  "cited_evidence_ids": [
    "..."
  ],
  "valid_time_used": [
    "..."
  ],
  "transaction_time_used_as_valid_time": false,
  "conflict_warning": false,
  "partial_or_refusal": false,
  "clarification_requested": false
}
```

## av2_q02_western_europe_1913_window

Evidence IDs: e2:oecd_pdf:western_europe_exact_1913, e2:synthetic:conflict:western_europe:gdp_pc:1913, e2:synthetic:same_year_wrong_entity_1913, e2:oecd_pdf:table_note:western_europe:1913, e2:maddison:regional:gdp_pc:western_europe:1950

```text
You are ChronoRAG's grounded temporal answer synthesizer.
Use only the TCC-enriched evidence cards.
Do not use outside knowledge.
Do not invent values.
Do not treat transaction_time as valid_time.
Prefer exact valid-time evidence over broad-window evidence.
Use broad-window evidence only as context unless no exact evidence exists.
If exact valid-time evidence is missing, answer partial/insufficient or refuse exact answer.
If evidence cards disagree for same entity + metric + valid time, return conflict_warning.
If the question has ambiguous temporal phrase, return clarify.
Always cite evidence IDs.
Return one compact strict JSON object only.
Do not wrap the JSON in markdown and do not include literal newlines inside string values.

Question: What was Western Europe GDP per capita in 1913, and which evidence window supports it?
Expected behavior label for evaluation: answer

TCC-enriched evidence cards:
Evidence ID: e2:oecd_pdf:western_europe_exact_1913
Source family: oecd_world_economy_pdf
Source file: data/raw/temporal_eval_v2/oecd/oecd3.pdf
Entity: Western Europe
Metric: GDP per capita
Value: None
Unit: 1990 international dollars
Valid time: 1913-01-01 to 1913-12-31
Transaction time: 2006
Temporal type: valid_time_exact
Source kind: pdf_derived_passage
Raw evidence: OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.
Retrieval context: Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Derived short passage. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1913-1913. Original chunk: OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.
TCC context: evidence_id=e2:oecd_pdf:western_europe_exact_1913; source_family=oecd_world_economy_pdf; valid_time=1913-01-01 to 1913-12-31; transaction_time=2006; temporal_type=valid_time_exact; source_kind=pdf_derived_passage; raw_evidence=OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.; retrieval_context=Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Derived short passage. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1913-1913. Original chunk: OECD table-derived evidence reports Western Europe GDP per capita as 3,473 in 1913, measured in 1990 international dollars.

---

Evidence ID: e2:synthetic:conflict:western_europe:gdp_pc:1913
Source family: synthetic_temporal_traps
Source file: data/sample/temporal_eval_v2/synthetic_traps.jsonl
Entity: Western Europe
Metric: GDP per capita
Value: 3200.0
Unit: 2011 international dollars
Valid time: 1913-01-01 to 1913-12-31
Transaction time: None
Temporal type: conflict_claim
Source kind: synthetic_trap
Raw evidence: Synthetic conflict trap reports Western Europe GDP per capita as 3,200 in 1913, conflicting with source-backed records.
Retrieval context: Document: Temporal Eval v2 synthetic_temporal_traps. Section: GDP per capita. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1913. Original chunk: Synthetic conflict trap reports Western Europe GDP per capita as 3,200 in 1913, conflicting with source-backed records.
TCC context: evidence_id=e2:synthetic:conflict:western_europe:gdp_pc:1913; source_family=synthetic_temporal_traps; valid_time=1913-01-01 to 1913-12-31; transaction_time=None; temporal_type=conflict_claim; source_kind=synthetic_trap; raw_evidence=Synthetic conflict trap reports Western Europe GDP per capita as 3,200 in 1913, conflicting with source-backed records.; retrieval_context=Document: Temporal Eval v2 synthetic_temporal_traps. Section: GDP per capita. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1913. Original chunk: Synthetic conflict trap reports Western Europe GDP per capita as 3,200 in 1913, conflicting with source-backed records.

---

Evidence ID: e2:synthetic:same_year_wrong_entity_1913
Source family: synthetic_temporal_traps
Source file: data/sample/temporal_eval_v2/synthetic_traps.jsonl
Entity: Europe
Metric: GDP per capita
Value: None
Unit: 2011 international dollars
Valid time: 1913-01-01 to 1913-12-31
Transaction time: None
Temporal type: valid_time_exact
Source kind: synthetic_trap
Raw evidence: Wrong-entity trap gives Europe GDP per capita context in 1913 rather than Western Europe.
Retrieval context: Document: Temporal Eval v2 synthetic_temporal_traps. Section: GDP per capita. Entity: Europe. Unit: 2011 international dollars. Temporal scope: 1913. Original chunk: Wrong-entity trap gives Europe GDP per capita context in 1913 rather than Western Europe.
TCC context: evidence_id=e2:synthetic:same_year_wrong_entity_1913; source_family=synthetic_temporal_traps; valid_time=1913-01-01 to 1913-12-31; transaction_time=None; temporal_type=valid_time_exact; source_kind=synthetic_trap; raw_evidence=Wrong-entity trap gives Europe GDP per capita context in 1913 rather than Western Europe.; retrieval_context=Document: Temporal Eval v2 synthetic_temporal_traps. Section: GDP per capita. Entity: Europe. Unit: 2011 international dollars. Temporal scope: 1913. Original chunk: Wrong-entity trap gives Europe GDP per capita context in 1913 rather than Western Europe.

---

Evidence ID: e2:oecd_pdf:table_note:western_europe:1913
Source family: oecd_world_economy_pdf
Source file: data/raw/temporal_eval_v2/oecd/oecd3.pdf
Entity: Western Europe
Metric: GDP per capita
Value: None
Unit: 1990 international dollars
Valid time: 1913-01-01 to 1913-12-31
Transaction time: 2006
Temporal type: valid_time_exact
Source kind: pdf_derived_passage
Raw evidence: OECD table-derived note references Western Europe benchmark-year GDP per capita evidence for 1913.
Retrieval context: Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Benchmark year table note. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1913. Original chunk: OECD table-derived note references Western Europe benchmark-year GDP per capita evidence for 1913.
TCC context: evidence_id=e2:oecd_pdf:table_note:western_europe:1913; source_family=oecd_world_economy_pdf; valid_time=1913-01-01 to 1913-12-31; transaction_time=2006; temporal_type=valid_time_exact; source_kind=pdf_derived_passage; raw_evidence=OECD table-derived note references Western Europe benchmark-year GDP per capita evidence for 1913.; retrieval_context=Document: Temporal Eval v2 oecd_world_economy_pdf. Section: Benchmark year table note. Entity: Western Europe. Unit: 1990 international dollars. Temporal scope: 1913. Original chunk: OECD table-derived note references Western Europe benchmark-year GDP per capita evidence for 1913.

---

Evidence ID: e2:maddison:regional:gdp_pc:western_europe:1950
Source family: maddison_project_2023
Source file: data/raw/temporal_eval_v2/maddison/mpd2023_web.xlsx
Entity: Western Europe
Metric: GDP per capita
Value: 7239.914295569185
Unit: 2011 international dollars
Valid time: 1950-01-01 to 1950-12-31
Transaction time: None
Temporal type: valid_time_exact
Source kind: structured_excel
Raw evidence: Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.
Retrieval context: Document: Temporal Eval v2 maddison_project_2023. Section: Regional data GDPpc. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1950. Original chunk: Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.
TCC context: evidence_id=e2:maddison:regional:gdp_pc:western_europe:1950; source_family=maddison_project_2023; valid_time=1950-01-01 to 1950-12-31; transaction_time=None; temporal_type=valid_time_exact; source_kind=structured_excel; raw_evidence=Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.; retrieval_context=Document: Temporal Eval v2 maddison_project_2023. Section: Regional data GDPpc. Entity: Western Europe. Unit: 2011 international dollars. Temporal scope: 1950. Original chunk: Western Europe GDP per capita was 7,240 in 1950, measured in 2011 international dollars in Maddison Project 2023 regional data.

Required JSON output schema:
{
  "answer": "...",
  "behavior": "answer | compare | prefer_exact | partial | refuse | conflict_warning | clarify",
  "cited_evidence_ids": [
    "..."
  ],
  "valid_time_used": [
    "..."
  ],
  "transaction_time_used_as_valid_time": false,
  "conflict_warning": false,
  "partial_or_refusal": false,
  "clarification_requested": false
}
```
