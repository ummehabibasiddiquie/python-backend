# HRMS — Full System Role-Based Workflow

**Document type:** End-to-end workflow reference for managers  
**System:** HRMS  
**Date:** 18 September 2026  
**Audience:** Managers, supervisors, QA leads  

> **Admin & Super Admin** privileged actions (roster approve, week lock, holiday master, report emails) are in a **separate document**.  
> This guide covers **where** each operational role works and **what** they can do.

---

## 1. How to read this document

| Column / term | Meaning |
|---------------|---------|
| **From where** | Menu path in the application (Header → screen → action) |
| **What they can do** | View, Edit, Submit, Export, Manage |
| **Scope** | Self only · Team · Assigned agents · Entire organization |

**Roles in this document**

| Role | Lands on after login | Data they usually see |
|------|----------------------|------------------------|
| Project Manager | Dashboard | Entire organization |
| Assistant Manager | Dashboard | Own team / assigned agents |
| Assistant Team Leader | Dashboard | Own team only |
| QA | Dashboard | Agents assigned to them (+ own) |
| Agent | Tracker screen | Own data only |

---

## 2. End-to-end business workflows

### 2.1 Daily work tracking

```
Agent
  Header → Tracker
  → Enter project, task, hours, files
  → Submit
        ↓
Managers / QA see the same work in:
  Header → Tracker Report
  Analytics → Billable Report
  Header → Agent Files & QC Report  (PM, QA; not Team Leader)
```

| Role | From where | What they can do |
|------|------------|------------------|
| Agent | Header → **Tracker** | Create / edit / submit **own** daily entries |
| Project Manager | Header → **Tracker Report** | View / filter / export — all org |
| Assistant Manager | Header → **Tracker Report** | View / filter / export — assigned / team |
| Team Leader | Header → **Tracker Report** | View — team only |
| QA | Header → **Tracker Report** | View — assigned agents |

---

### 2.2 User Monthly Goals ↔ Roster

```
Manage → Roster Management → Generate (PM / AM / Admin)
  → Creates monthly target + working days
        ↓
Analytics → User Monthly Goal / Report
  → PM / AM: edit Extra Assign Hours → Save / Submit All → Export
  → Team Leader: view only
        ↓
Roster calendar stays aligned with goal hours for the month
```

| Role | From where | What they can do | Scope |
|------|------------|------------------|-------|
| Project Manager | Analytics → **User Monthly Report** | Edit Extra Hours, Submit, Export | All org (+ team filter) |
| Assistant Manager | Analytics → **User Monthly Goal** | Edit Extra Hours, Submit, Export | **Own team only** (locked) |
| Team Leader | Analytics → **User Monthly Goal** | View only | Team |
| Agent / QA | — | No this screen | — |

---

### 2.3 Roster change → approval

```
PM / AM / Team Leader
  Manage → Roster Management → Roster Calendar
  → Edit days / leave (draft)
  → Submit for approval
  → Track under My Submissions
        ↓
Admin / Super Admin ONLY  (separate privileged doc)
  Manage → Roster Management → Approval Queue
  → Approve or Reject
        ↓
Agent / QA
  Header → My Roster
  → View only (pending changes may show as awaiting approval)
```

| Role | From where | What they can do |
|------|------------|------------------|
| Project Manager | Manage → **Roster Management** | Edit, Generate, Submit for approval — all org |
| Assistant Manager | Manage → **Roster Management** | Edit, Generate, Submit — **team locked** |
| Team Leader | Manage → **Roster Management** | Edit, Submit — team (**only write area** for TL) |
| Agent / QA | Header → **My Roster** | View own roster only |
| Admin / Super Admin | Approval Queue | **Approve / Reject** (not in this doc’s role set) |

---

### 2.4 QC / Agent Files

```
PM / QA
  Header → Agent Files & QC Report
  → Agent's Tracker File / Rework
  → Open QC Form
        ↓
Results also appear in:
  Header → QC Report Overview   (PM, AM)
  Header → QA Agent Audit       (PM, AM; QA limited)
```

| Role | From where | What they can do |
|------|------------|------------------|
| Project Manager | Agent Files & QC · QC Overview · QA Audit | View / export; open QC Form |
| Assistant Manager | QC Overview · QA Audit | View / export (scoped) |
| QA | Agent Files & QC · My Report | QC on assigned agents; enter **own** QA hours |
| Team Leader / Agent | — | No Agent Files / QC Overview in normal nav |

---

### 2.5 KRA

```
Any role with KRA tab
  Analytics → KRA
  → Select month and agent (list is role-scoped)
  → View scores
  → Save notes (managers/QA in scope; not Agent)
  → Export Excel
```

| Role | Scope on KRA |
|------|----------------|
| Project Manager | All agents |
| Assistant Manager | Assigned agents |
| Team Leader | Team |
| QA | Assigned agents |
| Agent | Self only |

---

## 3. Role workflows — screen by screen

### 3.1 Project Manager

**Login → Dashboard**

**Header:** Analytics · Tracker Report · Agent Files & QC Report · QC Report Overview · QA Agent Audit · Manage

| From where | What they can do | Scope |
|------------|------------------|-------|
| Analytics → Overview | View dashboard | All org |
| Analytics → Billable Report | View | All org |
| Analytics → QA Report | View / export | All org |
| Analytics → User Monthly Report | Edit Extra Hours, Submit, Export | All org |
| Analytics → Project Monthly Report | View | All org |
| Analytics → KRA | View, notes, Export | All org |
| Tracker Report | View / filter / export | All org |
| Agent Files & QC Report | View files; open QC Form | All org |
| QC Report Overview | View / export | All org |
| QA Agent Audit | Full audit view | All org |
| Manage → User Management | Create / edit users | All org |
| Manage → Projects & Targets / AFD / Category / Permissions | Manage | Org |
| Manage → Roster Management | Edit, Generate, Submit for approval | All org |

**Cannot:** Approve roster, lock weeks, edit holiday master, manage report emails.

---

### 3.2 Assistant Manager

**Login → Dashboard**

**Header:** Analytics · Tracker Report · QC Report Overview · QA Agent Audit · Manage

| From where | What they can do | Scope |
|------------|------------------|-------|
| Analytics → Overview / Billable / QA Report / Project Monthly | View | Assigned / team |
| Analytics → User Monthly Goal | Edit Extra Hours, Submit, Export | **Own team only** |
| Analytics → KRA | View, notes, Export | Assigned |
| Tracker Report | View / export | Assigned / team |
| QC Report Overview / QA Agent Audit | View / export | Scoped |
| Manage → Projects / AFD / Category / Permissions | Manage | Own / assigned |
| Manage → Roster Management | Edit, Generate, Submit | **Team locked** |
| Manage → User Management | Not available | — |

**Cannot:** Manage users, approve roster, lock weeks.

---

### 3.3 Assistant Team Leader (Team Leader)

**Login → Dashboard**

**Header:** Analytics · Tracker Report · Manage

| From where | What they can do | Scope |
|------------|------------------|-------|
| Analytics → Overview / Billable / User Monthly Goal / Project Monthly / KRA | **View only** | Team |
| Tracker Report | View | Team |
| Manage → Roster Management | **Edit + Submit for approval** | Team |
| Manage → Users / Projects / other manage tabs | Hidden | — |

**Cannot:** Edit monthly goal hours, manage users/projects, QC Overview / Agent Files (normal nav), approve roster.  
**Note:** Outside roster, this role is treated as **read-only**.

---

### 3.4 QA

**Login → Dashboard**

**Header:** Analytics · My Report · My Roster · Tracker Report · Agent Files & QC Report

| From where | What they can do | Scope |
|------------|------------------|-------|
| Analytics → Overview / Agents Billable / Audit / KRA | View (KRA notes/export) | Assigned agents |
| My Report | Enter / edit **own** QA hours | Self |
| My Roster | View | Self |
| Tracker Report | View | Assigned |
| Agent Files & QC Report | Review files; QC Form | Assigned |
| Manage / Roster Management | Not available | — |

---

### 3.5 Agent

**Login → Tracker** (not Dashboard)

**Header:** Analytics · My Roster · Tracker · AI Evaluation

| From where | What they can do | Scope |
|------------|------------------|-------|
| Tracker | Create / edit / submit daily work | Self |
| Analytics → Overview | View own productivity | Self |
| Analytics → Billable & QC Report | View | Self |
| Analytics → KRA | View own KRA | Self |
| My Roster | View only | Self |
| AI Evaluation | Run evaluation | Self |
| Manage / Tracker Report / QC Overview | Not available | — |

---

## 4. Navigation map (what appears in the header)

| Header item | PM | AM | Team Leader | QA | Agent |
|-------------|:--:|:--:|:-----------:|:--:|:-----:|
| Analytics | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tracker Report | ✓ | ✓ | ✓ | ✓ | — |
| Agent Files & QC Report | ✓ | — | — | ✓ | — |
| QC Report Overview | ✓ | ✓ | — | — | — |
| QA Agent Audit | ✓ | ✓ | — | Limited | — |
| Manage | ✓ | ✓ | ✓ (roster) | — | — |
| My Report | — | — | — | ✓ | — |
| My Roster | — | — | — | ✓ | ✓ |
| Tracker | — | — | — | — | ✓ |
| AI Evaluation | — | — | — | — | ✓ |

---

## 5. Who starts vs who finishes key processes

| Process | Started by | Finished / approved by |
|---------|------------|-------------------------|
| Daily tracker entry | Agent | Auto visible in manager reports |
| Monthly goals Extra Hours | PM / AM (TL view only) | Saved / submitted on Goals screen |
| Roster generate | PM / AM / Admin | Creates goal baseline |
| Roster day change | PM / AM / Team Leader | **Admin / Super Admin** approve |
| QC scoring | QA / PM via QC Form | Visible in QC Overview / Audit |
| KRA export | Any role with KRA tab | Download on same screen |

---

## 6. Quick “where do I go?” guide

| I need to… | Go here | Role |
|------------|---------|------|
| Enter today’s work | Header → **Tracker** | Agent |
| See team hours / productivity | Analytics → **Billable Report** | PM / AM / TL / QA |
| Set Extra Assign Hours | Analytics → **User Monthly Goal/Report** | PM / AM |
| Change roster days | Manage → **Roster Management** | PM / AM / TL |
| Approve roster | Manage → **Approval Queue** | Admin / Super Admin only |
| Score QC on a file | Agent Files → **QC Form** | PM / QA |
| Enter my QA hours | Header → **My Report** | QA |
| Download KRA Excel | Analytics → **KRA** → Export | PM / AM / TL / QA / Agent (own) |
| See my shift plan | Header → **My Roster** | Agent / QA |

---

## 7. Related documents

| Document | Use for |
|----------|---------|
| **HRMS Role-Based Access Control** | Feature access matrix (View / Edit / Manage) for operational roles |
| **Admin & Super Admin Access Control** | Privileged actions and Admin vs Super Admin differences |
| **This document** | Full workflow — **what** + **from where** |
