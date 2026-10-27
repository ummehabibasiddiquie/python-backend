"""
Weekly goal report: every Monday, email last week's (Mon-Sun) agents who did not reach their weekly goal.

Weekly goal = the monthly-target rule (utils.roster_metrics) applied to the week's roster: Mon-Fri days that
are not holidays at the agent's daily hours (9 x tenure), minus half working days, "Left" days and leave that
affects the target. Leave that does not affect the target still counts in the goal. Agents with no roster for
the week fall back to their daily assigned hours (temp_qc).
Achieved = billable hours from tracker entries (production / tenure target), the same figures as the daily
billable report. Agents of teams A and B only.

Recipients (active users, by role):
  Admin, Project Manager           -> all agents
  Assistant Manager, Team Leader   -> only the agents assigned to them
If everyone in a recipient's list reached the goal, they get an "all achieved" email instead.

Usage (from backend-api; server cron runs it every Monday at 10:30 IST):
    python weekly_goal_report.py                                   # last week, send to everyone
    python weekly_goal_report.py --dry-run                         # show who would get what, send nothing
    python weekly_goal_report.py --week-start 2026-10-19           # send a past week again (any date in it works)
    python weekly_goal_report.py --week-start 2026-10-19 --to name@transformsolution.net   # resend to one person
    python weekly_goal_report.py --test-to a@transformsolution.net,b@transformsolution.net  # test: full report to these only

Stop / start / change time: comment out, uncomment or edit its line in the server crontab (crontab -e).
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import smtplib
from collections import defaultdict
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(dotenv_path=HERE / ".env")

from utils.roster_helpers import FULL_DAY_HOURS, daily_hours_for_tenure  # noqa: E402
from utils.roster_metrics import (  # noqa: E402
    apply_active_leaves_to_days,
    recalculate_metrics_from_days_and_leaves,
)

logging.basicConfig(
    filename=HERE / "weekly_goal_report.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

ROLE_ADMIN, ROLE_PM, ROLE_AM, ROLE_TL = 2, 3, 4, 7
FULL_LIST_ROLES = (ROLE_ADMIN, ROLE_PM)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE", "tfs_hrms"),
    )


def last_week(today: date) -> tuple[date, date]:
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(days=7)
    return start, start + timedelta(days=6)


def id_list(value) -> set[int]:
    """Reporting-line columns hold ID lists such as "[192]", "192,193" or "192"."""
    return {int(x) for x in re.findall(r"\d+", str(value or ""))}


def roster_week_goals(cursor, ids: list[int], tenure: dict[int, object], week_start: date,
                      week_end: date) -> dict[int, float]:
    """Week goal per agent from the roster, with the same rules as the monthly target."""
    ph = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        SELECT rm.user_id, rd.roster_date, rd.day_type, rd.working_type, rd.working_hours,
               rd.holiday_id, rd.leave_id
        FROM roster_day rd
        JOIN roster_month rm ON rm.roster_month_id = rd.roster_month_id AND rm.is_active = 1
        WHERE rd.is_active = 1 AND rd.roster_date BETWEEN %s AND %s AND rm.user_id IN ({ph})
        ORDER BY rm.user_id, rd.roster_date
        """,
        [week_start, week_end] + ids,
    )
    days_by_user: dict[int, list[dict]] = defaultdict(list)
    for row in cursor.fetchall():
        if (row.get("day_type") or "").strip() != "PreJoin":
            days_by_user[row["user_id"]].append(row)

    cursor.execute(
        f"""
        SELECT rm.user_id, rl.leave_id, rl.start_date, rl.end_date, rl.affect_target, rl.is_half_day,
               rl.is_rostered, rl.leave_type, rl.is_active
        FROM roster_leave rl
        JOIN roster_month rm ON rm.roster_month_id = rl.roster_month_id AND rm.is_active = 1
        WHERE rl.is_active = 1 AND rl.start_date <= %s AND rl.end_date >= %s AND rm.user_id IN ({ph})
        """,
        [week_end, week_start] + ids,
    )
    leaves_by_user: dict[int, list[dict]] = defaultdict(list)
    for row in cursor.fetchall():
        leaves_by_user[row["user_id"]].append(row)

    goals = {}
    for uid, days in days_by_user.items():
        leaves = leaves_by_user.get(uid, [])
        merged = apply_active_leaves_to_days(days, leaves)
        hours = float(recalculate_metrics_from_days_and_leaves(merged, leaves)["monthly_target_hours"] or 0)
        if not any((d.get("day_type") or "") == "Working" for d in days):
            # No working day to read the agent's daily hours from, so scale the 9 h default by tenure.
            hours = hours * daily_hours_for_tenure(tenure.get(uid)) / FULL_DAY_HOURS
        goals[uid] = round(hours, 2)
    return goals


def fetch_week(cursor, week_start: date, week_end: date) -> list[dict]:
    cursor.execute(
        """
        SELECT u.user_id, u.user_name, t.team_name, u.asst_manager_id, u.team_leader_id, u.user_tenure
        FROM tfs_user u
        JOIN user_role r ON r.role_id = u.role_id
        LEFT JOIN team t ON t.team_id = u.team_id
        WHERE u.is_delete = 1
          AND LOWER(r.role_name) = 'agent'
          AND t.team_name IN ('A', 'B')
          AND LOWER(TRIM(u.user_name)) <> LOWER(TRIM(t.team_name))
          AND DATE(u.created_date) <= %s
          AND (u.is_active = 1 OR (u.deactivated_at IS NOT NULL AND DATE(u.deactivated_at) >= %s))
        ORDER BY t.team_name, u.user_name
        """,
        (week_end, week_start),
    )
    agents = cursor.fetchall()
    if not agents:
        return []

    ids = [a["user_id"] for a in agents]
    ph = ",".join(["%s"] * len(ids))

    cursor.execute(
        f"""
        SELECT user_id, SUM(production / NULLIF(tenure_target, 0)) AS hours
        FROM task_work_tracker
        WHERE is_active = 1 AND DATE(date_time) BETWEEN %s AND %s AND user_id IN ({ph})
        GROUP BY user_id
        """,
        [week_start, week_end] + ids,
    )
    achieved = {r["user_id"]: float(r["hours"] or 0) for r in cursor.fetchall()}

    cursor.execute(
        f"""
        SELECT user_id, SUM(assigned_hours) AS hours
        FROM temp_qc
        WHERE DATE(date) BETWEEN %s AND %s AND user_id IN ({ph})
        GROUP BY user_id
        """,
        [week_start, week_end] + ids,
    )
    goal = {r["user_id"]: float(r["hours"] or 0) for r in cursor.fetchall()}
    goal.update(roster_week_goals(cursor, ids, {a["user_id"]: a["user_tenure"] for a in agents},
                                  week_start, week_end))

    rows = []
    for a in agents:
        week_goal = round(goal.get(a["user_id"], 0.0), 2)
        if week_goal <= 0:
            continue  # nothing assigned that week (full leave, not yet joined)
        done = round(achieved.get(a["user_id"], 0.0), 2)
        rows.append({
            "user_id": a["user_id"],
            "name": a["user_name"],
            "team": a["team_name"],
            "am_ids": id_list(a["asst_manager_id"]),
            "tl_ids": id_list(a["team_leader_id"]),
            "goal": week_goal,
            "achieved": done,
            "shortfall": round(max(week_goal - done, 0), 2),
            "percent": round(done / week_goal * 100, 1),
        })
    return rows


def fetch_recipients(cursor) -> list[dict]:
    cursor.execute(
        """
        SELECT user_id, user_name, user_email, role_id
        FROM tfs_user
        WHERE is_active = 1 AND is_delete = 1 AND role_id IN (%s, %s, %s, %s)
          AND user_email IS NOT NULL AND TRIM(user_email) <> ''
        """,
        (ROLE_ADMIN, ROLE_PM, ROLE_AM, ROLE_TL),
    )
    return cursor.fetchall()


def rows_for(recipient: dict, rows: list[dict]) -> list[dict]:
    role = int(recipient["role_id"])
    if role in FULL_LIST_ROLES:
        return rows
    key = "am_ids" if role == ROLE_AM else "tl_ids"
    return [r for r in rows if recipient["user_id"] in r[key]]


def week_label(start: date, end: date) -> str:
    return f"{start:%d %b} - {end:%d %b %Y}"


FONT = "font-family:Segoe UI,Arial,Helvetica,sans-serif"
BRAND = "#1D4ED8"
GOAL_NOTE = ("Week goal = Monday-Friday working days at each agent's daily hours, minus holidays, half days and "
             "leave that affects the target. Leave that does not affect the target still counts in the goal.")


def percent_colours(percent: float) -> tuple[str, str]:
    """(text / bar colour, light background) for the % achieved badge."""
    if percent < 50:
        return "#B91C1C", "#FEE2E2"
    if percent < 80:
        return "#B45309", "#FEF3C7"
    return "#1D4ED8", "#DBEAFE"


def summary_box(value, label: str, colour: str, background: str) -> str:
    return (
        f'<td width="33%" style="padding:6px">'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="background:{background};border-radius:8px">'
        f'<tr><td align="center" style="padding:14px 8px;{FONT}">'
        f'<div style="font-size:26px;font-weight:700;color:{colour}">{value}</div>'
        f'<div style="font-size:12px;color:#475569;margin-top:2px">{label}</div>'
        "</td></tr></table></td>"
    )


def agent_row(r: dict, shaded: bool) -> str:
    colour, background = percent_colours(r["percent"])
    bar = max(2, min(100, int(round(r["percent"]))))
    cell = f"padding:9px 10px;border-bottom:1px solid #E2E8F0;{FONT};font-size:13px;color:#0F172A"
    return (
        f'<tr style="background:{"#F8FAFC" if shaded else "#FFFFFF"}">'
        f'<td style="{cell}">{r["name"]}</td>'
        f'<td align="right" style="{cell}">{r["goal"]:.2f}</td>'
        f'<td align="right" style="{cell}">{r["achieved"]:.2f}</td>'
        f'<td align="right" style="{cell};color:#B91C1C;font-weight:600">{r["shortfall"]:.2f}</td>'
        f'<td style="{cell};width:150px">'
        f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="background:#E2E8F0;border-radius:4px;height:8px">'
        f'<table width="{bar}%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="background:{colour};border-radius:4px;height:8px;font-size:0;line-height:0">&nbsp;</td>'
        "</tr></table></td>"
        f'<td width="52" align="right" style="padding-left:8px">'
        f'<span style="background:{background};color:{colour};border-radius:10px;padding:2px 7px;'
        f'font-size:12px;font-weight:700;{FONT}">{r["percent"]:.0f}%</span></td>'
        "</tr></table></td></tr>"
    )


def build_html(recipient: dict, rows: list[dict], start: date, end: date) -> str:
    label = week_label(start, end)
    missed = sorted((r for r in rows if r["achieved"] < r["goal"]), key=lambda r: (r["team"], r["percent"]))
    achieved_count = len(rows) - len(missed)
    own_team = int(recipient["role_id"]) not in FULL_LIST_ROLES
    missed_line = (f"{len(missed)} of your {len(rows)} agents" if own_team
                   else f"{len(missed)} of {len(rows)} agents (teams A and B)")
    all_line = f"All {len(rows)} of your agents" if own_team else f"All {len(rows)} agents (teams A and B)"

    header = (
        f'<tr><td style="background:{BRAND};padding:22px 26px;border-radius:10px 10px 0 0;{FONT}">'
        '<div style="font-size:20px;font-weight:700;color:#FFFFFF">Weekly Goal Report</div>'
        f'<div style="font-size:13px;color:#DBEAFE;margin-top:4px">{label}</div>'
        "</td></tr>"
    )
    intro = (
        f'<p style="margin:0 0 14px;font-size:14px;color:#0F172A">Hello {recipient["user_name"]},</p>'
    )
    summary = (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px"><tr>'
        + summary_box(len(rows), "Agents checked", "#0F172A", "#F1F5F9")
        + summary_box(len(missed), "Missed the goal", "#B91C1C", "#FEE2E2")
        + summary_box(achieved_count, "Achieved the goal", "#15803D", "#DCFCE7")
        + "</tr></table>"
    )

    if not missed:
        content = (
            intro + summary
            + '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td style="background:#DCFCE7;border-left:4px solid #15803D;padding:14px 16px;{FONT};'
            'font-size:14px;color:#14532D;border-radius:6px">'
            f"<b>Great week!</b> {all_line} achieved their weekly goal.</td></tr></table>"
        )
    else:
        th = (f"padding:10px;{FONT};font-size:12px;font-weight:700;color:#FFFFFF;background:#1E3A8A;"
              "text-transform:uppercase;letter-spacing:0.3px")
        table = (
            '<table width="100%" cellpadding="0" cellspacing="0" '
            'style="border-collapse:collapse;border:1px solid #E2E8F0">'
            f'<tr><th align="left" style="{th}">Agent</th><th align="right" style="{th}">Week goal (h)</th>'
            f'<th align="right" style="{th}">Achieved (h)</th><th align="right" style="{th}">Shortfall (h)</th>'
            f'<th align="left" style="{th}">% achieved</th></tr>'
        )
        by_team: dict[str, list[dict]] = defaultdict(list)
        for r in missed:
            by_team[r["team"]].append(r)
        for team, members in by_team.items():
            table += (
                f'<tr><td colspan="5" style="background:#EFF6FF;padding:7px 10px;{FONT};font-size:12px;'
                f'font-weight:700;color:{BRAND};border-bottom:1px solid #E2E8F0">Team {team} - '
                f'{len(members)} agent{"s" if len(members) != 1 else ""}</td></tr>'
            )
            for i, r in enumerate(members):
                table += agent_row(r, i % 2 == 1)
        table += "</table>"
        content = (
            intro
            + f'<p style="margin:0 0 14px;font-size:14px;color:#334155">{missed_line} did not achieve their '
            "weekly goal last week.</p>"
            + summary + table
        )

    footer = (
        f'<tr><td style="padding:14px 26px 22px;{FONT};font-size:11px;color:#64748B">'
        f"{GOAL_NOTE}<br>Automated report from TFS HRMS.</td></tr>"
    )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:20px 0">'
        '<tr><td align="center">'
        '<table width="680" cellpadding="0" cellspacing="0" '
        'style="background:#FFFFFF;border-radius:10px;border:1px solid #E2E8F0">'
        f"{header}"
        f'<tr><td style="padding:22px 26px 6px;{FONT}">{content}</td></tr>'
        f"{footer}"
        "</table></td></tr></table>"
    )


def send(to_email: str, subject: str, html: str) -> None:
    user = os.getenv("SMTP_USER")
    msg = MIMEMultipart("alternative")
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 587))) as server:
        server.starttls()
        server.login(user, os.getenv("SMTP_PASS"))
        server.sendmail(user, [to_email], msg.as_string())


def send_test(test_to: str, start: date, end: date, rows: list[dict]) -> dict:
    """Send the full (Admin view) report only to the given addresses (comma-separated), marked as a test."""
    addresses = [a.strip() for a in test_to.split(",") if a.strip()]
    for address in addresses:
        reader = {"user_name": address, "role_id": ROLE_ADMIN}
        send(address, f"[TEST] Weekly goal report: {week_label(start, end)}", build_html(reader, rows, start, end))
        logging.info("test report sent to %s for %s", address, week_label(start, end))
    result = {"week": week_label(start, end), "agents": len(rows),
              "missed": sum(1 for r in rows if r["achieved"] < r["goal"]), "test_sent_to": addresses}
    print(result)
    return result


def run(week_start: date | None = None, dry_run: bool = False, only_to: str | None = None,
        test_to: str | None = None) -> dict:
    if week_start is None:
        start, end = last_week(datetime.now().date())
    else:
        start = week_start - timedelta(days=week_start.weekday())
        end = start + timedelta(days=6)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        rows = fetch_week(cursor, start, end)
        recipients = fetch_recipients(cursor)
    finally:
        cursor.close()
        conn.close()

    if test_to:
        return send_test(test_to, start, end, rows)

    if only_to:
        recipients = [r for r in recipients if r["user_email"].strip().lower() == only_to.strip().lower()]
        if not recipients:
            print(f"{only_to} is not an active Admin, Project Manager, Assistant Manager or Team Lead; nothing sent.")

    subject = f"Weekly goal report: {week_label(start, end)}"
    summary = defaultdict(int)
    for recipient in recipients:
        own_rows = rows_for(recipient, rows)
        if not own_rows:
            summary["skipped_no_agents"] += 1
            continue
        missed = sum(1 for r in own_rows if r["achieved"] < r["goal"])
        line = (f"{recipient['user_name']} (role {recipient['role_id']}): {len(own_rows)} agents, "
                f"{missed} missed the goal")
        if dry_run:
            print("[dry-run]", recipient["user_email"], "-", line)
            summary["would_send"] += 1
            continue
        try:
            send(recipient["user_email"], subject, build_html(recipient, own_rows, start, end))
            logging.info("sent to %s - %s", recipient["user_email"], line)
            summary["sent"] += 1
        except Exception:
            logging.exception("failed to send to %s", recipient["user_email"])
            summary["failed"] += 1

    result = {"week": week_label(start, end), "agents": len(rows),
              "missed": sum(1 for r in rows if r["achieved"] < r["goal"]), **summary}
    logging.info("weekly goal report done: %s", result)
    print(result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print recipients and counts, send nothing")
    parser.add_argument("--week-start", help="any date in the week to report, YYYY-MM-DD (default: last week)")
    parser.add_argument("--to", help="send only to this recipient's email")
    parser.add_argument("--test-to", help="send the full report only to these addresses (comma-separated), "
                                          "marked [TEST]")
    args = parser.parse_args()
    try:
        week = datetime.strptime(args.week_start, "%Y-%m-%d").date() if args.week_start else None
        run(week, args.dry_run, args.to, args.test_to)
    except Exception:
        logging.exception("weekly goal report failed")
        raise
