"""Notify the agent when a leave change request is approved or rejected."""

from __future__ import annotations

import html
import json
import logging
from typing import Any

from utils.email_utils import send_email

logger = logging.getLogger(__name__)

LEAVE_CHANGE_TYPES = frozenset({"LEAVE_ADD", "LEAVE_UPDATE", "LEAVE_DELETE"})


def _safe(text: Any) -> str:
    return html.escape(str(text or "").strip())


def _parse_payload(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _yes_no(value: Any) -> str:
    try:
        return "Yes" if int(value or 0) else "No"
    except (TypeError, ValueError):
        return "Yes" if value else "No"


def _action_label(change_type: str) -> str:
    return {
        "LEAVE_ADD": "Leave application",
        "LEAVE_UPDATE": "Leave update",
        "LEAVE_DELETE": "Leave removal",
    }.get(change_type, "Leave request")


def _build_html(
    *,
    agent_name: str,
    status: str,
    change_type: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    is_half_day: str,
    apply_reason: str,
    reviewer_comment: str | None,
) -> str:
    is_approved = status.lower() == "approved"
    status_color = "#15803d" if is_approved else "#b91c1c"
    status_bg = "#dcfce7" if is_approved else "#fee2e2"
    headline = (
        f"Your {_action_label(change_type).lower()} has been <strong>{status}</strong>."
    )
    comment_label = "Approver comment" if is_approved else "Rejection reason"
    comment_row = ""
    if reviewer_comment:
        comment_row = f"""
        <tr>
          <td style="padding:8px 0;color:#6b7280;">{comment_label}</td>
          <td style="padding:8px 0;color:#111827;">{_safe(reviewer_comment)}</td>
        </tr>
        """
    elif not is_approved:
        comment_row = f"""
        <tr>
          <td style="padding:8px 0;color:#6b7280;">{comment_label}</td>
          <td style="padding:8px 0;color:#111827;">—</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 12px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:10px;overflow:hidden;">
          <tr>
            <td style="background:#111827;color:#ffffff;padding:18px 24px;font-size:18px;font-weight:bold;">
              HRMS Leave Decision
            </td>
          </tr>
          <tr>
            <td style="padding:24px;">
              <p style="margin:0 0 12px;color:#111827;">Hi {_safe(agent_name) or "there"},</p>
              <p style="margin:0 0 16px;color:#374151;">{headline}</p>
              <div style="display:inline-block;padding:6px 12px;border-radius:999px;
                          background:{status_bg};color:{status_color};font-weight:bold;margin-bottom:16px;">
                {status.upper()}
              </div>
              <table width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">
                <tr>
                  <td style="padding:8px 0;color:#6b7280;width:40%;">Request type</td>
                  <td style="padding:8px 0;color:#111827;">{_safe(_action_label(change_type))}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#6b7280;">Leave type</td>
                  <td style="padding:8px 0;color:#111827;">{_safe(leave_type) or "—"}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#6b7280;">Dates</td>
                  <td style="padding:8px 0;color:#111827;">{_safe(start_date) or "—"} to {_safe(end_date) or "—"}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#6b7280;">Half day</td>
                  <td style="padding:8px 0;color:#111827;">{_safe(is_half_day)}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;color:#6b7280;">Application reason</td>
                  <td style="padding:8px 0;color:#111827;">{_safe(apply_reason) or "—"}</td>
                </tr>
                {comment_row}
              </table>
              <p style="margin:20px 0 0;color:#374151;">
                Best regards,<br />
                <strong>TRANSFORM Solutions (P) Limited</strong>
              </p>
            </td>
          </tr>
          <tr>
            <td align="center"
                style="background:#f3f4f6;padding:14px;color:#6b7280;font-size:11px;">
              © 2026 TRANSFORM Solutions (P) Limited. All rights reserved.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def notify_agent_leave_decision(cursor, req: dict, *, status: str, reviewer_comment: str | None = None) -> None:
    """
    Email the roster agent about leave approve/reject.
    Failures are logged only — they must not undo the decision.
    """
    change_type = (req.get("change_type") or "").strip()
    if change_type not in LEAVE_CHANGE_TYPES:
        print(f"[leave_email] skipped: change_type={change_type!r} (not a leave request)")
        return

    user_id = req.get("user_id")
    if not user_id:
        print("[leave_email] skipped: missing user_id on request")
        return

    cursor.execute(
        """
        SELECT user_id, user_name, user_email
        FROM tfs_user
        WHERE user_id=%s
        LIMIT 1
        """,
        (int(user_id),),
    )
    agent = cursor.fetchone() or {}
    to_email = (agent.get("user_email") or "").strip()
    if not to_email:
        msg = f"[leave_email] skipped: no email for user_id={user_id}"
        print(msg)
        logger.warning("Leave %s email skipped: no email for user_id=%s", status, user_id)
        return

    payload = _parse_payload(req.get("change_payload"))
    leave_type = (payload.get("leave_type") or "").strip() or "Leave"
    start_date = str(payload.get("start_date") or "")[:10]
    end_date = str(payload.get("end_date") or "")[:10]
    is_half_day = _yes_no(payload.get("is_half_day"))
    apply_reason = (payload.get("reason") or "").strip()
    agent_name = (agent.get("user_name") or "").strip() or "there"
    status_label = "Approved" if status.lower() == "approved" else "Rejected"

    subject = (
        f"Leave {status_label}: {leave_type} ({start_date} to {end_date})"
        if start_date and end_date
        else f"Leave {status_label}: {leave_type}"
    )
    html = _build_html(
        agent_name=agent_name,
        status=status_label,
        change_type=change_type,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        apply_reason=apply_reason,
        reviewer_comment=(reviewer_comment or "").strip() or None,
    )

    print(
        f"[leave_email] sending {status_label} mail to {to_email} "
        f"(user_id={user_id}, leave={leave_type}, {start_date}..{end_date})"
    )
    try:
        send_email(to_email, subject, html)
        print(f"[leave_email] SUCCESS: {status_label} email sent to {to_email}")
        logger.info("Leave %s email sent to %s (user_id=%s)", status_label, to_email, user_id)
    except Exception as mail_err:
        print(f"[leave_email] FAILED: {status_label} email to {to_email} — {mail_err}")
        logger.exception(
            "Leave %s email failed for user_id=%s: %s", status_label, user_id, mail_err
        )
