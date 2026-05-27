from __future__ import annotations

import calendar
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta

from benchmarks.layer2_crossdomain.schemas import CorpusRow, QuestionCase


MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): index for index, name in enumerate(calendar.month_abbr) if name})

TRANSACTION_ROLE_WORDS = {
    "transaction": "transaction_time",
    "transaction-time": "transaction_time",
    "observed": "transaction_time",
    "ingested": "transaction_time",
    "publication": "publication_time",
    "published": "publication_time",
    "filing": "filing_time",
    "filed": "filing_time",
    "release": "release_time",
    "released": "release_time",
}

ISO_DATE_RE = re.compile(r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b")
NUMERIC_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
MONTH_DD_YYYY_RE = re.compile(
    r"\b("
    + "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
    + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE,
)
DD_MONTH_YYYY_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+("
    + "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
    + r")\s+(\d{4})\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?\s*(am|pm)\b|\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b")


@dataclass(frozen=True)
class TemporalConstraint:
    original_text: str
    normalized_start: str
    normalized_end: str
    granularity: str
    precision: float
    confidence: float
    ambiguous_parse: bool
    temporal_role: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def extract_temporal_constraints(text: str) -> list[TemporalConstraint]:
    """Extract deterministic temporal constraints without guessing ambiguous dates."""
    constraints: list[TemporalConstraint] = []
    occupied: list[tuple[int, int]] = []

    for constraint, span in _extract_datetime_constraints(text):
        constraints.append(constraint)
        occupied.append(span)

    for constraint, span in _extract_interval_constraints(text):
        constraints.append(constraint)
        occupied.append(span)

    for constraint, span in _extract_fuzzy_constraints(text):
        constraints.append(constraint)
        occupied.append(span)

    for constraint, span in _extract_quarter_constraints(text):
        constraints.append(constraint)
        occupied.append(span)

    for constraint, span in _extract_month_constraints(text):
        if not _covered(span, occupied):
            constraints.append(constraint)
            occupied.append(span)

    for constraint, span in _extract_date_constraints(text):
        if not _covered(span, occupied):
            constraints.append(constraint)
            occupied.append(span)

    for constraint, span in _extract_daypart_constraints(text):
        if not _covered(span, occupied):
            constraints.append(constraint)
            occupied.append(span)

    for constraint, span in _extract_time_constraints(text):
        if not _covered(span, occupied):
            constraints.append(constraint)
            occupied.append(span)

    for match in YEAR_RE.finditer(text):
        if _covered(match.span(), occupied):
            continue
        year = int(match.group(1))
        constraints.append(
            TemporalConstraint(
                original_text=match.group(0),
                normalized_start=f"{year:04d}-01-01",
                normalized_end=f"{year:04d}-12-31",
                granularity="year",
                precision=0.45,
                confidence=0.85,
                ambiguous_parse=False,
                temporal_role=_infer_role(text, match.start(), match.end()),
            )
        )

    constraints.sort(key=lambda item: (item.precision, item.confidence), reverse=True)
    return constraints


def score_temporal_precision(case: QuestionCase, row: CorpusRow) -> float:
    """Score row time against query constraints at the most specific safe granularity."""
    constraints = extract_temporal_constraints(case.question)
    if not constraints:
        constraints = _constraints_from_expected_valid_time(case)

    asks_transaction = _asks_transaction_role(case.question, constraints)
    if row.temporal_type == "transaction_time_only" and not asks_transaction:
        return 0.03

    row_start, row_end = _row_interval(row, use_transaction=asks_transaction)
    if not row_start:
        if row.temporal_type in {"conflict_claim", "revision"} and case.category in {"conflict_or_revision", "conflict_detection"}:
            return 0.80
        return 0.08 if row.temporal_type != "missing_or_unknown" else 0.02

    best = 0.0
    for constraint in constraints:
        if constraint.ambiguous_parse:
            best = max(best, 0.18)
            continue
        score = _score_constraint_against_interval(constraint, row_start, row_end or row_start, row.temporal_type)
        best = max(best, score)

    if row.temporal_type in {"conflict_claim", "revision"} and case.category in {"conflict_or_revision", "conflict_detection"}:
        best = max(best, 0.80)
    return round(best, 4)


def has_exact_date_query(constraints: list[TemporalConstraint]) -> bool:
    return any(item.granularity == "day" and not item.ambiguous_parse for item in constraints)


def has_exact_timestamp_query(constraints: list[TemporalConstraint]) -> bool:
    return any(item.granularity in {"hour", "minute", "second"} and "T" in item.normalized_start for item in constraints)


def _extract_datetime_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    iso_datetime = re.compile(
        r"\b(\d{4}-\d{2}-\d{2})[T\s]+(\d{1,2}:\d{2}(?::\d{2})?)\b",
        re.IGNORECASE,
    )
    for match in iso_datetime.finditer(text):
        parsed_date = _parse_date_value(match.group(1))
        parsed_time = _parse_time_value(match.group(2))
        if parsed_date and parsed_time:
            results.append((_datetime_constraint(match.group(0), parsed_date, parsed_time, text, match.span()), match.span()))

    month_datetime = re.compile(
        r"((?:"
        + "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
        + r")\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\s+(?:at\s+)?(noon|midnight|\d{1,2}(?::\d{2})?(?::\d{2})?\s*(?:am|pm))\b",
        re.IGNORECASE,
    )
    for match in month_datetime.finditer(text):
        parsed_date = _parse_date_value(match.group(1))
        parsed_time = _parse_time_value(match.group(2))
        if parsed_date and parsed_time:
            results.append((_datetime_constraint(match.group(0), parsed_date, parsed_time, text, match.span()), match.span()))

    day_month_datetime = re.compile(
        r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:"
        + "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
        + r")\s+\d{4})\s+(?:at\s+)?(noon|midnight|\d{1,2}(?::\d{2})?(?::\d{2})?\s*(?:am|pm))\b",
        re.IGNORECASE,
    )
    for match in day_month_datetime.finditer(text):
        parsed_date = _parse_date_value(match.group(1))
        parsed_time = _parse_time_value(match.group(2))
        if parsed_date and parsed_time:
            results.append((_datetime_constraint(match.group(0), parsed_date, parsed_time, text, match.span()), match.span()))
    return results


def _extract_interval_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    date_pattern = _date_fragment_pattern()
    interval_patterns = [
        re.compile(rf"\bbetween\s+({date_pattern})\s+and\s+({date_pattern})", re.IGNORECASE),
        re.compile(rf"\bfrom\s+({date_pattern})\s+to\s+({date_pattern})", re.IGNORECASE),
    ]
    for pattern in interval_patterns:
        for match in pattern.finditer(text):
            start = _parse_date_value(match.group(1))
            end = _parse_date_value(match.group(2))
            if start and end:
                if end < start:
                    start, end = end, start
                results.append(
                    (
                        TemporalConstraint(match.group(0), start.isoformat(), end.isoformat(), "range", 0.75, 0.85, False, _infer_role(text, *match.span())),
                        match.span(),
                    )
                )

    for direction in ("before", "after"):
        pattern = re.compile(rf"\b{direction}\s+({date_pattern})", re.IGNORECASE)
        for match in pattern.finditer(text):
            parsed = _parse_date_value(match.group(1))
            if not parsed:
                continue
            start = "0001-01-01" if direction == "before" else parsed.isoformat()
            end = parsed.isoformat() if direction == "before" else "9999-12-31"
            results.append(
                (
                    TemporalConstraint(match.group(0), start, end, "range", 0.65, 0.80, False, _infer_role(text, *match.span())),
                    match.span(),
                )
            )
    return results


def _extract_fuzzy_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    for match in re.finditer(r"\b(early|mid|late)\s+(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", text, re.IGNORECASE):
        part = match.group(1).lower()
        year = int(match.group(2))
        start_month, end_month = {"early": (1, 4), "mid": (5, 8), "late": (9, 12)}[part]
        start = date(year, start_month, 1)
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
        results.append((_fuzzy_constraint(match.group(0), start, end, text, match.span()), match.span()))

    month_names = "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
    for match in re.finditer(rf"\b(early|mid|late)\s+({month_names})\s+(18\d{{2}}|19\d{{2}}|20\d{{2}}|21\d{{2}})\b", text, re.IGNORECASE):
        part = match.group(1).lower()
        month = MONTHS[match.group(2).lower()]
        year = int(match.group(3))
        start_day, end_day = {"early": (1, 10), "mid": (11, 20), "late": (21, calendar.monthrange(year, month)[1])}[part]
        start = date(year, month, start_day)
        end = date(year, month, end_day)
        results.append((_fuzzy_constraint(match.group(0), start, end, text, match.span()), match.span()))

    date_pattern = _date_fragment_pattern()
    for match in re.finditer(rf"\baround\s+({date_pattern})", text, re.IGNORECASE):
        parsed = _parse_date_value(match.group(1))
        if parsed:
            results.append((_fuzzy_constraint(match.group(0), parsed - timedelta(days=3), parsed + timedelta(days=3), text, match.span()), match.span()))

    for match in re.finditer(r"\baround\s+(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", text, re.IGNORECASE):
        year = int(match.group(1))
        results.append((_fuzzy_constraint(match.group(0), date(year, 1, 1), date(year, 12, 31), text, match.span()), match.span()))
    return results


def _extract_quarter_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    quarter_re = re.compile(r"\b(?:Q([1-4])|(first|second|third|fourth)\s+quarter)\s+(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", re.IGNORECASE)
    ordinal = {"first": 1, "second": 2, "third": 3, "fourth": 4}
    for match in quarter_re.finditer(text):
        quarter = int(match.group(1)) if match.group(1) else ordinal[match.group(2).lower()]
        year = int(match.group(3))
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start = date(year, start_month, 1)
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
        results.append(
            (
                TemporalConstraint(match.group(0), start.isoformat(), end.isoformat(), "quarter", 0.60, 0.90, False, _infer_role(text, *match.span())),
                match.span(),
            )
        )
    return results


def _extract_month_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    month_names = "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    for match in re.finditer(rf"\b({month_names})\s+(18\d{{2}}|19\d{{2}}|20\d{{2}}|21\d{{2}})\b", text, re.IGNORECASE):
        month = MONTHS[match.group(1).lower()]
        year = int(match.group(2))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        results.append(
            (
                TemporalConstraint(match.group(0), start.isoformat(), end.isoformat(), "month", 0.58, 0.90, False, _infer_role(text, *match.span())),
                match.span(),
            )
        )
    return results


def _extract_date_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    for match in ISO_DATE_RE.finditer(text):
        parsed = _parse_date_value(match.group(0))
        if parsed:
            results.append((_date_constraint(match.group(0), parsed, text, match.span(), ambiguous=False), match.span()))

    for pattern in (MONTH_DD_YYYY_RE, DD_MONTH_YYYY_RE, NUMERIC_DATE_RE):
        for match in pattern.finditer(text):
            parsed = _parse_date_value(match.group(0))
            ambiguous = _is_ambiguous_numeric_date(match.group(0))
            if parsed:
                results.append((_date_constraint(match.group(0), parsed, text, match.span(), ambiguous=ambiguous), match.span()))
            elif ambiguous:
                results.append(
                    (
                        TemporalConstraint(match.group(0), "", "", "day", 0.20, 0.30, True, _infer_role(text, *match.span())),
                        match.span(),
                    )
                )
    return results


def _extract_daypart_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    parts = {
        "morning": ("06:00:00", "11:59:59"),
        "afternoon": ("12:00:00", "16:59:59"),
        "evening": ("17:00:00", "20:59:59"),
        "night": ("21:00:00", "05:59:59"),
        "noon": ("12:00:00", "12:00:00"),
        "midnight": ("00:00:00", "00:00:00"),
    }
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    for match in re.finditer(r"\b(morning|afternoon|evening|night|noon|midnight)\b", text, re.IGNORECASE):
        start, end = parts[match.group(1).lower()]
        exact = start == end
        results.append(
            (
                TemporalConstraint(match.group(0), start, end, "time" if exact else "daypart", 0.85 if exact else 0.45, 0.85, False, _infer_role(text, *match.span())),
                match.span(),
            )
        )
    return results


def _extract_time_constraints(text: str) -> list[tuple[TemporalConstraint, tuple[int, int]]]:
    results: list[tuple[TemporalConstraint, tuple[int, int]]] = []
    for match in TIME_RE.finditer(text):
        parsed = _parse_time_value(match.group(0))
        if parsed:
            granularity = "second" if parsed.second else "minute" if parsed.minute else "hour"
            results.append(
                (
                    TemporalConstraint(match.group(0), parsed.isoformat(), parsed.isoformat(), granularity, 0.70, 0.90, False, _infer_role(text, *match.span())),
                    match.span(),
                )
            )
    return results


def _parse_date_value(value: str) -> date | None:
    value = value.strip().replace(",", "")
    iso = ISO_DATE_RE.fullmatch(value)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    month_first = MONTH_DD_YYYY_RE.fullmatch(value)
    if month_first:
        return _safe_date(int(month_first.group(3)), MONTHS[month_first.group(1).lower()], int(month_first.group(2)))
    day_first = DD_MONTH_YYYY_RE.fullmatch(value)
    if day_first:
        return _safe_date(int(day_first.group(3)), MONTHS[day_first.group(2).lower()], int(day_first.group(1)))
    numeric = NUMERIC_DATE_RE.fullmatch(value)
    if numeric:
        first, second, year = int(numeric.group(1)), int(numeric.group(2)), int(numeric.group(3))
        if first > 12 and second <= 12:
            return _safe_date(year, second, first)
        if second > 12 and first <= 12:
            return _safe_date(year, first, second)
        return None
    return None


def _parse_time_value(value: str) -> time | None:
    value = value.strip().lower()
    if value == "noon":
        return time(12, 0, 0)
    if value == "midnight":
        return time(0, 0, 0)
    match = TIME_RE.fullmatch(value)
    if not match:
        return None
    if match.group(5):
        hour = int(match.group(5))
        minute = int(match.group(6))
        second = int(match.group(7) or 0)
    else:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        second = int(match.group(3) or 0)
        marker = match.group(4).lower()
        if marker == "pm" and hour != 12:
            hour += 12
        if marker == "am" and hour == 12:
            hour = 0
    try:
        return time(hour, minute, second)
    except ValueError:
        return None


def _score_constraint_against_interval(constraint: TemporalConstraint, row_start: str, row_end: str, temporal_type: str) -> float:
    constraint_start = _parse_isoish(constraint.normalized_start)
    constraint_end = _parse_isoish(constraint.normalized_end) or constraint_start
    row_start_dt = _parse_isoish(row_start)
    row_end_dt = _parse_isoish(row_end) or row_start_dt
    if not constraint_start or not row_start_dt:
        return 0.08

    if constraint.granularity in {"second", "minute", "hour"} and "T" in constraint.normalized_start:
        if row_start_dt == constraint_start:
            return 1.0
        if row_start_dt.date() == constraint_start.date():
            return 0.42
        if row_start_dt.year == constraint_start.year:
            return 0.18
        return 0.02

    if constraint.granularity == "day":
        if row_start_dt.date() == constraint_start.date() and row_end_dt.date() == constraint_end.date():
            return 1.0
        if row_start_dt.date() <= constraint_start.date() <= row_end_dt.date():
            return 0.78 if temporal_type == "valid_time_range" else 0.62
        if row_start_dt.year == constraint_start.year and row_start_dt.month == constraint_start.month:
            return 0.34
        if row_start_dt.year == constraint_start.year:
            return 0.18
        return 0.02

    if constraint.granularity == "month":
        if row_start_dt.year == constraint_start.year and row_start_dt.month == constraint_start.month:
            return 0.86
        if row_start_dt.year == constraint_start.year:
            return 0.26
        return 0.02

    if constraint.granularity == "year":
        if row_start_dt.year == constraint_start.year:
            return 0.72
        return 0.04

    if constraint.granularity in {"range", "quarter", "fuzzy_interval"}:
        if row_start_dt <= constraint_end and row_end_dt >= constraint_start:
            return 0.78 if constraint.granularity != "fuzzy_interval" else 0.68
        if row_start_dt.year == constraint_start.year or row_start_dt.year == constraint_end.year:
            return 0.25
        return 0.03

    return 0.10


def _constraints_from_expected_valid_time(case: QuestionCase) -> list[TemporalConstraint]:
    constraints: list[TemporalConstraint] = []
    for item in case.expected_valid_time:
        if not item:
            continue
        parsed = _parse_date_value(item)
        if parsed:
            constraints.append(TemporalConstraint(item, parsed.isoformat(), parsed.isoformat(), "day", 0.85, 0.80, False, "valid_time"))
        elif re.fullmatch(r"\d{4}", item):
            constraints.append(TemporalConstraint(item, f"{item}-01-01", f"{item}-12-31", "year", 0.45, 0.75, False, "valid_time"))
    return constraints


def _row_interval(row: CorpusRow, *, use_transaction: bool) -> tuple[str | None, str | None]:
    if use_transaction:
        return row.transaction_time, row.transaction_time
    return row.valid_from, row.valid_to or row.valid_from


def _asks_transaction_role(text: str, constraints: list[TemporalConstraint]) -> bool:
    lowered = text.lower()
    if any(item.temporal_role in {"transaction_time", "publication_time", "filing_time", "release_time"} for item in constraints):
        return True
    return any(token in lowered for token in ("transaction", "publication", "published", "filing", "filed", "release time", "released when", "ingestion"))


def _parse_isoish(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        parsed_time = time.fromisoformat(value)
        return datetime.combine(date(1, 1, 1), parsed_time)
    except ValueError:
        return None


def _date_constraint(original: str, parsed: date, text: str, span: tuple[int, int], *, ambiguous: bool) -> TemporalConstraint:
    return TemporalConstraint(
        original_text=original,
        normalized_start="" if ambiguous else parsed.isoformat(),
        normalized_end="" if ambiguous else parsed.isoformat(),
        granularity="day",
        precision=0.20 if ambiguous else 0.90,
        confidence=0.30 if ambiguous else 0.95,
        ambiguous_parse=ambiguous,
        temporal_role=_infer_role(text, *span),
    )


def _datetime_constraint(original: str, parsed_date: date, parsed_time: time, text: str, span: tuple[int, int]) -> TemporalConstraint:
    normalized = datetime.combine(parsed_date, parsed_time).isoformat()
    granularity = "second" if parsed_time.second else "minute" if parsed_time.minute else "hour"
    return TemporalConstraint(original, normalized, normalized, granularity, 1.0, 0.98, False, _infer_role(text, *span))


def _fuzzy_constraint(original: str, start: date, end: date, text: str, span: tuple[int, int]) -> TemporalConstraint:
    return TemporalConstraint(original, start.isoformat(), end.isoformat(), "fuzzy_interval", 0.50, 0.65, False, _infer_role(text, *span))


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _is_ambiguous_numeric_date(value: str) -> bool:
    match = NUMERIC_DATE_RE.fullmatch(value.strip())
    if not match:
        return False
    first, second = int(match.group(1)), int(match.group(2))
    return first <= 12 and second <= 12


def _covered(span: tuple[int, int], occupied: list[tuple[int, int]]) -> bool:
    return any(span[0] >= start and span[1] <= end for start, end in occupied)


def _infer_role(text: str, start: int, end: int) -> str:
    window = text[max(0, start - 48) : min(len(text), end + 48)].lower()
    for token, role in TRANSACTION_ROLE_WORDS.items():
        if token in window:
            return role
    return "valid_time"


def _date_fragment_pattern() -> str:
    month_names = "|".join(re.escape(name) for name in sorted(MONTHS, key=len, reverse=True))
    return rf"(?:\d{{4}}[-/]\d{{2}}[-/]\d{{2}}|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{4}}|(?:{month_names})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{month_names})\s+\d{{4}})"
