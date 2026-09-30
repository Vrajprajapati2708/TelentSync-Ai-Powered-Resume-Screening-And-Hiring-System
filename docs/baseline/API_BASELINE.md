# HireAI / TalentSync — Complete API Baseline & Route Inventory

**Generated**: 2026-09-02  
**Phase**: Phase 0 — Baseline & System Freeze  
**Mode**: Read-Only Audit  

---

## 1. Complete REST API Route Inventory

| Method | Endpoint Route | File & Handler | Auth Required | Role | Purpose & Payload |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `POST` | `/api/auth/login` | `auth_routes.py:login` | No | Any | User login `{email, password}`. Returns 200 or 423 (Locked). |
| `POST` | `/api/auth/register` | `auth_routes.py:register` | No | Any | Candidate/HR registration `{name, email, password, role}`. |
| `POST` | `/api/auth/verify_email` | `auth_routes.py:verify_email` | No | Any | Verify registration `{token}`. |
| `POST` | `/api/auth/resend_verification`| `auth_routes.py:resend_verification` | No | Any | Re-issue verification token `{email}`. |
| `POST` | `/api/auth/forgot_password`| `auth_routes.py:forgot_password` | No | Any | Generate reset token `{email}`. |
| `POST` | `/api/auth/reset_password` | `auth_routes.py:reset_password` | No | Any | Set new password `{token, new_password}`. |
| `POST` | `/api/auth/logout` | `auth_routes.py:logout` | Yes | Any | Clear session cookie. |
| `GET` | `/api/auth/me` | `auth_routes.py:get_me` | Yes | Any | Return logged-in user profile dictionary. |
| `POST` | `/api/auth/change_password`| `auth_routes.py:change_password`| Yes | Any | Change password `{current_password, new_password}`. |
| `GET` | `/api/auth/landing_stats` | `auth_routes.py:landing_stats` | No | Public | Global platform metrics for landing hero. |
| `POST` | `/api/upload_resume` | `resume_routes.py:upload_resume`| Yes | Candidate | Upload resume file (multipart `resume`). |
| `GET` | `/api/resume/download/<id>`| `resume_routes.py:download_resume`| Yes | Owner/HR | Download original uploaded resume binary. |
| `GET` | `/api/resume/my_resumes` | `resume_routes.py:get_my_resumes`| Yes | Candidate | List past uploaded resumes with ATS score. |
| `POST` | `/api/match_jobs` | `resume_routes.py:match_jobs` | Yes | Candidate | Compute TF-IDF & Adzuna matches for `{skills}`. |
| `POST` | `/api/apply` | `resume_routes.py:apply_job` | Yes | Candidate | Submit job application `{job_id, match_score}`. |
| `GET` | `/api/candidate/stats/<id>`| `user_routes.py:candidate_stats`| Yes | Owner | Radar charts, market trends, daily view telemetry. |
| `GET/PUT`| `/api/users/<id>/profile` | `user_routes.py:user_profile` | Yes | Owner | Get or update profile bio and contact details. |
| `GET` | `/api/notifications/<id>` | `user_routes.py:get_notifications`| Yes | Owner | Fetch user alerts list. |
| `POST` | `/api/notifications/<id>/read`| `user_routes.py:read_notifications`| Yes| Owner | Mark all notifications as read. |
| `GET` | `/api/admin/stats` | `admin_routes.py:admin_stats` | Yes | HR | Recruiter dashboard KPIs and ATS histogram. |
| `GET` | `/api/admin/candidates` | `admin_routes.py:get_candidates` | Yes | HR | All applicants with Outlier flags and Cluster tags. |
| `GET` | `/api/admin/clusters` | `admin_routes.py:get_clusters` | Yes | HR | Candidates grouped by KMeans skill cluster. |
| `GET` | `/api/admin/outliers` | `admin_routes.py:get_outliers` | Yes | HR | Candidates flagged by IsolationForest / rules. |
| `POST` | `/api/admin/update_status` | `admin_routes.py:update_status` | Yes | HR | Update status `{app_id, status}`. |
| `GET/POST`| `/api/admin/jobs` | `admin_routes.py:jobs_api` | Yes | HR | List all jobs or create new job posting. |
| `GET/PUT`| `/api/admin/jobs/<id>` | `admin_routes.py:job_detail` | Yes | HR | View or edit job description details. |
| `DELETE`| `/api/admin/delete_job/<id>`| `admin_routes.py:delete_job` | Yes | HR | Delete job posting. |
| `GET` | `/api/ml/status` | `ml_routes.py:ml_status` | No | Public | ML pipeline health, vocab size, and model state. |
| `POST` | `/api/ml/train` | `ml_routes.py:trigger_training` | Yes | HR | Asynchronously trigger pipeline retraining. |
| `POST` | `/api/ml/pipeline` | `ml_routes.py:run_pipeline` | No | Public | Run full inference on raw text. |
| `GET` | `/api/v1/jobs/search` | `jobs_routes.py:search_jobs` | Optional| Any | Aggregated multi-provider job search with AI ranking. |

---

## 2. Identified Route Inconsistencies & Gaps

1. **Missing Candidate Talent Pool Route**:
   `/api/admin/candidates` queries `applications` table. Candidates who register and upload resumes without submitting a job application are invisible to recruiters.
2. **External Job Apply Crash**:
   `/api/apply` queries `SELECT id FROM jobs WHERE id=?`. Applying to Adzuna external jobs with string IDs returns HTTP 404.
3. **Missing Resume Intelligence Route**:
   No standalone endpoint exists for retrieving the canonical `structured_json` for a specific resume.
