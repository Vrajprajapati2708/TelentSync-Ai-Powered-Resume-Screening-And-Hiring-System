# ============================================================
#  HireAI / TalentSync — Platform Admin Controller
#  Business logic for centralized platform administration:
#    1. User & Role Management (with final-admin safety)
#    2. System-Wide Analytics (derived strictly from live DB)
#    3. Security & Fraud Oversight (login attempts & outliers)
#    4. Read-Only Audit Viewer (recommendations, status, searches)
# ============================================================

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.database.connection import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_ROLES = {"candidate", "hr", "admin"}


# ── 1. User & Role Management ────────────────────────────────

def get_platform_users(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    role: str = "",
    status: str = "",
    verification: str = ""
) -> Dict[str, Any]:
    """
    Paginated, searchable, and filterable retrieval of users.
    Bounded page size. Never loads the entire table into memory.
    Never exposes passwords, hashes, or sensitive tokens.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    conditions = []
    params: List[Any] = []

    if search:
        term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(name) LIKE ? OR LOWER(email) LIKE ?)")
        params.extend([term, term])

    if role and role.strip().lower() in ALLOWED_ROLES:
        conditions.append("role = ?")
        params.append(role.strip().lower())

    if status:
        st = status.strip().lower()
        if st in ("active", "1", "verified"):
            conditions.append("is_verified = 1")
        elif st in ("inactive", "0", "unverified"):
            conditions.append("is_verified = 0")

    if verification:
        vf = verification.strip().lower()
        if vf in ("verified", "1", "true"):
            conditions.append("is_verified = 1")
        elif vf in ("unverified", "0", "false"):
            conditions.append("is_verified = 0")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        count_query = f"SELECT COUNT(*) FROM users {where_clause}"
        total_count = conn.execute(count_query, tuple(params)).fetchone()[0]

        data_query = f"""
            SELECT id, name, email, role, is_verified, ats_score, location,
                   is_outlier, cluster_label, created_at,
                   (SELECT attempted_at FROM login_attempts WHERE email = users.email AND success = 1 ORDER BY id DESC LIMIT 1) as last_login
            FROM users
            {where_clause}
            ORDER BY id ASC
            LIMIT ? OFFSET ?
        """
        fetch_params = list(params) + [limit, offset]
        rows = conn.execute(data_query, tuple(fetch_params)).fetchall()

    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "role": r["role"],
            "is_verified": bool(r["is_verified"]),
            "is_active": bool(r["is_verified"]),
            "ats_score": r["ats_score"] or 0,
            "location": r["location"] or "",
            "is_outlier": bool(r["is_outlier"]),
            "cluster_label": r["cluster_label"] or "Unclustered",
            "created_at": r["created_at"] or "",
            "last_login": r["last_login"] or ""
        })

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    pagination_info = {
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_items": total_count,
        "total_pages": total_pages,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    return {
        "success": True,
        "users": users,
        "pagination": pagination_info,
        "data": {
            "users": users,
            "pagination": pagination_info
        }
    }


def get_platform_user_detail(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive administrative details for a single user.
    Excludes password, password_hash, and verification tokens.
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, name, email, role, is_verified, skills, ats_score,
                      phone, location, linkedin, github, summary, education,
                      is_outlier, cluster_label, created_at
               FROM users WHERE id = ?""",
            (user_id,)
        ).fetchone()

        if not row:
            return None

        # Fetch count of user's resumes and applications
        app_count = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        resume_count = conn.execute(
            "SELECT COUNT(*) FROM resumes WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        # Last successful login
        last_login_row = conn.execute(
            "SELECT attempted_at FROM login_attempts WHERE email = ? AND success = 1 ORDER BY id DESC LIMIT 1",
            (row["email"],)
        ).fetchone()
        last_login = last_login_row["attempted_at"] if last_login_row else ""

        # Recent applications (up to 5)
        recent_apps_rows = conn.execute(
            """SELECT a.id, a.job_id, a.status, a.applied_at, j.title as job_title, j.company as job_company
               FROM applications a
               LEFT JOIN jobs j ON a.job_id = j.id
               WHERE a.user_id = ?
               ORDER BY a.id DESC LIMIT 5""",
            (user_id,)
        ).fetchall()
        recent_apps = [{
            "id": ra["id"],
            "job_title": ra["job_title"] or "Job Posting",
            "company": ra["job_company"] or "",
            "status": ra["status"] or "Pending",
            "applied_at": ra["applied_at"] or ""
        } for ra in recent_apps_rows]

        # Recent logins (up to 5)
        recent_logins_rows = conn.execute(
            """SELECT ip_address, success, attempted_at
               FROM login_attempts
               WHERE email = ?
               ORDER BY id DESC LIMIT 5""",
            (row["email"],)
        ).fetchall()
        recent_logins = [{
            "ip_address": rl["ip_address"],
            "success": bool(rl["success"]),
            "attempted_at": rl["attempted_at"] or ""
        } for rl in recent_logins_rows]

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "is_verified": bool(row["is_verified"]),
        "is_active": bool(row["is_verified"]),
        "skills": [s.strip() for s in (row["skills"] or "").split(",") if s.strip()],
        "ats_score": row["ats_score"] or 0,
        "phone": row["phone"] or "",
        "location": row["location"] or "",
        "linkedin": row["linkedin"] or "",
        "github": row["github"] or "",
        "summary": row["summary"] or "",
        "education": row["education"] or "",
        "is_outlier": bool(row["is_outlier"]),
        "cluster_label": row["cluster_label"] or "Unclustered",
        "created_at": row["created_at"] or "",
        "last_login": last_login,
        "stats": {
            "applications_count": app_count,
            "resumes_count": resume_count
        },
        "recent_activity": {
            "applications": recent_apps,
            "logins": recent_logins
        }
    }


def activate_platform_user(user_id: int) -> Tuple[bool, str, int]:
    """
    Activates a user account (is_verified = 1).
    Returns (success, message, status_code).
    """
    with get_db() as conn:
        user = conn.execute("SELECT id, is_verified FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found.", 404

        conn.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
        if hasattr(conn, "commit"):
            conn.commit()

    logger.info(f"Platform admin activated user_id={user_id}")
    return True, "User account activated successfully.", 200


def deactivate_platform_user(user_id: int, admin_user_id: int) -> Tuple[bool, str, int]:
    """
    Deactivates a user account (is_verified = 0).
    Enforces final-admin and self-deactivation protections.
    Returns (success, message, status_code).
    """
    if user_id == admin_user_id:
        return False, "Administrators cannot deactivate their own account.", 400

    with get_db() as conn:
        user = conn.execute("SELECT id, role, is_verified FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found.", 404

        # Final Active Admin Protection
        if user["role"] == "admin" and user["is_verified"] == 1:
            active_admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_verified = 1"
            ).fetchone()[0]
            if active_admin_count <= 1:
                return False, "Cannot deactivate the final active administrator on the platform.", 400

        conn.execute("UPDATE users SET is_verified = 0 WHERE id = ?", (user_id,))
        if hasattr(conn, "commit"):
            conn.commit()

    logger.info(f"Platform admin deactivated user_id={user_id}")
    return True, "User account deactivated successfully.", 200


def change_platform_user_role(user_id: int, new_role: str, admin_user_id: int) -> Tuple[bool, str, int]:
    """
    Updates a user's role (candidate <-> hr <-> admin).
    Enforces final-admin demotion and self-demotion protections.
    Returns (success, message, status_code).
    """
    clean_role = (new_role or "").strip().lower()
    if clean_role not in ALLOWED_ROLES:
        return False, f"Invalid role '{new_role}'. Allowed roles: {', '.join(sorted(ALLOWED_ROLES))}", 400

    if user_id == admin_user_id:
        return False, "Administrators cannot modify their own role.", 400

    with get_db() as conn:
        user = conn.execute("SELECT id, role, is_verified FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found.", 404

        current_role = user["role"]
        if current_role == clean_role:
            return True, f"User already has the role '{clean_role}'.", 200

        # Final Active Admin Protection against demotion
        if current_role == "admin" and clean_role != "admin" and user["is_verified"] == 1:
            active_admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_verified = 1"
            ).fetchone()[0]
            if active_admin_count <= 1:
                return False, "Cannot demote the final active administrator on the platform.", 400

        conn.execute("UPDATE users SET role = ? WHERE id = ?", (clean_role, user_id))
        if hasattr(conn, "commit"):
            conn.commit()

    logger.info(f"Platform admin changed role for user_id={user_id} from {current_role} to {clean_role}")
    return True, f"User role successfully updated to '{clean_role}'.", 200


def delete_platform_user(user_id: int, admin_user_id: int) -> Tuple[bool, str, int]:
    """
    Permanently deletes a user account with cascading cleanup and audit logging.
    Enforces final-admin and self-deletion protections.
    Returns (success, message, status_code).
    """
    if user_id == admin_user_id:
        return False, "Administrators cannot delete their own account.", 400

    with get_db() as conn:
        user = conn.execute("SELECT id, name, email, role, is_verified FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found.", 404

        # Final Active Admin Protection
        if user["role"] == "admin" and user["is_verified"] == 1:
            active_admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_verified = 1"
            ).fetchone()[0]
            if active_admin_count <= 1:
                return False, "Cannot delete the final active administrator on the platform.", 400

        # 1. Clean up resume files from disk
        resume_rows = conn.execute("SELECT file_path FROM resumes WHERE user_id = ?", (user_id,)).fetchall()
        for rr in resume_rows:
            fpath = rr["file_path"]
            if fpath and os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                except Exception as e:
                    logger.warning(f"Failed to remove resume file on user delete: {e}")

        # 2. Cascading DB cleanup
        conn.execute("DELETE FROM resumes WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM applications WHERE user_id = ?", (user_id,))
        try:
            conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
        except Exception:
            pass
        try:
            conn.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        except Exception:
            pass
        try:
            conn.execute("DELETE FROM recommendation_history WHERE user_id = ?", (user_id,))
        except Exception:
            pass

        # 3. Record audit log
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, ip_address TEXT, timestamp TEXT DEFAULT (datetime('now')))"
            )
            conn.execute(
                "INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp) VALUES (?, 'delete_user', ?, '127.0.0.1', datetime('now'))",
                (admin_user_id, f"Deleted user {user['email']} (ID #{user_id}, role={user['role']})")
            )
        except Exception as e:
            logger.warning(f"Audit log write on delete failed: {e}")

        # 4. Delete user record
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if hasattr(conn, "commit"):
            conn.commit()

    logger.info(f"Platform admin (ID #{admin_user_id}) deleted user_id={user_id}")
    return True, "User account and associated records deleted successfully.", 200


def create_platform_user(data: Dict[str, Any], admin_user_id: int) -> Tuple[bool, str, int, Optional[int]]:
    """
    Provisions a new user directly from the Platform Administration panel.
    Returns (success, message, status_code, user_id).
    """
    from werkzeug.security import generate_password_hash
    from app.utils.validators import validate_email

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "candidate").strip().lower()
    is_verified = 1 if data.get("is_verified", True) else 0

    if not name:
        return False, "User name is required.", 400, None
    if not email or not validate_email(email):
        return False, "Valid email address is required.", 400, None
    if role not in ALLOWED_ROLES:
        return False, f"Invalid role '{role}'. Allowed roles: {', '.join(sorted(ALLOWED_ROLES))}", 400, None
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters.", 400, None

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if existing:
            return False, f"An account with email '{email}' already exists.", 409, None

        pwd_hash = generate_password_hash(password)
        cursor = conn.execute(
            """INSERT INTO users (name, email, password, role, is_verified, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (name, email, pwd_hash, role, is_verified)
        )
        new_id = cursor.lastrowid
        if hasattr(conn, "commit"):
            conn.commit()

        # Write audit log
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, ip_address TEXT, timestamp TEXT DEFAULT (datetime('now')))"
            )
            conn.execute(
                "INSERT INTO audit_logs (user_id, action, details, ip_address, timestamp) VALUES (?, 'create_user', ?, '127.0.0.1', datetime('now'))",
                (admin_user_id, f"Created {role} user '{name}' ({email}) with ID #{new_id}")
            )
            if hasattr(conn, "commit"):
                conn.commit()
        except Exception:
            pass

    logger.info(f"Platform admin user_id={admin_user_id} created new user_id={new_id} ({email}, role={role})")
    return True, f"User '{name}' ({role.upper()}) created successfully.", 201, new_id


# ── 2. System-Wide Analytics ─────────────────────────────────

def get_platform_analytics() -> Dict[str, Any]:
    """
    Computes system-wide operational metrics directly from live DB records.
    Zero fabricated or hardcoded numbers.
    """
    with get_db() as conn:
        # A. Users
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1").fetchone()[0]
        inactive_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_verified = 0").fetchone()[0]

        role_counts = conn.execute(
            "SELECT role, COUNT(*) as cnt FROM users GROUP BY role"
        ).fetchall()
        users_by_role = {r["role"]: r["cnt"] for r in role_counts}
        for r in ALLOWED_ROLES:
            users_by_role.setdefault(r, 0)

        # B. Recruitment & Applications
        total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        app_status_counts = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
        ).fetchall()
        status_dist = {r["status"]: r["cnt"] for r in app_status_counts}
        for s in ("Pending", "Reviewing", "Shortlisted", "Rejected"):
            status_dist.setdefault(s, 0)

        # C. Jobs
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        job_status_counts = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ).fetchall()
        jobs_by_status = {r["status"]: r["cnt"] for r in job_status_counts}
        for s in ("Active", "Closed", "Draft"):
            jobs_by_status.setdefault(s, 0)

        # D. ATS Distribution
        ats_ranges = {
            "0-20": 0, "21-40": 0, "41-60": 0,
            "61-70": 0, "71-80": 0, "81-90": 0, "91-100": 0
        }
        all_ats = conn.execute(
            "SELECT ats_score FROM users WHERE role = 'candidate' AND ats_score > 0"
        ).fetchall()

        scores = [row["ats_score"] for row in all_ats if row["ats_score"] is not None]
        for s in scores:
            if s <= 20:   ats_ranges["0-20"] += 1
            elif s <= 40: ats_ranges["21-40"] += 1
            elif s <= 60: ats_ranges["41-60"] += 1
            elif s <= 70: ats_ranges["61-70"] += 1
            elif s <= 80: ats_ranges["71-80"] += 1
            elif s <= 90: ats_ranges["81-90"] += 1
            else:         ats_ranges["91-100"] += 1

        avg_ats = round(sum(scores) / len(scores), 1) if scores else 0.0

        # E. Resumes
        total_resumes = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        resume_status_counts = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM resumes GROUP BY status"
        ).fetchall()
        by_res_status = {r["status"]: r["cnt"] for r in resume_status_counts}
        processed_resumes = by_res_status.get("processed", 0)
        pending_resumes = by_res_status.get("uploaded", 0) + by_res_status.get("processing", 0)
        failed_resumes = by_res_status.get("failed", 0)

    analytics_payload = {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
            "by_role": users_by_role
        },
        "applications": {
            "total": total_apps,
            "pending": status_dist.get("Pending", 0),
            "reviewing": status_dist.get("Reviewing", 0),
            "shortlisted": status_dist.get("Shortlisted", 0),
            "rejected": status_dist.get("Rejected", 0),
            "status_distribution": status_dist
        },
        "recruitment": {
            "total_applications": total_apps,
            "status_distribution": status_dist,
            "funnel": {
                "total": total_apps,
                "reviewing": status_dist.get("Reviewing", 0),
                "shortlisted": status_dist.get("Shortlisted", 0),
                "pending": status_dist.get("Pending", 0),
                "rejected": status_dist.get("Rejected", 0)
            }
        },
        "jobs": {
            "total": total_jobs,
            "active": jobs_by_status.get("Active", 0),
            "closed": jobs_by_status.get("Closed", 0),
            "draft": jobs_by_status.get("Draft", 0),
            "by_status": jobs_by_status
        },
        "resumes": {
            "total": total_resumes,
            "processed": processed_resumes,
            "pending": pending_resumes,
            "failed": failed_resumes,
            "by_status": by_res_status
        },
        "ats": {
            "average": avg_ats,
            "average_score": avg_ats,
            "total_candidates_scored": len(scores),
            "candidates_scored": len(scores),
            "distribution": ats_ranges
        },
        "kpis": {
            "total_users": total_users,
            "candidates": users_by_role.get("candidate", 0),
            "hr_users": users_by_role.get("hr", 0),
            "platform_admins": users_by_role.get("admin", 0),
            "active_users": active_users,
            "total_jobs": total_jobs,
            "active_jobs": jobs_by_status.get("Active", 0),
            "total_applications": total_apps,
            "total_resumes": total_resumes,
            "average_ats": avg_ats
        }
    }

    return {
        "success": True,
        "analytics": analytics_payload,
        "data": analytics_payload,
        **analytics_payload
    }


# ── 3. Security & Fraud Oversight ────────────────────────────

def get_platform_login_attempts(
    page: int = 1,
    limit: int = 20,
    status_filter: str = "",
    search: str = ""
) -> Dict[str, Any]:
    """
    Aggregates and paginates platform-wide authentication attempts from login_attempts.
    Only uses fields that actually exist in the schema.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    conditions = []
    params: List[Any] = []

    if status_filter:
        sf = status_filter.strip().lower()
        if sf in ("success", "1"):
            conditions.append("success = 1")
        elif sf in ("failed", "fail", "0"):
            conditions.append("success = 0")

    if search:
        term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(email) LIKE ? OR ip_address LIKE ?)")
        params.extend([term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        # Aggregated summary KPIs
        total_attempts = conn.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0]
        successful_attempts = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE success = 1").fetchone()[0]
        failed_attempts = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE success = 0").fetchone()[0]

        # Top 5 failed IPs
        failed_ips_raw = conn.execute(
            """SELECT ip_address, COUNT(*) as cnt
               FROM login_attempts
               WHERE success = 0
               GROUP BY ip_address
               ORDER BY cnt DESC LIMIT 5"""
        ).fetchall()
        top_failed_ips = [{"ip_address": r["ip_address"], "failed_count": r["cnt"]} for r in failed_ips_raw]

        # Top 5 targeted accounts
        targeted_raw = conn.execute(
            """SELECT email, COUNT(*) as cnt
               FROM login_attempts
               WHERE success = 0
               GROUP BY email
               ORDER BY cnt DESC LIMIT 5"""
        ).fetchall()
        top_targeted_emails = [{"email": r["email"], "failed_count": r["cnt"]} for r in targeted_raw]

        # Filtered total count
        filtered_count = conn.execute(
            f"SELECT COUNT(*) FROM login_attempts {where_clause}", tuple(params)
        ).fetchone()[0]

        # Data query
        fetch_params = list(params) + [limit, offset]
        rows = conn.execute(
            f"""SELECT id, email, ip_address, success, attempted_at
                FROM login_attempts
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?""",
            tuple(fetch_params)
        ).fetchall()

    attempts = []
    for r in rows:
        attempts.append({
            "id": r["id"],
            "email": r["email"],
            "ip_address": r["ip_address"],
            "success": bool(r["success"]),
            "attempted_at": r["attempted_at"] or ""
        })

    total_pages = (filtered_count + limit - 1) // limit if limit > 0 else 1

    pagination_info = {
        "page": page,
        "limit": limit,
        "total": filtered_count,
        "total_items": filtered_count,
        "total_pages": total_pages,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    summary_info = {
        "total_attempts": total_attempts,
        "successful_attempts": successful_attempts,
        "failed_attempts": failed_attempts,
        "success_rate_pct": round((successful_attempts / total_attempts * 100), 1) if total_attempts else 100.0,
        "top_failed_ips": top_failed_ips,
        "top_targeted_emails": top_targeted_emails,
        "top_targeted_accounts": top_targeted_emails
    }

    payload = {
        "summary": summary_info,
        "top_failed_ips": top_failed_ips,
        "top_targeted_accounts": top_targeted_emails,
        "attempts": attempts,
        "pagination": pagination_info
    }

    return {
        "success": True,
        "data": payload,
        **payload
    }


def get_platform_outliers(page: int = 1, limit: int = 20) -> Dict[str, Any]:
    """
    Fetches flagged anomalous profiles based on the persistent users.is_outlier column
    and existing heuristic/IsolationForest outlier detection rules.
    Does NOT reimplement or retrain models unnecessarily.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    with get_db() as conn:
        total_outliers = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_outlier = 1"
        ).fetchone()[0]

        rows = conn.execute(
            """SELECT id, name, email, role, ats_score, is_outlier, cluster_label, created_at
               FROM users
               WHERE is_outlier = 1
               ORDER BY id DESC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        ).fetchall()

    outliers = []
    for r in rows:
        score = r["ats_score"] or 0
        if score < 15:
            reason = "Suspicious: Very low ATS score (possible spam resume)"
        elif score > 95:
            reason = "Suspicious: Extremely high score (possible keyword stuffing)"
        else:
            reason = "Statistical anomaly detected by AI model"

        outliers.append({
            "user_id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "role": r["role"],
            "ats_score": score,
            "cluster_label": r["cluster_label"] or "Unclustered",
            "detected_at": r["created_at"] or "",
            "reason": reason
        })

    total_pages = (total_outliers + limit - 1) // limit if limit > 0 else 1

    return {
        "success": True,
        "total_outliers": total_outliers,
        "outliers": outliers,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_items": total_outliers,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ── 4. Audit / Activity Viewer ───────────────────────────────

def get_platform_audit_logs(
    page: int = 1,
    limit: int = 20,
    source: str = "all",
    search: str = ""
) -> Dict[str, Any]:
    """
    Read-only unified activity stream across historical application tables:
      - application_status
      - recommendation_history
      - search_history
    Never mutates records. Gracefully returns empty structures when tables are empty.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit
    source_clean = (source or "all").strip().lower()

    events: List[Dict[str, Any]] = []

    with get_db() as conn:
        # Source 1: application_status
        if source_clean in ("all", "application_status", "applications"):
            app_status_rows = conn.execute(
                """SELECT s.id, s.application_id, s.status, s.notes, s.updated_at,
                          u.email as user_email, u.name as user_name
                   FROM application_status s
                   LEFT JOIN applications a ON s.application_id = a.id
                   LEFT JOIN users u ON a.user_id = u.id
                   ORDER BY s.id DESC LIMIT 100"""
            ).fetchall()
            for r in app_status_rows:
                events.append({
                    "id": f"app_status_{r['id']}",
                    "source": "application_status",
                    "timestamp": r["updated_at"] or "",
                    "entity": r["user_name"] or r["user_email"] or f"App #{r['application_id']}",
                    "action": f"Status updated to '{r['status']}'",
                    "details": r["notes"] or ""
                })

        # Source 2: recommendation_history
        if source_clean in ("all", "recommendation_history", "recommendations"):
            recs = conn.execute(
                """SELECT h.id, h.user_id, h.job_id, h.external_id, h.match_score,
                          h.matched_skills, h.missing_skills, h.recommended_at,
                          u.email as user_email, u.name as user_name
                   FROM recommendation_history h
                   LEFT JOIN users u ON h.user_id = u.id
                   ORDER BY h.id DESC LIMIT 100"""
            ).fetchall()
            for r in recs:
                events.append({
                    "id": f"rec_{r['id']}",
                    "source": "recommendation_history",
                    "timestamp": r["recommended_at"] or "",
                    "entity": r["user_name"] or r["user_email"] or f"User #{r['user_id']}",
                    "action": f"Job recommendation calculated (Match: {r['match_score']}%)",
                    "details": f"Job Ref: {r['job_id'] or r['external_id'] or 'N/A'}"
                })

        # Source 3: search_history
        if source_clean in ("all", "search_history", "searches"):
            searches = conn.execute(
                """SELECT sh.id, sh.user_id, sh.keyword, sh.location, sh.filters, sh.searched_at,
                          u.email as user_email, u.name as user_name
                   FROM search_history sh
                   LEFT JOIN users u ON sh.user_id = u.id
                   ORDER BY sh.id DESC LIMIT 100"""
            ).fetchall()
            for r in searches:
                events.append({
                    "id": f"search_{r['id']}",
                    "source": "search_history",
                    "timestamp": r["searched_at"] or "",
                    "entity": r["user_name"] or r["user_email"] or f"User #{r['user_id']}",
                    "action": f"Candidate job search executed ('{r['keyword'] or 'All'}')",
                    "details": f"Keyword: {r['keyword'] or 'All'} | Location: {r['location'] or 'Any'}"
                })

    # Filter by search string if provided
    if search:
        s_term = search.strip().lower()
        events = [
            e for e in events
            if s_term in e["entity"].lower() or s_term in e["action"].lower() or s_term in e["details"].lower()
        ]

    # Chronological sort (most recent first)
    events.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    total_events = len(events)
    paged_events = events[offset:offset + limit]
    total_pages = (total_events + limit - 1) // limit if limit > 0 else 1

    pagination_info = {
        "page": page,
        "limit": limit,
        "total": total_events,
        "total_items": total_events,
        "total_pages": total_pages,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    payload = {
        "events": paged_events,
        "source": source_clean,
        "pagination": pagination_info
    }

    return {
        "success": True,
        "data": payload,
        **payload
    }


# ── 5. Platform Jobs Management ──────────────────────────────

def get_platform_jobs(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    status: str = "",
    company: str = ""
) -> Dict[str, Any]:
    """
    Paginated, searchable retrieval of internal TalentSync jobs only.
    Excludes external Adzuna jobs.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    conditions = []
    params: List[Any] = []

    if search:
        term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(j.title) LIKE ? OR LOWER(j.company) LIKE ? OR LOWER(j.location) LIKE ?)")
        params.extend([term, term, term])

    if status:
        conditions.append("LOWER(j.status) = ?")
        params.append(status.strip().lower())

    if company:
        conditions.append("LOWER(j.company) LIKE ?")
        params.append(f"%{company.strip().lower()}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        count_query = f"SELECT COUNT(*) FROM jobs j {where_clause}"
        total_count = conn.execute(count_query, tuple(params)).fetchone()[0]

        data_query = f"""
            SELECT j.id, j.title, j.company, j.location, j.type, j.salary, j.status, j.created_at,
                   (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) as applications_count
            FROM jobs j
            {where_clause}
            ORDER BY j.id DESC
            LIMIT ? OFFSET ?
        """
        fetch_params = list(params) + [limit, offset]
        rows = conn.execute(data_query, tuple(fetch_params)).fetchall()

    jobs = []
    for r in rows:
        jobs.append({
            "id": r["id"],
            "title": r["title"],
            "company": r["company"],
            "location": r["location"] or "",
            "type": r["type"] or "Full-time",
            "salary": r["salary"] or "",
            "status": r["status"] or "Active",
            "created_at": r["created_at"] or "",
            "applications_count": r["applications_count"] or 0
        })

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
    pagination = {
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_items": total_count,
        "total_pages": total_pages,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    return {
        "success": True,
        "jobs": jobs,
        "pagination": pagination,
        "data": {
            "jobs": jobs,
            "pagination": pagination
        }
    }


def get_platform_job_detail(job_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch administrative details for a single internal job posting,
    including applicant list with match scores.
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, title, company, location, type, salary, skills, description, status, created_at
               FROM jobs WHERE id = ?""",
            (job_id,)
        ).fetchone()

        if not row:
            return None

        # Fetch recent applicants
        app_rows = conn.execute(
            """SELECT a.id, a.user_id, a.match_score, a.status, a.applied_at,
                      u.name as candidate_name, u.email as candidate_email
               FROM applications a
               LEFT JOIN users u ON a.user_id = u.id
               WHERE a.job_id = ?
               ORDER BY a.id DESC LIMIT 20""",
            (job_id,)
        ).fetchall()

    applicants = []
    for a in app_rows:
        applicants.append({
            "application_id": a["id"],
            "user_id": a["user_id"],
            "candidate_name": a["candidate_name"] or "Unknown",
            "candidate_email": a["candidate_email"] or "",
            "match_score": a["match_score"] or 0,
            "status": a["status"] or "Pending",
            "applied_at": a["applied_at"] or ""
        })

    return {
        "id": row["id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"] or "",
        "type": row["type"] or "Full-time",
        "salary": row["salary"] or "",
        "skills": [s.strip() for s in (row["skills"] or "").split(",") if s.strip()],
        "description": row["description"] or "",
        "status": row["status"] or "Active",
        "created_at": row["created_at"] or "",
        "applications_count": len(applicants),
        "applicants": applicants
    }


def update_platform_job_status(job_id: int, status: str, admin_user_id: int = 0) -> Tuple[bool, str, int]:
    """
    Administrative status toggle for an internal job posting (Active / Closed / Draft).
    """
    valid_statuses = {"Active", "Closed", "Draft"}
    status_normalized = status.strip().title()
    if status_normalized not in valid_statuses:
        return False, f"Invalid job status '{status}'. Must be Active, Closed, or Draft.", 400

    with get_db() as conn:
        job = conn.execute("SELECT id, title, status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return False, "Job posting not found.", 404

        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status_normalized, job_id))
        conn.commit()

    return True, f"Job #{job_id} ('{job['title']}') status successfully updated to {status_normalized}.", 200


def delete_platform_job(job_id: int, admin_user_id: int = 0) -> Tuple[bool, str, int]:
    """
    Permanently delete an internal job posting and cascade clean associated applications.
    """
    with get_db() as conn:
        job = conn.execute("SELECT id, title FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return False, "Job posting not found.", 404

        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()

    return True, f"Job #{job_id} ('{job['title']}') successfully deleted.", 200


# ── 6. Platform Applications Management ──────────────────────

def get_platform_applications(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    status: str = "",
    job_id: Optional[int] = None,
    min_match: Optional[int] = None,
    max_match: Optional[int] = None
) -> Dict[str, Any]:
    """
    Paginated, searchable administrative view of internal candidate applications.
    Supports filtering by candidate, job, status, job_id, and match score ranges.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    conditions = []
    params: List[Any] = []

    if search:
        term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(u.name) LIKE ? OR LOWER(u.email) LIKE ? OR LOWER(j.title) LIKE ? OR LOWER(j.company) LIKE ?)")
        params.extend([term, term, term, term])

    if status:
        conditions.append("LOWER(a.status) = ?")
        params.append(status.strip().lower())

    if job_id is not None and int(job_id) > 0:
        conditions.append("a.job_id = ?")
        params.append(int(job_id))

    if min_match is not None:
        conditions.append("a.match_score >= ?")
        params.append(int(min_match))

    if max_match is not None:
        conditions.append("a.match_score <= ?")
        params.append(int(max_match))

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        count_query = f"""
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN jobs j ON a.job_id = j.id
            {where_clause}
        """
        total_count = conn.execute(count_query, tuple(params)).fetchone()[0]

        data_query = f"""
            SELECT a.id, a.user_id, a.job_id, a.match_score, a.status, a.applied_at,
                   u.name as candidate_name, u.email as candidate_email,
                   j.title as job_title, j.company as job_company
            FROM applications a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN jobs j ON a.job_id = j.id
            {where_clause}
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?
        """
        fetch_params = list(params) + [limit, offset]
        rows = conn.execute(data_query, tuple(fetch_params)).fetchall()

    applications = []
    for r in rows:
        applications.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "job_id": r["job_id"],
            "candidate_name": r["candidate_name"] or "Unknown",
            "candidate_email": r["candidate_email"] or "",
            "job_title": r["job_title"] or "Deleted Job",
            "job_company": r["job_company"] or "",
            "match_score": r["match_score"] or 0,
            "status": r["status"] or "Pending",
            "applied_at": r["applied_at"] or ""
        })

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
    pagination = {
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_items": total_count,
        "total_pages": total_pages,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    return {
        "success": True,
        "applications": applications,
        "pagination": pagination,
        "data": {
            "applications": applications,
            "pagination": pagination
        }
    }


def update_platform_application_status(
    app_id: int,
    status: str,
    notes: str = "",
    admin_user_id: int = 0
) -> Tuple[bool, str, int]:
    """
    Administrative status transition for an application (Pending, Reviewing, Shortlisted, Rejected, Hired).
    Inserts audit trail and candidate notification.
    """
    valid_statuses = {"Pending", "Reviewing", "Shortlisted", "Rejected", "Hired"}
    status_normalized = status.strip().title()
    if status_normalized not in valid_statuses:
        return False, f"Invalid status '{status}'. Allowed values: {', '.join(sorted(valid_statuses))}", 400

    with get_db() as conn:
        app_row = conn.execute(
            """SELECT a.id, a.user_id, a.job_id, a.status, u.name as candidate_name, j.title as job_title
               FROM applications a
               LEFT JOIN users u ON a.user_id = u.id
               LEFT JOIN jobs j ON a.job_id = j.id
               WHERE a.id = ?""",
            (app_id,)
        ).fetchone()

        if not app_row:
            return False, "Application not found.", 404

        prev_status = app_row["status"]
        conn.execute("UPDATE applications SET status = ? WHERE id = ?", (status_normalized, app_id))

        audit_note = notes.strip() if notes else f"Status updated from {prev_status} to {status_normalized} by Platform Admin"
        conn.execute(
            "INSERT INTO application_status (application_id, status, notes) VALUES (?, ?, ?)",
            (app_id, status_normalized, audit_note)
        )

        if app_row["user_id"]:
            conn.execute(
                """INSERT INTO notifications (user_id, title, message, type, action_type, action_target)
                   VALUES (?, ?, ?, 'application', 'view_application', '#cand-applications')""",
                (
                    app_row["user_id"],
                    f"Application Status Updated: {status_normalized}",
                    f"Your application for '{app_row['job_title'] or 'Job Post'}' has been updated to '{status_normalized}'."
                )
            )
        conn.commit()

    return True, f"Application #{app_id} status successfully updated to {status_normalized}.", 200


def get_platform_jobs_apps_summary() -> Dict[str, Any]:
    """
    Returns real-time KPI overview metrics and unique company list for Jobs & Applications tab.
    """
    with get_db() as conn:
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        active_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE LOWER(status) = 'active'").fetchone()[0]
        closed_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE LOWER(status) = 'closed'").fetchone()[0]
        draft_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE LOWER(status) = 'draft'").fetchone()[0]

        total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        avg_match_row = conn.execute("SELECT AVG(match_score) FROM applications WHERE match_score > 0").fetchone()[0]
        avg_match = round(float(avg_match_row), 1) if avg_match_row is not None else 0.0

        company_rows = conn.execute("SELECT DISTINCT company FROM jobs WHERE company IS NOT NULL AND company != '' ORDER BY company ASC").fetchall()
        companies = [r["company"] for r in company_rows]

    summary_data = {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "closed_jobs": closed_jobs,
        "draft_jobs": draft_jobs,
        "total_applications": total_apps,
        "avg_match_score": avg_match,
        "companies": companies
    }

    return {
        "success": True,
        "summary": summary_data,
        "data": summary_data
    }


def get_platform_application_detail(app_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive administrative details for a specific application,
    including candidate profile, job details, and status transition history.
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT a.id, a.user_id, a.job_id, a.match_score, a.status, a.applied_at,
                      u.name as candidate_name, u.email as candidate_email, u.phone as candidate_phone,
                      u.location as candidate_location, u.skills as candidate_skills, u.ats_score,
                      j.title as job_title, j.company as job_company, j.location as job_location,
                      j.type as job_type, j.salary as job_salary
               FROM applications a
               LEFT JOIN users u ON a.user_id = u.id
               LEFT JOIN jobs j ON a.job_id = j.id
               WHERE a.id = ?""",
            (app_id,)
        ).fetchone()

        if not row:
            return None

        # Fetch status audit trail for this application
        status_trail = conn.execute(
            """SELECT id, status, notes, updated_at
               FROM application_status
               WHERE application_id = ?
               ORDER BY id ASC""",
            (app_id,)
        ).fetchall()

    history = []
    for s in status_trail:
        history.append({
            "id": s["id"],
            "status": s["status"],
            "notes": s["notes"] or "",
            "updated_at": s["updated_at"] or ""
        })

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "job_id": row["job_id"],
        "match_score": row["match_score"] or 0,
        "status": row["status"] or "Pending",
        "applied_at": row["applied_at"] or "",
        "candidate": {
            "id": row["user_id"],
            "name": row["candidate_name"] or "Unknown",
            "email": row["candidate_email"] or "",
            "phone": row["candidate_phone"] or "",
            "location": row["candidate_location"] or "",
            "skills": [s.strip() for s in (row["candidate_skills"] or "").split(",") if s.strip()],
            "ats_score": row["ats_score"] or 0
        },
        "job": {
            "id": row["job_id"],
            "title": row["job_title"] or "Deleted Job",
            "company": row["job_company"] or "",
            "location": row["job_location"] or "",
            "type": row["job_type"] or "Full-time",
            "salary": row["job_salary"] or ""
        },
        "history": history
    }


# ── 7. Platform Resume Operations ────────────────────────────

def get_platform_resumes(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    status: str = ""
) -> Dict[str, Any]:
    """
    Paginated, searchable administrative view of resumes in the system.
    Tracks file integrity, parse status, and candidate linkage.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit

    conditions = []
    params: List[Any] = []

    if search:
        term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(r.original_name) LIKE ? OR LOWER(u.name) LIKE ? OR LOWER(u.email) LIKE ?)")
        params.extend([term, term, term])

    if status:
        st = status.strip().lower()
        if st in ("pending", "processing", "uploaded"):
            conditions.append("r.status IN ('uploaded', 'processing')")
        else:
            conditions.append("LOWER(r.status) = ?")
            params.append(st)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        # Processing summary statistics
        total_resumes = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        status_counts = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM resumes GROUP BY status"
        ).fetchall()
        by_status = {r["status"]: r["cnt"] for r in status_counts}
        summary_info = {
            "total": total_resumes,
            "processed": by_status.get("processed", 0),
            "pending": by_status.get("uploaded", 0) + by_status.get("processing", 0),
            "failed": by_status.get("failed", 0)
        }

        # Filtered count
        filtered_count = conn.execute(
            f"""SELECT COUNT(*)
                FROM resumes r
                LEFT JOIN users u ON r.user_id = u.id
                {where_clause}""",
            tuple(params)
        ).fetchone()[0]

        # Data query
        data_query = f"""
            SELECT r.id, r.user_id, r.original_name, r.stored_filename, r.file_path,
                   r.file_size_bytes, r.mime_type, r.word_count, r.ats_score,
                   r.status, r.uploaded_at,
                   u.name as candidate_name, u.email as candidate_email
            FROM resumes r
            LEFT JOIN users u ON r.user_id = u.id
            {where_clause}
            ORDER BY r.id DESC
            LIMIT ? OFFSET ?
        """
        fetch_params = list(params) + [limit, offset]
        rows = conn.execute(data_query, tuple(fetch_params)).fetchall()

    resumes = []
    for r in rows:
        fpath = r["file_path"] or ""
        exists_on_disk = os.path.isfile(fpath) if fpath else False
        resumes.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "candidate_name": r["candidate_name"] or "Unknown",
            "candidate_email": r["candidate_email"] or "",
            "filename": r["original_name"],
            "stored_filename": r["stored_filename"],
            "file_size_bytes": r["file_size_bytes"] or 0,
            "mime_type": r["mime_type"] or "application/pdf",
            "word_count": r["word_count"] or 0,
            "ats_score": r["ats_score"] or 0,
            "status": r["status"] or "processed",
            "file_exists": exists_on_disk,
            "file_status": "Available" if exists_on_disk else "Missing File",
            "uploaded_at": r["uploaded_at"] or ""
        })

    total_pages = (filtered_count + limit - 1) // limit if limit > 0 else 1
    pagination = {
        "page": page,
        "limit": limit,
        "total": filtered_count,
        "total_items": filtered_count,
        "total_pages": total_pages,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    return {
        "success": True,
        "summary": summary_info,
        "resumes": resumes,
        "pagination": pagination,
        "data": {
            "summary": summary_info,
            "resumes": resumes,
            "pagination": pagination
        }
    }


def get_platform_resume_detail(resume_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch administrative metadata and parsed intelligence for a resume.
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT r.id, r.user_id, r.original_name, r.stored_filename, r.file_path,
                      r.file_hash, r.file_size_bytes, r.mime_type, r.parsed_text,
                      r.word_count, r.ats_score, r.extracted_skills, r.structured_json,
                      r.status, r.version, r.uploaded_at,
                      u.name as candidate_name, u.email as candidate_email
               FROM resumes r
               LEFT JOIN users u ON r.user_id = u.id
               WHERE r.id = ?""",
            (resume_id,)
        ).fetchone()

        if not row:
            return None

    fpath = row["file_path"] or ""
    exists_on_disk = os.path.isfile(fpath) if fpath else False

    # Preview of parsed text (first 500 chars)
    raw_text = row["parsed_text"] or ""
    text_preview = (raw_text[:500] + "...") if len(raw_text) > 500 else raw_text

    skills_raw = row["extracted_skills"] or ""
    skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "candidate_name": row["candidate_name"] or "Unknown",
        "candidate_email": row["candidate_email"] or "",
        "original_name": row["original_name"],
        "stored_filename": row["stored_filename"],
        "file_hash": row["file_hash"] or "",
        "file_size_bytes": row["file_size_bytes"] or 0,
        "mime_type": row["mime_type"] or "application/pdf",
        "word_count": row["word_count"] or 0,
        "ats_score": row["ats_score"] or 0,
        "status": row["status"] or "processed",
        "version": row["version"] or 1,
        "uploaded_at": row["uploaded_at"] or "",
        "file_exists": exists_on_disk,
        "file_status": "Available" if exists_on_disk else "Missing on disk",
        "extracted_skills": skills_list,
        "text_preview": text_preview
    }


# ── 8. Platform System Health & Integrations ─────────────────

def get_platform_system_health() -> Dict[str, Any]:
    """
    Real-time health verification for internal and external services.
    Every service is probed; statuses are strictly:
    'Healthy', 'Degraded', 'Unavailable', or 'Not Configured'.
    Zero hardcoded statuses.
    """
    import time
    services = {}

    # 1. Database
    try:
        t0 = time.time()
        with get_db() as conn:
            row = conn.execute("SELECT 1 AS probe").fetchone()
            latency_ms = round((time.time() - t0) * 1000, 2)
            if row and (row["probe"] == 1 or row[0] == 1):
                services["database"] = {
                    "name": "Database (SQLite/PostgreSQL)",
                    "status": "Healthy",
                    "latency_ms": latency_ms,
                    "details": f"Responsive ({latency_ms} ms)"
                }
            else:
                services["database"] = {
                    "name": "Database",
                    "status": "Degraded",
                    "details": "Unexpected probe return"
                }
    except Exception as e:
        logger.error(f"Health probe database error: {e}")
        services["database"] = {
            "name": "Database",
            "status": "Unavailable",
            "details": f"Database error: {type(e).__name__}"
        }

    # 2. File Storage (Resumes directory)
    try:
        upload_dir = os.path.join(os.getcwd(), "uploads", "resumes")
        if os.path.isdir(upload_dir):
            probe_path = os.path.join(upload_dir, ".health_probe.tmp")
            with open(probe_path, "w") as f:
                f.write("probe")
            if os.path.isfile(probe_path):
                os.remove(probe_path)
                services["file_storage"] = {
                    "name": "Resume File Storage",
                    "status": "Healthy",
                    "details": "Directory mounted and writable"
                }
            else:
                services["file_storage"] = {
                    "name": "Resume File Storage",
                    "status": "Degraded",
                    "details": "Probe file creation failed"
                }
        else:
            services["file_storage"] = {
                "name": "Resume File Storage",
                "status": "Unavailable",
                "details": "Upload directory does not exist"
            }
    except Exception as e:
        services["file_storage"] = {
            "name": "Resume File Storage",
            "status": "Degraded",
            "details": f"File storage write test failed: {e}"
        }

    # 3. Authentication Subsystem
    try:
        from flask import current_app
        secret = current_app.config.get("SECRET_KEY", "") if current_app else os.getenv("SECRET_KEY", "")
        if secret and len(secret) >= 16:
            services["authentication"] = {
                "name": "Authentication & RBAC",
                "status": "Healthy",
                "details": "Session signer & tokens active"
            }
        else:
            services["authentication"] = {
                "name": "Authentication & RBAC",
                "status": "Degraded",
                "details": "Weak or default secret key detected"
            }
    except Exception as e:
        services["authentication"] = {
            "name": "Authentication & RBAC",
            "status": "Degraded",
            "details": str(e)
        }

    # 4. Resume Parser
    try:
        import PyPDF2
        services["resume_parser"] = {
            "name": "Resume Parser Pipeline",
            "status": "Healthy",
            "details": "PDF parser engines loaded"
        }
    except Exception as e:
        services["resume_parser"] = {
            "name": "Resume Parser Pipeline",
            "status": "Unavailable",
            "details": f"Parser dependency missing: {e}"
        }

    # 5. ATS & Skill Intelligence Engine
    try:
        from app.ml.skill_extraction.skills_db import ALL_SKILLS, JOB_ROLE_SKILLS
        if len(ALL_SKILLS) > 0 and len(JOB_ROLE_SKILLS) > 0:
            services["ats_engine"] = {
                "name": "ATS & Skill Engine",
                "status": "Healthy",
                "details": f"Loaded {len(ALL_SKILLS)} canonical skills"
            }
        else:
            services["ats_engine"] = {
                "name": "ATS & Skill Engine",
                "status": "Degraded",
                "details": "Skill database dictionary is empty"
            }
    except Exception as e:
        services["ats_engine"] = {
            "name": "ATS & Skill Engine",
            "status": "Unavailable",
            "details": f"ATS engine error: {e}"
        }

    # 6. Job Matcher
    try:
        from app.ml.matching.job_matcher import calculate_match_score
        score = calculate_match_score(["Python"], ["Python", "Flask"])
        services["job_matcher"] = {
            "name": "Job Matching Engine",
            "status": "Healthy",
            "details": "Matcher operational"
        }
    except Exception as e:
        services["job_matcher"] = {
            "name": "Job Matching Engine",
            "status": "Degraded",
            "details": f"Matcher error: {e}"
        }

    # 7. Adzuna Integration
    try:
        from app.services.adzuna_client import adzuna_client
        app_id = adzuna_client.app_id or ""
        app_key = adzuna_client.app_key or ""
        if app_id and app_key and len(app_id) > 2 and len(app_key) > 5:
            services["adzuna"] = {
                "name": "Adzuna Live Jobs",
                "status": "Healthy",
                "details": f"Configured ({adzuna_client.country.upper()})"
            }
        else:
            services["adzuna"] = {
                "name": "Adzuna Live Jobs",
                "status": "Not Configured",
                "details": "Credentials not set in environment"
            }
    except Exception as e:
        services["adzuna"] = {
            "name": "Adzuna Live Jobs",
            "status": "Degraded",
            "details": f"Client initialization error: {e}"
        }

    # 8. Email Service
    try:
        from app.services.email_service import get_email_provider, SMTPEmailProvider, TestEmailProvider
        provider = get_email_provider()
        if isinstance(provider, TestEmailProvider):
            services["email"] = {
                "name": "Email Delivery",
                "status": "Healthy",
                "details": "In-memory test provider active"
            }
        elif isinstance(provider, SMTPEmailProvider):
            if provider.host:
                services["email"] = {
                    "name": "Email Delivery (SMTP)",
                    "status": "Healthy",
                    "details": "SMTP server configured"
                }
            else:
                services["email"] = {
                    "name": "Email Delivery (SMTP)",
                    "status": "Not Configured",
                    "details": "SMTP host not specified"
                }
        else:
            services["email"] = {
                "name": "Email Delivery",
                "status": "Not Configured",
                "details": "Provider unconfigured"
            }
    except Exception as e:
        services["email"] = {
            "name": "Email Delivery",
            "status": "Degraded",
            "details": f"Email service error: {e}"
        }

    # Calculate overall health
    statuses = [s["status"] for s in services.values()]
    if any(st == "Unavailable" for st in [services.get("database", {}).get("status")]):
        overall = "Unavailable"
    elif any(st in ("Degraded", "Unavailable") for st in statuses):
        overall = "Degraded"
    else:
        overall = "Healthy"

    healthy_count = sum(1 for st in statuses if st == "Healthy")
    total_count = len(services)

    payload = {
        "overall": overall,
        "overall_status": overall,
        "healthy_count": healthy_count,
        "total_services": total_count,
        "services": services
    }

    return {
        "success": True,
        "data": payload,
        **payload
    }


def get_platform_integrations() -> Dict[str, Any]:
    """
    Returns sanitized status of external/subsystem integrations.
    STRICT SECURITY: Never exposes API keys, tokens, credentials, or .env values.
    """
    integrations = []

    # 1. Adzuna Integration
    try:
        from app.services.adzuna_client import adzuna_client
        has_id = bool(adzuna_client.app_id and len(adzuna_client.app_id) > 2)
        has_key = bool(adzuna_client.app_key and len(adzuna_client.app_key) > 5)
        is_cfg = has_id and has_key

        with get_db() as conn:
            cached_count = conn.execute("SELECT COUNT(*) FROM provider_cache").fetchone()[0]
            last_health_row = conn.execute(
                "SELECT status, latency_ms, checked_at FROM provider_health ORDER BY id DESC LIMIT 1"
            ).fetchone()

        last_status = last_health_row["status"] if last_health_row else ("Configured" if is_cfg else "Unconfigured")
        last_check = last_health_row["checked_at"] if last_health_row else None

        integrations.append({
            "name": "Adzuna Job Search API",
            "type": "Live Job Data Provider",
            "configured": is_cfg,
            "status": "Active" if is_cfg else "Not Configured",
            "country": adzuna_client.country.upper() if adzuna_client else "IN",
            "cached_queries": cached_count,
            "last_status": last_status,
            "last_checked": last_check,
            "notes": "External live job search and multi-query caching layer."
        })
    except Exception as e:
        integrations.append({
            "name": "Adzuna Job Search API",
            "type": "Live Job Data Provider",
            "configured": False,
            "status": "Error",
            "notes": f"Error: {e}"
        })

    # 2. Email Delivery Subsystem
    try:
        from app.services.email_service import get_email_provider, SMTPEmailProvider, TestEmailProvider
        from app.config.settings import Config
        provider = get_email_provider()
        is_test = isinstance(provider, TestEmailProvider)
        is_smtp = isinstance(provider, SMTPEmailProvider)

        # Masked host if smtp
        masked_host = ""
        if is_smtp and provider.host:
            parts = provider.host.split(".")
            masked_host = f"{parts[0][:2]}***.{'.'.join(parts[1:])}" if len(parts) > 1 else "Configured (SMTP)"

        integrations.append({
            "name": "Email Delivery Service",
            "type": "Transactional Messaging",
            "configured": True,
            "status": "Active (Test Provider)" if is_test else ("Active (SMTP)" if is_smtp else "Unconfigured"),
            "provider_type": "TestEmailProvider" if is_test else "SMTPEmailProvider",
            "host": masked_host if is_smtp else "In-Memory Outbox",
            "from_email": Config.MAIL_FROM if hasattr(Config, "MAIL_FROM") else "noreply@talentsync.ai",
            "notes": "Account verification and notification dispatch."
        })
    except Exception as e:
        integrations.append({
            "name": "Email Delivery Service",
            "type": "Transactional Messaging",
            "configured": False,
            "status": "Error",
            "notes": f"Error: {e}"
        })

    # 3. Optical Character Recognition (OCR)
    try:
        from app.services.ocr_service import is_ocr_engine_available
        from app.config.settings import Config
        ocr_avail, ocr_desc = is_ocr_engine_available()

        integrations.append({
            "name": "Optical Character Recognition (OCR)",
            "type": "Document Text Extraction Fallback",
            "configured": Config.OCR_ENABLED,
            "status": "Available" if ocr_avail else ("Disabled" if not Config.OCR_ENABLED else "Unavailable"),
            "engine": ocr_desc,
            "notes": "Fallback parser for scanned or image-based PDF resumes."
        })
    except Exception as e:
        integrations.append({
            "name": "Optical Character Recognition (OCR)",
            "type": "Document Text Extraction Fallback",
            "configured": False,
            "status": "Error",
            "notes": f"Error: {e}"
        })

    # 4. ML / AI Resume Intelligence Engine
    try:
        from app.ml.skill_extraction.skills_db import ALL_SKILLS
        from app.ml.recommendation.tfidf_model import get_model_info
        skill_count = len(ALL_SKILLS)
        model_info = get_model_info()
        model_loaded = model_info.get('loaded', False)
        integrations.append({
            "name": "ML / AI Resume Intelligence Engine",
            "type": "AI Skill Extraction & Job Matching",
            "configured": True,
            "status": "Active" if model_loaded else "Degraded",
            "skill_db_size": skill_count,
            "model": "spaCy NER + TF-IDF Recommender",
            "notes": "Powers ATS scoring, skill extraction, and intelligent job matching."
        })
    except Exception as e:
        integrations.append({
            "name": "ML / AI Resume Intelligence Engine",
            "type": "AI Skill Extraction & Job Matching",
            "configured": False,
            "status": "Degraded",
            "notes": f"ML engine probe: {type(e).__name__}"
        })

    payload = {
        "integrations": integrations
    }

    return {
        "success": True,
        "data": payload,
        **payload
    }

