# routes/holiday.py

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from flask import Blueprint, request

from config import get_db_connection
from utils.response import api_response
from utils.roster_helpers import (
    can_modify_holiday_master,
    get_role_context,
    now_str,
    parse_date,
)

holiday_bp = Blueprint("holiday", __name__)

HOLIDAY_EXCEL_COLUMNS = {
    "holiday_date": ["holiday_date", "date", "holiday date"],
    "holiday_name": ["holiday_name", "name", "holiday name", "holiday"],
}


def _normalize_column_name(name: str) -> str:
    return str(name or "").strip().lower().replace("_", " ")


def _map_excel_columns(columns: list) -> dict[str, str]:
    mapping: dict[str, str] = {}
    normalized = {_normalize_column_name(c): c for c in columns}
    for target, aliases in HOLIDAY_EXCEL_COLUMNS.items():
        for alias in aliases:
            key = _normalize_column_name(alias)
            if key in normalized:
                mapping[target] = normalized[key]
                break
    return mapping


def _require_logged_in_user(data: dict) -> tuple[int | None, dict | None]:
    logged_in_user_id = data.get("logged_in_user_id")
    if not logged_in_user_id:
        return None, api_response(400, "logged_in_user_id is required")
    return int(logged_in_user_id), None


@holiday_bp.route("/list", methods=["POST"])
def list_holidays():
    """View-only for all roles."""
    data = request.get_json(silent=True) or {}
    logged_in_user_id, err = _require_logged_in_user(data)
    if err:
        return err

    calendar_year = data.get("calendar_year")
    include_inactive = bool(data.get("include_inactive", False))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        if not ctx.get("user_role_name"):
            return api_response(404, "User not found")

        where = "WHERE 1=1"
        params: list = []
        if calendar_year:
            where += " AND h.calendar_year=%s"
            params.append(int(calendar_year))
        if not include_inactive:
            where += " AND h.is_active=1"

        cursor.execute(
            f"""
            SELECT
                h.holiday_id,
                h.holiday_date,
                h.holiday_name,
                h.calendar_year,
                h.is_active,
                h.created_by,
                h.created_date,
                h.updated_date,
                u.user_name AS created_by_name
            FROM org_holiday h
            LEFT JOIN tfs_user u ON u.user_id = h.created_by
            {where}
            ORDER BY h.holiday_date ASC
            """,
            tuple(params),
        )
        rows = cursor.fetchall() or []
        for row in rows:
            if row.get("holiday_date"):
                row["holiday_date"] = row["holiday_date"].isoformat()
        return api_response(200, "Holidays fetched successfully", rows)
    except Exception as e:
        return api_response(500, f"Failed to fetch holidays: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@holiday_bp.route("/add", methods=["POST"])
def add_holiday():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, err = _require_logged_in_user(data)
    if err:
        return err

    holiday_date = parse_date(data.get("holiday_date"))
    holiday_name = (data.get("holiday_name") or "").strip()
    if not holiday_date or not holiday_name:
        return api_response(400, "holiday_date and holiday_name are required")

    calendar_year = int(data.get("calendar_year") or holiday_date.year)
    now = now_str()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        if not can_modify_holiday_master(ctx.get("user_role_name", "")):
            return api_response(403, "Only Super Admin can modify the Holiday Master")

        cursor.execute(
            """
            INSERT INTO org_holiday (
                holiday_date, holiday_name, calendar_year,
                is_active, created_by, created_date, updated_date
            ) VALUES (%s,%s,%s,1,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                holiday_name=VALUES(holiday_name),
                is_active=1,
                updated_date=VALUES(updated_date)
            """,
            (holiday_date.isoformat(), holiday_name, calendar_year, logged_in_user_id, now, now),
        )
        conn.commit()
        return api_response(201, "Holiday added successfully", {"holiday_id": cursor.lastrowid})
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to add holiday: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@holiday_bp.route("/update", methods=["POST"])
def update_holiday():
    data = request.get_json(silent=True) or {}
    logged_in_user_id, err = _require_logged_in_user(data)
    if err:
        return err

    holiday_id = data.get("holiday_id")
    if not holiday_id:
        return api_response(400, "holiday_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        if not can_modify_holiday_master(ctx.get("user_role_name", "")):
            return api_response(403, "Only Super Admin can modify the Holiday Master")

        updates = []
        params: list = []
        if data.get("holiday_date"):
            d = parse_date(data.get("holiday_date"))
            if not d:
                return api_response(400, "Invalid holiday_date")
            updates.append("holiday_date=%s")
            params.append(d.isoformat())
        if data.get("holiday_name") is not None:
            updates.append("holiday_name=%s")
            params.append(str(data.get("holiday_name")).strip())
        if data.get("calendar_year") is not None:
            updates.append("calendar_year=%s")
            params.append(int(data.get("calendar_year")))
        if data.get("is_active") is not None:
            updates.append("is_active=%s")
            params.append(int(data.get("is_active")))

        if not updates:
            return api_response(400, "No valid fields provided for update")

        updates.append("updated_date=%s")
        params.append(now_str())
        params.append(int(holiday_id))

        cursor.execute(
            f"UPDATE org_holiday SET {', '.join(updates)} WHERE holiday_id=%s",
            tuple(params),
        )
        conn.commit()
        return api_response(200, "Holiday updated successfully")
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to update holiday: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@holiday_bp.route("/delete", methods=["POST"])
def deactivate_holiday():
    """Soft deactivate — nothing is permanently deleted."""
    data = request.get_json(silent=True) or {}
    logged_in_user_id, err = _require_logged_in_user(data)
    if err:
        return err

    holiday_id = data.get("holiday_id")
    if not holiday_id:
        return api_response(400, "holiday_id is required")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        ctx = get_role_context(cursor, logged_in_user_id)
        if not can_modify_holiday_master(ctx.get("user_role_name", "")):
            return api_response(403, "Only Super Admin can modify the Holiday Master")

        cursor.execute(
            "UPDATE org_holiday SET is_active=0, updated_date=%s WHERE holiday_id=%s",
            (now_str(), int(holiday_id)),
        )
        conn.commit()
        return api_response(200, "Holiday deactivated successfully")
    except Exception as e:
        conn.rollback()
        return api_response(500, f"Failed to deactivate holiday: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@holiday_bp.route("/upload", methods=["POST"])
def upload_holiday_excel():
  """
  Super Admin uploads yearly holiday Excel.
  Expected columns: holiday_date, holiday_name
  """
  logged_in_user_id = request.form.get("logged_in_user_id")
  if not logged_in_user_id:
      return api_response(400, "logged_in_user_id is required")

  uploaded = request.files.get("file") or request.files.get("holiday_file")
  if not uploaded or not uploaded.filename:
      return api_response(400, "Excel file is required")

  calendar_year = request.form.get("calendar_year")
  if not calendar_year:
      return api_response(400, "calendar_year is required")

  conn = get_db_connection()
  cursor = conn.cursor(dictionary=True)
  try:
      ctx = get_role_context(cursor, int(logged_in_user_id))
      if not can_modify_holiday_master(ctx.get("user_role_name", "")):
          return api_response(403, "Only Super Admin can modify the Holiday Master")

      file_bytes = uploaded.read()
      df = pd.read_excel(io.BytesIO(file_bytes))
      if df.empty:
          return api_response(400, "Excel file is empty")

      col_map = _map_excel_columns(list(df.columns))
      if "holiday_date" not in col_map or "holiday_name" not in col_map:
          return api_response(
              400,
              "Excel must contain holiday_date and holiday_name columns",
          )

      now = now_str()
      year = int(calendar_year)
      inserted = 0
      updated = 0
      skipped = []

      for idx, row in df.iterrows():
          try:
              raw_date = row[col_map["holiday_date"]]
              if pd.isna(raw_date):
                  skipped.append({"row": int(idx) + 2, "reason": "missing holiday_date"})
                  continue
              if isinstance(raw_date, datetime):
                  holiday_date = raw_date.date()
              else:
                  holiday_date = parse_date(str(raw_date))
              holiday_name = str(row[col_map["holiday_name"]]).strip()
              if not holiday_date or not holiday_name or holiday_name.lower() == "nan":
                  skipped.append({"row": int(idx) + 2, "reason": "invalid holiday data"})
                  continue

              cursor.execute(
                  "SELECT holiday_id FROM org_holiday WHERE holiday_date=%s AND calendar_year=%s",
                  (holiday_date.isoformat(), year),
              )
              existing = cursor.fetchone()
              if existing:
                  cursor.execute(
                      """
                      UPDATE org_holiday
                      SET holiday_name=%s, is_active=1, updated_date=%s
                      WHERE holiday_id=%s
                      """,
                      (holiday_name, now, int(existing["holiday_id"])),
                  )
                  updated += 1
              else:
                  cursor.execute(
                      """
                      INSERT INTO org_holiday (
                          holiday_date, holiday_name, calendar_year,
                          is_active, created_by, created_date, updated_date
                      ) VALUES (%s,%s,%s,1,%s,%s,%s)
                      """,
                      (
                          holiday_date.isoformat(),
                          holiday_name,
                          year,
                          int(logged_in_user_id),
                          now,
                          now,
                      ),
                  )
                  inserted += 1
          except Exception as row_err:
              skipped.append({"row": int(idx) + 2, "reason": str(row_err)})

      conn.commit()
      return api_response(
          200,
          "Holiday Excel processed successfully",
          {"inserted": inserted, "updated": updated, "skipped": skipped},
      )
  except Exception as e:
      conn.rollback()
      return api_response(500, f"Holiday upload failed: {str(e)}")
  finally:
      cursor.close()
      conn.close()
