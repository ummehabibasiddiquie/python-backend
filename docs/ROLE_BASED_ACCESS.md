# HRMS Role-Based Access Control (RBAC)

**Document type:** Access control reference for managers  
**System:** HRMS (Human Resource Management System)  
**Audience:** Project Managers, Assistant Managers, Team Leaders, QA leads, and team supervisors  
**Date:** 18 September 2026

> **Note:** Super Admin and Admin capabilities are documented separately in  
> **Admin & Super Admin Access Control** (`ADMIN_SUPER_ADMIN_ACCESS.md` / matching PDF).  
> This document covers operational roles only.

---

## 1. Purpose

This document explains what each **operational** HRMS role can see and do so managers can:

- Assign the correct role when creating or changing users
- Understand team vs organization visibility
- Align team structure (team lead, assistant manager, QA assignment) with system permissions

Access is based on the user’s **role**. Job designation is for display only and does not control permissions.

---

## 2. Access levels

| Level | Meaning |
|-------|---------|
| No access | Feature is not available for this role |
| View | Can see data only (read-only) |
| Edit | Can create and update records |
| Manage | Full control (create, update, delete as applicable) |
| Approve | Can approve or reject workflow items (e.g. roster) — **Admin / Super Admin only** (see separate doc) |

---

## 3. Roles and data visibility (this document)

| Role | What data they can see |
|------|-------------------------|
| Project Manager | Entire organization |
| Assistant Manager | Own team / assigned agents |
| Assistant Team Leader | Own team only |
| QA | Agents assigned to them (+ their own data) |
| Agent | Own data only |

**Additional:** Finance / HR users may see salary and incentives where configured.

---

## 4. Feature access matrix

| Feature | Project Manager | Assistant Manager | Team Leader | QA | Agent |
|---------|:---------------:|:-----------------:|:-----------:|:--:|:-----:|
| Analytics / Overview | View | View | View | View | View |
| Billable report | View | View | View | View | View (own) |
| QA hours report | View | View | — | — | — |
| User Monthly Goals | Edit | Edit (team) | View | — | — |
| Project Monthly Report | View | View | View | — | — |
| KRA | View + Export | View (scoped) | View (team) | View (scoped) | View (own) |
| Tracker Report | View | View | View | View | — |
| Agent Files & QC | View | View | — | View | — |
| QC Report Overview | View | View | — | — | — |
| QA Agent Audit | View | View | — | Limited | — |
| Manage Users | Manage | — | — | — | — |
| Manage Projects | Manage | Manage | — | — | — |
| Roster Management | Edit | Edit (team) | Edit (team) | — | — |
| Roster Approve / Reject | — | — | — | — | — |
| My Roster | — | — | — | View | View |
| Daily Tracker (Agent app) | — | — | — | — | Edit (own) |
| AI Evaluation | — | — | — | — | Yes |
| Salary details | View | — | — | — | — |

**—** = No access  
Roster **approve / reject** is Admin and Super Admin only (separate document).

---

## 5. Role-by-role details

### 5.1 Project Manager

**Organization-wide visibility** for most reports.

**Can**

- View all analytics, tracker, QC, and KRA reports
- Edit User Monthly Goals
- Manage users and projects
- Edit and submit roster changes
- View salary details

**Cannot**

- Approve or reject roster
- Lock roster weeks / manage holiday master
- Manage report emails

---

### 5.2 Assistant Manager

**Team / assignment scoped.**

**Can**

- View analytics and reports for assigned agents
- Edit User Monthly Goals for **their own team only** (team is locked in the UI)
- Manage projects (assigned / own)
- Edit and submit roster for their team

**Cannot**

- Manage users
- Approve roster
- See organization-wide data outside their assignment / team

---

### 5.3 Assistant Team Leader (Team Leader)

**Mostly view-only**, with one important exception.

**Can**

- View team analytics, billable, monthly reports, KRA, and tracker report
- **Edit and submit roster** for their team

**Cannot**

- Edit User Monthly Goals hours
- Manage users or projects
- Approve roster
- Access QC overview / agent files modules typically shown to managers
- Make other write changes (system treats them as read-only outside roster)

---

### 5.4 QA

**Scoped to agents assigned to them.**

**Can**

- View analytics, billable, audit, and KRA for assigned agents
- Maintain own QA hours (My Report)
- View own roster
- View Tracker Report and Agent Files & QC for assigned agents
- Use QC form

**Cannot**

- Manage users, projects, or roster administration

---

### 5.5 Agent

**Self-service role.**

**Can**

- Enter and edit **own** daily tracker
- View own analytics, billable & QC, and KRA
- View own roster
- Use AI Evaluation / agent project screens

**Cannot**

- See other agents’ data
- Access Manage, roster management, or org-level reports

Default landing page after login: Agent Tracker (not the manager dashboard).

---

## 6. Important business rules

1. **Roster approval** is not available to roles in this document — only Admin / Super Admin (see separate doc).
2. **Project Manager** can see org-wide data but cannot approve roster.
3. **Assistant Manager** is locked to their team for monthly goals and roster filters.
4. **Team Leader** is view-only except roster edit/submit.
5. **Agents** and **QA** use “My Roster” (view only), not Roster Management.
6. Creating a user with the wrong role will immediately change what they can see and do — choose roles carefully.

---

## 7. Quick decision guide

| If you want someone to… | Assign this role |
|-------------------------|------------------|
| See all teams/reports, manage users/projects, but not approve roster | Project Manager |
| Manage one team’s goals, projects, and roster (no user management) | Assistant Manager |
| View team reports and update roster only | Assistant Team Leader |
| Review QC / assigned agents and enter QA hours | QA |
| Enter daily work and view own reports only | Agent |
| Full system control / roster approval | See **Admin & Super Admin** document |
