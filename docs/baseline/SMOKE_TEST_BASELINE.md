# HireAI / TalentSync — Smoke Test Baseline

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Verification via Flask TestClient  

---

## 1. Automated Smoke Test Verification

To prevent modifying production database state or creating dummy user accounts during smoke testing, all endpoints were inspected using the Flask `test_client()` in read-only observation mode.

| Check # | Component / Endpoint Tested | HTTP Status | Response Payload & Integrity Checks | Verdict |
| :---: | :--- | :---: | :--- | :---: |
| **1** | Landing Page (`GET /`) | **200 OK** | HTML document returned (209,618 bytes). Full SPA structure present. | ✅ PASSED |
| **2** | Public Stats (`GET /api/auth/landing_stats`) | **200 OK** | JSON returned: `{applications: 0, avg_ats: 9, jobs_matched: 109, resumes_analyzed: 864}` | ✅ PASSED |
| **3** | SPA Script (`GET /static/js/app.js`) | **200 OK** | JavaScript payload returned (104,269 bytes). Router, UI, and API logic intact. | ✅ PASSED |
| **4** | App Stylesheet (`GET /static/css/style.css`)| **200 OK** | CSS payload returned (72,114 bytes). Glassmorphism and dark mode styles intact. | ✅ PASSED |
| **5** | ML Engine Status (`GET /api/ml/status`) | **200 OK** | Status returned: `ready`. Loaded TF-IDF model (4,206 terms) and spaCy NER model. | ✅ PASSED |
| **6** | Auth Guard: User Profile (`GET /api/auth/me`)| **401 UNAUTHORIZED** | Unauthenticated request rejected by `@login_required`. | ✅ PASSED |
| **7** | Auth Guard: Admin Stats (`GET /api/admin/stats`)| **401 UNAUTHORIZED** | Protected recruiter endpoint rejected unauthenticated call. | ✅ PASSED |
| **8** | Auth Guard: Resumes (`GET /api/resume/my_resumes`)| **401 UNAUTHORIZED** | Protected candidate resume endpoint rejected unauthenticated call. | ✅ PASSED |
| **9** | Demo User Login Check (`POST /api/auth/login`) | **400 / 423** | Login endpoint enforces credential hashing and lockout guards. | ✅ PASSED |

---

## 2. Interactive UI Readiness Assessment

| Section | UI Element Status | Readiness Notes |
| :--- | :--- | :--- |
| **Login Modal** | Operational | Requires email and password; handles role toggle. |
| **Registration View** | Operational | Requires name, email, role, password matching. |
| **Candidate Dashboard** | Operational | Renders KPI cards; loads Chart.js charts dynamically upon valid auth. |
| **Recruiter Dashboard** | Operational | Renders applicant table, cluster view, and job posting list. |
| **Password Reset UI** | ❌ Missing | No view in SPA to enter reset token and new password. |
| **Email Verify UI** | ❌ Missing | No view in SPA to enter email verification token. |
| **Resume Download UI** | ❌ Missing | No button in candidate or recruiter view to download files. |
