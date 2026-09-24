"""
Resolve QA hours from task config.

Three QC criteria (from QA_NEW_TARGETS_EFFECTIVE_FROM onward — 16 Sep 2026):
  1. object_range — sum agent file column (e.g. New add object); match min-max;
     band value is MINUTES for that file → hours = minutes / 60
  2. file_minutes — fixed minutes per file → hours = minutes / 60
  3. record_minutes — minutes per QC record → hours = qc_count * minutes / 60

If none of the above are configured from that date onward, hours = 0
(no fallback to agent task_target / half-target).

Before QA_NEW_TARGETS_EFFECTIVE_FROM, flat: hours = qc_count / task_target.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any


QA_NEW_TARGETS_EFFECTIVE_FROM = date(2026, 9, 16)


def _float(v, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _round4(v) -> float:
    return round(_float(v), 4)


def parse_qa_target_ranges(raw: Any) -> list[dict]:
    """Bands: {min, max, minutes} (also accepts legacy key `target` as minutes)."""
    if raw is None or raw == "":
        return []
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            mn = float(item.get("min"))
            mx = float(item.get("max"))
            minutes = item.get("minutes", item.get("target"))
            minutes = float(minutes)
        except (TypeError, ValueError):
            continue
        if minutes <= 0:
            continue
        if mx < mn:
            mn, mx = mx, mn
        out.append({"min": mn, "max": mx, "minutes": minutes})
    return out


def match_range_minutes(ranges: list[dict], object_count) -> float | None:
    count = _float(object_count, default=-1.0)
    if count < 0:
        return None
    for band in ranges:
        if band["min"] <= count <= band["max"]:
            return _float(band["minutes"])
    return None


def _parse_work_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _flat_task_target(task_target, qc_generated_count) -> dict:
    """Pre-cutoff only: hours = qc_count / task_target."""
    actual = _round4(task_target)
    qc_count = _float(qc_generated_count)
    hours = _round4(qc_count / actual) if actual else 0.0
    return {
        "actual_target": actual,
        "qa_target": actual,
        "hours": hours,
        "target_mode": "flat",
    }


def _unset_qa_target() -> dict:
    return {
        "actual_target": 0.0,
        "qa_target": 0.0,
        "hours": 0.0,
        "target_mode": "none",
    }


def resolve_qa_targets(
    *,
    task_target=None,
    qa_minutes_per_file=None,
    qa_minutes_per_record=None,
    qa_target_ranges=None,
    object_count=None,
    qc_generated_count=None,
    work_date=None,
    is_rework: bool = False,
) -> dict:
    """
    Returns actual_target, qa_target, hours, target_mode.

    Detection order when new modes are active:
      object_range → file_minutes → record_minutes → none (no task_target fallback)
    For rework (is_rework=True), target is halved:
      - object_range: matched_minutes / 2
      - file_minutes: qa_minutes_per_file / 2
      - record_minutes: qa_minutes_per_record / 2
    """
    wd = _parse_work_date(work_date)
    use_new_modes = wd is None or wd >= QA_NEW_TARGETS_EFFECTIVE_FROM
    if not use_new_modes:
        res = _flat_task_target(task_target, qc_generated_count)
        if is_rework and res.get("actual_target"):
            half_t = _round4(res["actual_target"] / 2.0)
            qc_c = _float(qc_generated_count)
            res["actual_target"] = half_t
            res["qa_target"] = half_t
            res["hours"] = _round4(qc_c / half_t) if half_t else 0.0
        return res

    ranges = parse_qa_target_ranges(qa_target_ranges)
    if ranges:
        matched_minutes = match_range_minutes(ranges, object_count)
        if matched_minutes is not None:
            eff_minutes = (matched_minutes / 2.0) if is_rework else matched_minutes
            hours = _round4(eff_minutes / 60.0)
            return {
                "actual_target": _round4(eff_minutes),
                "qa_target": _round4(eff_minutes),
                "hours": hours,
                "target_mode": "object_range",
            }

    file_min = _float(qa_minutes_per_file, default=0.0)
    if file_min > 0:
        eff_minutes = (file_min / 2.0) if is_rework else file_min
        hours = _round4(eff_minutes / 60.0)
        return {
            "actual_target": _round4(eff_minutes),
            "qa_target": _round4(eff_minutes),
            "hours": hours,
            "target_mode": "file_minutes",
        }

    rec_min = _float(qa_minutes_per_record, default=0.0)
    if rec_min > 0:
        eff_rec_min = (rec_min / 2.0) if is_rework else rec_min
        qc_count = _float(qc_generated_count)
        hours = _round4((qc_count * eff_rec_min) / 60.0)
        return {
            "actual_target": _round4(eff_rec_min),
            "qa_target": _round4(eff_rec_min),
            "hours": hours,
            "target_mode": "record_minutes",
        }

    return _unset_qa_target()


def report_record_counts(rec: dict) -> tuple[int, int]:
    """
    Range tasks count File Record / QC Record from the selected Excel column.
    Other tasks keep the stored file row count and QC sample row count.
    """
    file_rows = int(_float(rec.get("file_record_count")))
    qc_rows = int(_float(rec.get("qc_generated_count")))
    ranges = parse_qa_target_ranges(rec.get("qa_target_ranges"))
    column = str(rec.get("qa_count_column") or "").strip()
    if not ranges or not column or rec.get("object_count") is None:
        return file_rows, qc_rows

    file_sum = int(round(_float(rec.get("object_count"))))
    if rec.get("qc_object_count") is not None:
        qc_sum = int(round(_float(rec.get("qc_object_count"))))
    elif file_rows <= 0 or qc_rows >= file_rows:
        qc_sum = file_sum
    else:
        qc_sum = int(round(_float(rec.get("object_count")) * qc_rows / file_rows))
    return file_sum, qc_sum
