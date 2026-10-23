# HRMS — Admin & Super Admin Access Control

**Document type:** Privileged access reference  
**System:** HRMS (Human Resource Management System)  
**Audience:** System owners, HR leadership, IT / product owners  
**Date:** 18 September 2026

> **Companion document:** Operational roles (Project Manager, Assistant Manager, Team Leader, QA, Agent) are covered in  
> **HRMS Role-Based Access Control** (`ROLE_BASED_ACCESS.md` / matching PDF).  
> This document covers **Admin** and **Super Admin** only.

---

## 1. Purpose

This document describes the highest privilege roles in HRMS:

- What Super Admin and Admin can see and do
- How they differ from each other
- Which actions only these roles can perform (especially roster approval)

Access is based on the user’s **role**. Job designation is for display only and does not control permissions.

---

## 2. Access levels

| Level | Meaning |
|-------|---------|
| View | Can see data only (read-only) |
| Edit | Can create and update records |
| Manage | Full control (create, update, delete as applicable) |
| Approve | Can approve or reject workflow items (e.g. roster) |

---

## 3. Roles covered

| Role | Data visibility | Privilege summary |
|------|-----------------|-------------------|
| Super Admin | Entire organization | Highest access — full system control including report emails |
| Admin | Entire organization | Same day-to-day power as Super Admin, except report emails |

Both roles have **organization-wide** visibility for analytics, reports, users, projects, QC, KRA, and roster.

---

## 4. Feature access comparison

| Feature | Super Admin | Admin |
|---------|:-----------:|:-----:|
| Analytics / Overview | View | View |
| Billable report | View | View |
| QA hours report | View | View |
| User Monthly Goals | Edit | Edit |
| Project Monthly Report | View | View |
| KRA (view, notes, export) | View + Export | View + Export |
| Tracker Report | View | View |
| Agent Files & QC | View | View |
| QC Report Overview | View | View |
| QA Agent Audit | View | View |
| Manage Users (create / edit / delete) | Manage | Manage |
| Manage Projects / AFD / Category / Permissions | Manage | Manage |
| Roster — generate / edit / submit | Manage | Manage |
| Roster — **approve / reject** | Approve | Approve |
| Roster — week lock | Manage | Manage |
| Roster — holiday master | Manage | Manage |
| Report emails | Manage | **No access** |
| Salary details | View | View |
| QC form / Entry screens | Allowed | Allowed |

---

## 5. Super Admin — detailed capabilities

**Highest access level in the system.**

### Can

- View all analytics, billable, QA hours, tracker, QC, and KRA data for the **entire organization**
- Edit User Monthly Goals for any team / agent (with filters as needed)
- Create, edit, and delete users
- Fully manage projects, AFD, categories, and permissions
- Full roster control:
  - Generate, edit, submit
  - **Approve / reject**
  - Lock weeks
  - Manage holiday master
- Manage **report email** settings
- View salary details

### Scope

- Entire organization — no team lock

---

## 6. Admin — detailed capabilities

**Same as Super Admin for day-to-day operations**, with one difference:

| Area | Admin vs Super Admin |
|------|----------------------|
| Report emails | Admin **cannot** manage report emails |
| Everything else listed above | **Same** as Super Admin |

Admin **can**:

- Approve / reject roster
- Lock roster weeks
- Manage holiday settings
- Manage users and projects
- View salary details
- Access all org-wide reports and QC / KRA surfaces

---

## 7. Privileged actions (Admin / Super Admin only)

These actions are **not** available to Project Manager, Assistant Manager, Team Leader, QA, or Agent:

1. **Approve or reject roster** submissions  
2. **Lock roster weeks**  
3. **Manage holiday master**  
4. **Manage report emails** (Super Admin only)  

Project Manager may see org-wide data and edit roster requests, but **cannot** approve roster. See the operational RBAC document for that role.

---

## 8. Important rules

1. Assign Super Admin / Admin only to trusted system owners — these roles can change users, projects, and approvals across the company.
2. Prefer **Admin** for operational system owners who do not need report-email configuration; use **Super Admin** when report-email management is required.
3. Creating a user as Admin or Super Admin immediately grants organization-wide control — choose carefully.
4. Roster approval must never be expected from PM / AM / Team Leader — only Admin or Super Admin.

---

## 9. Quick decision guide

| If you want someone to… | Assign |
|-------------------------|--------|
| Full system control including report emails | Super Admin |
| Full system control without report emails | Admin |
| Org-wide reports + manage users/projects, but **no** roster approve | Project Manager (see operational RBAC doc) |
| Team-only goals / roster edit, no user management | Assistant Manager (see operational RBAC doc) |
