# HireAI / TalentSync — Database Baseline & Inventory

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Database Discovery Summary

An exhaustive filesystem search located **two** SQLite database files named `talentsync.db`:

```text
Database #1 (ACTIVE RUNTIME DATABASE):
  Path:        V:\HireAI_Website-main (2)\AI-Resume-Screening-System\talentsync.db
  Size:        1,306,624 bytes (~1.3 MB)
  SHA-256:     f0695b8642437b2814f38499e7cb6be5706f05121d1e27e5123a437d621c3053
  Last Mod:    2026-09-02 17:34:52
  Status:      ACTIVE — Actively written to by tests and runtime controllers.

Database #2 (STALE / HISTORICAL SNAPSHOT):
  Path:        V:\HireAI_Website-main (2)\talentsync.db
  Size:        151,552 bytes (~151 KB)
  SHA-256:     8b0428db63554df8d72e2429f1dbe07a75592d5ef4baee44b72f00a763fc1a3c
  Last Mod:    2026-08-03 12:31:16
  Status:      STALE — Root snapshot prior to Phase 0 / Phase 1 implementation.
```

---

## 2. Table-by-Table Inventory & Row Counts

| Table Name | Active DB (`AI-Resume-Screening-System`) | Stale DB (`Outer Root`) | Schema Classification |
| :--- | :---: | :---: | :--- |
| **`users`** | **1,134 rows** | 12 rows | Core IAM, candidate profiles, ATS scores |
| **`jobs`** | **109 rows** | 10 rows | Internal job vacancy postings |
| **`applications`** | **0 rows** | 18 rows | Candidate job application submissions |
| **`notifications`** | **1,133 rows** | 0 rows | User platform alerts and notifications |
| **`email_verification_tokens`** | **1,132 rows** | 0 rows | Phase 0 verification tokens |
| **`password_reset_tokens`** | **53 rows** | 0 rows | Phase 0 password reset tokens (15m expiry) |
| **`login_attempts`** | **622 rows** | 0 rows | Phase 0 account lockout tracking |
| **`resumes`** | **192 rows** | 0 rows | Phase 1 metadata & Resume Intelligence JSON |
| **`external_jobs`** | 0 rows | 0 rows | Adzuna external jobs cache table |
| **`companies`** | 0 rows | 0 rows | Company logo and profile directory |
| **`provider_cache`** | 0 rows | 0 rows | Job aggregator HTTP response cache |
| **`provider_health`** | 0 rows | 0 rows | External provider uptime tracker |
| **`saved_jobs`** | 0 rows | 0 rows | Candidate bookmarked jobs |
| **`search_history`** | 0 rows | 0 rows | Search telemetry |
| **`job_alerts`** | 0 rows | 0 rows | Saved search notifications |
| **`application_status`** | 0 rows | 0 rows | Extended status tracking |
| **`recommendation_history`**| 0 rows | 0 rows | Historical match scores |
| **`sqlite_sequence`** | 7 rows | 3 rows | Internal SQLite autoincrement metadata |

---

## 3. Database Backup & Cryptographic Verification

A verified read-only binary snapshot of the active database was taken:

- **Original DB**: `V:\HireAI_Website-main (2)\AI-Resume-Screening-System\talentsync.db`
  - SHA-256: `f0695b8642437b2814f38499e7cb6be5706f05121d1e27e5123a437d621c3053`
- **Backup DB**: `V:\HireAI_Website-main (2)\docs\baseline\backups\talentsync_baseline_20260902_182512.db`
  - SHA-256: `f0695b8642437b2814f38499e7cb6be5706f05121d1e27e5123a437d621c3053`
- **Integrity Status**: **100% VERIFIED BIT-FOR-BIT MATCH** (`MATCH: True`).
