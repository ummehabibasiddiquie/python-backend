"""Attach QC Code to legacy error_list entries that only stored a row number."""

import json
import urllib.request
from io import BytesIO

MAX_FILE_LOADS_PER_REQUEST = 40


def parse_error_list(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def sanitize_file_url(raw):
    file_url = str(raw or "").strip()
    if len(file_url) > 1 and "https://" in file_url[1:]:
        return file_url[file_url.find("https://") :]
    if len(file_url) > 1 and "http://" in file_url[1:]:
        return file_url[file_url.find("http://") :]
    return file_url


def errors_need_qc_code(errors):
    for err in errors or []:
        if isinstance(err, dict) and not str(err.get("qc_code") or err.get("qcCode") or "").strip():
            return True
    return False


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        if value.get("text") is not None:
            return str(value.get("text")).strip()
        if value.get("hyperlink"):
            return str(value.get("hyperlink")).strip()
    return str(value).strip()


def _is_qc_code_header(name):
    n = " ".join(_cell_text(name).replace("_", " ").replace("-", " ").split()).lower()
    if not n:
        return False
    if n in ("qc code", "qccode"):
        return True
    return "qc" in n and "code" in n


def _find_qc_code_column(ws):
    last_col = ws.max_column or 1
    for col in range(1, last_col + 1):
        if _is_qc_code_header(ws.cell(1, col).value):
            return col
    return None


def _data_last_row(ws):
    last_data = 1
    last_col = ws.max_column or 1
    for r in range(2, (ws.max_row or 1) + 1):
        first = str(ws.cell(r, 1).value or "").strip().lower()
        last = str(ws.cell(r, last_col).value or "").strip().lower()
        if first == "error list" or last == "error list":
            break
        last_data = r
    return last_data


def attach_qc_codes_to_error_list(ws, error_list):
    """Copy errors and fill qc_code from the sheet. Legacy row is sample index (1 = first image)."""
    errors = []
    for err in parse_error_list(error_list):
        errors.append(dict(err) if isinstance(err, dict) else err)

    qc_col = _find_qc_code_column(ws)
    if not qc_col:
        return errors

    last_data = _data_last_row(ws)
    display_by_row = {}
    for r in range(2, last_data + 1):
        raw = _cell_text(ws.cell(r, qc_col).value)
        if raw:
            display_by_row[r] = raw

    data_rows = sorted(display_by_row.keys())
    if not data_rows:
        return errors

    only_code = display_by_row[data_rows[0]] if len(data_rows) == 1 else None

    for err in errors:
        if not isinstance(err, dict):
            continue
        if str(err.get("qc_code") or err.get("qcCode") or "").strip():
            continue
        if only_code:
            err["qc_code"] = only_code
            continue
        try:
            row_num = int(err.get("row"))
        except (TypeError, ValueError):
            continue
        mapped = None
        for excel_row in (row_num, row_num + 1, row_num - 1):
            if excel_row in display_by_row:
                mapped = display_by_row[excel_row]
                break
        if not mapped and 1 <= row_num <= len(data_rows):
            mapped = display_by_row.get(data_rows[row_num - 1])
        if mapped:
            err["qc_code"] = mapped
    return errors


def load_worksheet_from_url(file_url):
    from openpyxl import load_workbook

    url = sanitize_file_url(file_url)
    if not url.startswith("http"):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "HRMS-QC-Enrich/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        payload = BytesIO(resp.read())
    wb = load_workbook(payload, read_only=False, data_only=False)
    return wb.active


def backfill_error_lists(cursor, conn, items, sheet_cache=None, max_loads=MAX_FILE_LOADS_PER_REQUEST):
    """
    items: list of dicts with keys:
      table, id_field, id_value, file_url, error_list, assign (callable or None)
    Mutates assign target and UPDATEs DB when codes are filled.
    """
    if sheet_cache is None:
        sheet_cache = {}
    loads = 0
    updated = 0

    for item in items:
        errors = parse_error_list(item.get("error_list"))
        if not errors_need_qc_code(errors):
            continue
        file_url = sanitize_file_url(item.get("file_url"))
        if not file_url.startswith("http"):
            continue

        if file_url not in sheet_cache:
            if loads >= max_loads:
                continue
            try:
                sheet_cache[file_url] = load_worksheet_from_url(file_url)
                loads += 1
            except Exception as exc:
                print("[qc_code_enrich] file load failed:", file_url, exc)
                sheet_cache[file_url] = None

        ws = sheet_cache.get(file_url)
        if ws is None:
            continue

        enriched = attach_qc_codes_to_error_list(ws, errors)
        if not any(isinstance(e, dict) and str(e.get("qc_code") or "").strip() for e in enriched):
            continue
        if not errors_need_qc_code(errors) and not errors_need_qc_code(enriched):
            continue

        table = item["table"]
        id_field = item["id_field"]
        error_field = item.get("error_field", "error_list")
        try:
            cursor.execute(
                f"UPDATE {table} SET {error_field} = %s WHERE {id_field} = %s",
                (json.dumps(enriched), item["id_value"]),
            )
            updated += 1
        except Exception as exc:
            print("[qc_code_enrich] update failed:", table, item.get("id_value"), exc)
            continue

        assign = item.get("assign")
        if callable(assign):
            assign(enriched)

    if updated:
        try:
            conn.commit()
        except Exception as exc:
            print("[qc_code_enrich] commit failed:", exc)
    return updated
