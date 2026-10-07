# ============================================================
#  TalentSync — Candidate Notification Center Tests
#  Security, RBAC, IDOR Defense, Event Lifecycle & Operations
# ============================================================

import json
import unittest
from app import create_app
from app.config.settings import TestingConfig
from app.database.connection import get_db
from werkzeug.security import generate_password_hash


class TestCandidateNotificationCenter(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            with get_db() as conn:
                conn.execute("DELETE FROM notifications")
                conn.execute("DELETE FROM applications")
                conn.execute("DELETE FROM resumes")
                conn.execute("DELETE FROM users WHERE email LIKE '%@testnotif.com'")

                pwd = generate_password_hash("Password123!")

                # Candidate A
                cur = conn.execute(
                    "INSERT INTO users (name, email, password, role, is_verified) VALUES ('Cand A', 'cand_a@testnotif.com', ?, 'candidate', 1)",
                    (pwd,)
                )
                self.cand_a_id = cur.lastrowid

                # Candidate B
                cur = conn.execute(
                    "INSERT INTO users (name, email, password, role, is_verified) VALUES ('Cand B', 'cand_b@testnotif.com', ?, 'candidate', 1)",
                    (pwd,)
                )
                self.cand_b_id = cur.lastrowid

                # HR Manager
                cur = conn.execute(
                    "INSERT INTO users (name, email, password, role, is_verified) VALUES ('HR Manager', 'hr_mgr@testnotif.com', ?, 'hr', 1)",
                    (pwd,)
                )
                self.hr_id = cur.lastrowid

                # Notifications for Cand A
                conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, is_read, action_type, action_target, metadata, created_at)
                       VALUES (?, 'App Shortlisted', 'Your application is shortlisted', 'application', 0, 'view_application', '#cand-applications', '{"job_id": 101}', '2026-10-07 10:00:00')""",
                    (self.cand_a_id,)
                )
                conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, is_read, action_type, action_target, metadata, created_at)
                       VALUES (?, 'New Job Match', 'React Developer role matches 88%', 'match', 0, 'view_jobs', '#cand-jobs', '{"job_id": 102}', '2026-10-07 11:00:00')""",
                    (self.cand_a_id,)
                )
                conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, is_read, action_type, action_target, metadata, created_at)
                       VALUES (?, 'Profile Viewed', 'Recruiter viewed your profile', 'view', 1, 'view_profile', '#cand-profile', '{}', '2026-10-06 09:00:00')""",
                    (self.cand_a_id,)
                )
                conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, is_read, action_type, action_target, metadata, created_at)
                       VALUES (?, 'Resume Scored', 'ATS score updated to 85/100', 'system', 1, 'view_ats', '#cand-ats', '{"ats_score": 85}', '2026-10-05 14:00:00')""",
                    (self.cand_a_id,)
                )

                # Notification for Cand B
                cur = conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, is_read, action_type, action_target, metadata, created_at)
                       VALUES (?, 'Cand B Secret Notif', 'Confidential to Candidate B', 'application', 0, 'view_application', '#cand-applications', '{}', '2026-10-07 12:00:00')""",
                    (self.cand_b_id,)
                )
                self.notif_b_id = cur.lastrowid

                conn.commit()

    def _login(self, user_id, role='candidate'):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = role

    # ============================================================
    # 1. AUTHENTICATION & ACCESS TESTS
    # ============================================================

    def test_unauthenticated_access_denied(self):
        """Unauthenticated access to notification endpoints must return 401."""
        assert self.client.get('/api/notifications').status_code == 401
        assert self.client.get('/api/notifications/unread-count').status_code == 401
        assert self.client.post('/api/notifications/1/read').status_code == 401
        assert self.client.delete('/api/notifications/1').status_code == 401
        assert self.client.post('/api/notifications/read-all').status_code == 401
        assert self.client.delete('/api/notifications/clear').status_code == 401

    def test_candidate_retrieves_own_notifications_only(self):
        """Candidate receives only their own notifications with accurate unread count."""
        self._login(self.cand_a_id)
        res = self.client.get('/api/notifications')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['total'] == 4
        assert data['unread_count'] == 2
        assert len(data['notifications']) == 4

        # Ensure Candidate B's notification is NOT leaked
        titles = [n['title'] for n in data['notifications']]
        assert 'Cand B Secret Notif' not in titles

    # ============================================================
    # 2. CATEGORY FILTERS & SEARCH TESTS
    # ============================================================

    def test_category_filters(self):
        """Category filter returns only matching notification types."""
        self._login(self.cand_a_id)

        # Unread category
        res = self.client.get('/api/notifications?category=unread')
        data = res.get_json()
        assert len(data['notifications']) == 2
        assert all(n['is_read'] == 0 for n in data['notifications'])

        # Application category
        res = self.client.get('/api/notifications?category=application')
        data = res.get_json()
        assert len(data['notifications']) == 1
        assert data['notifications'][0]['type'] == 'application'

        # Match category
        res = self.client.get('/api/notifications?category=match')
        data = res.get_json()
        assert len(data['notifications']) == 1
        assert data['notifications'][0]['type'] == 'match'

        # View category
        res = self.client.get('/api/notifications?category=view')
        data = res.get_json()
        assert len(data['notifications']) == 1
        assert data['notifications'][0]['type'] == 'view'

        # System category
        res = self.client.get('/api/notifications?category=system')
        data = res.get_json()
        assert len(data['notifications']) == 1
        assert data['notifications'][0]['type'] == 'system'

    def test_notification_search(self):
        """Search queries filter matching titles and messages."""
        self._login(self.cand_a_id)

        res = self.client.get('/api/notifications?search=React')
        data = res.get_json()
        assert len(data['notifications']) == 1
        assert 'React Developer' in data['notifications'][0]['message']

        res = self.client.get('/api/notifications?search=NonExistentTermXYZ')
        data = res.get_json()
        assert len(data['notifications']) == 0

    # ============================================================
    # 3. IDOR & OBJECT-LEVEL AUTHORIZATION DEFENSE (CRITICAL)
    # ============================================================

    def test_idor_cannot_read_another_users_notification(self):
        """Candidate A cannot mark Candidate B's notification as read."""
        self._login(self.cand_a_id)

        # Attempt to mark Candidate B's notification read
        res = self.client.post(f'/api/notifications/{self.notif_b_id}/read')
        assert res.status_code == 403
        assert res.get_json()['success'] is False

        # Verify Candidate B's notification remains unread in database
        with self.app.app_context():
            with get_db() as conn:
                b_notif = conn.execute("SELECT is_read FROM notifications WHERE id=?", (self.notif_b_id,)).fetchone()
                assert b_notif['is_read'] == 0

    def test_idor_cannot_delete_another_users_notification(self):
        """Candidate A cannot delete Candidate B's notification."""
        self._login(self.cand_a_id)

        # Attempt to delete Candidate B's notification
        res = self.client.delete(f'/api/notifications/{self.notif_b_id}')
        assert res.status_code == 403
        assert res.get_json()['success'] is False

        # Verify Candidate B's notification still exists in database
        with self.app.app_context():
            with get_db() as conn:
                b_notif = conn.execute("SELECT id FROM notifications WHERE id=?", (self.notif_b_id,)).fetchone()
                assert b_notif is not None

    # ============================================================
    # 4. MARK READ, MARK ALL, & CLEAR READ OPERATIONS
    # ============================================================

    def test_mark_individual_notification_read(self):
        """Owner marks a single notification as read."""
        self._login(self.cand_a_id)

        # Get one of Candidate A's unread notifications
        res = self.client.get('/api/notifications?category=unread')
        notif_id = res.get_json()['notifications'][0]['id']

        res = self.client.post(f'/api/notifications/{notif_id}/read')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['unread_count'] == 1

        # Verify state in DB
        with self.app.app_context():
            with get_db() as conn:
                row = conn.execute("SELECT is_read FROM notifications WHERE id=?", (notif_id,)).fetchone()
                assert row['is_read'] == 1

    def test_mark_all_read(self):
        """Owner marks all unread notifications as read."""
        self._login(self.cand_a_id)

        res = self.client.post('/api/notifications/read-all')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['unread_count'] == 0

        # Ensure Candidate B's unread notification was untouched
        with self.app.app_context():
            with get_db() as conn:
                b_row = conn.execute("SELECT is_read FROM notifications WHERE id=?", (self.notif_b_id,)).fetchone()
                assert b_row['is_read'] == 0

    def test_clear_read_preserves_unread(self):
        """SEC-14: Clear read must delete ONLY read notifications and PRESERVE unread notifications."""
        self._login(self.cand_a_id)

        # Cand A starts with 2 unread, 2 read
        res = self.client.delete('/api/notifications/clear')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['deleted_count'] == 2
        assert data['unread_count'] == 2

        # Fetch remaining notifications for Cand A
        res = self.client.get('/api/notifications')
        remaining = res.get_json()['notifications']
        assert len(remaining) == 2
        assert all(n['is_read'] == 0 for n in remaining)

        # Verify Candidate B was unaffected
        with self.app.app_context():
            with get_db() as conn:
                b_row = conn.execute("SELECT id FROM notifications WHERE id=?", (self.notif_b_id,)).fetchone()
                assert b_row is not None

    def test_delete_individual_notification(self):
        """Owner can delete their own notification."""
        self._login(self.cand_a_id)

        res = self.client.get('/api/notifications')
        notif_id = res.get_json()['notifications'][0]['id']

        res = self.client.delete(f'/api/notifications/{notif_id}')
        assert res.status_code == 200
        assert res.get_json()['success'] is True

        # Verify deleted from DB
        with self.app.app_context():
            with get_db() as conn:
                row = conn.execute("SELECT id FROM notifications WHERE id=?", (notif_id,)).fetchone()
                assert row is None

    def test_concurrency_and_idempotency(self):
        """Deleting or reading the same notification twice does not error or crash."""
        self._login(self.cand_a_id)

        res = self.client.get('/api/notifications')
        notif_id = res.get_json()['notifications'][0]['id']

        # Read twice
        res1 = self.client.post(f'/api/notifications/{notif_id}/read')
        res2 = self.client.post(f'/api/notifications/{notif_id}/read')
        assert res1.status_code == 200
        assert res2.status_code == 200

        # Delete twice (second should return 404 cleanly)
        del1 = self.client.delete(f'/api/notifications/{notif_id}')
        del2 = self.client.delete(f'/api/notifications/{notif_id}')
        assert del1.status_code == 200
        assert del2.status_code == 404

    # ============================================================
    # 5. HARDENING & P0/P1 PRODUCTION AUDIT TESTS
    # ============================================================

    def test_metadata_security_sanitization(self):
        """Verify sensitive credentials/tokens in metadata are never leaked to client."""
        self._login(self.cand_a_id)
        with self.app.app_context():
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, is_read, metadata)
                       VALUES (?, 'Security Test', 'Testing metadata sanitization', 'security', 0, ?)""",
                    (
                        self.cand_a_id,
                        json.dumps({
                            'job_id': 55,
                            'password': 'SuperSecretPassword!',
                            'token': 'bearer_token_xyz',
                            'database_url': 'sqlite:///sensitive.db'
                        })
                    )
                )
                conn.commit()

        res = self.client.get('/api/notifications?category=system')
        assert res.status_code == 200
        data = res.get_json()
        meta = None
        for n in data['notifications']:
            if n['title'] == 'Security Test':
                meta = n['metadata']
                break
        assert meta is not None
        assert meta.get('job_id') == 55
        assert 'password' not in meta
        assert 'token' not in meta
        assert 'database_url' not in meta

    def test_application_status_transition_idempotency(self):
        """Verify duplicate application status transitions do not produce duplicate notifications."""
        # Create job & application for Cand A
        with self.app.app_context():
            with get_db() as conn:
                cur = conn.execute(
                    "INSERT INTO jobs (title, company, status) VALUES ('Cloud Engineer', 'TalentSync Corp', 'Active')"
                )
                job_id = cur.lastrowid
                cur = conn.execute(
                    "INSERT INTO applications (user_id, job_id, status) VALUES (?, ?, 'Reviewing')",
                    (self.cand_a_id, job_id)
                )
                app_id = cur.lastrowid
                conn.commit()

        # Login as HR Manager
        self._login(self.hr_id, role='hr')

        # 1. Update status to Shortlisted
        res1 = self.client.post('/api/admin/update_status', json={'app_id': app_id, 'status': 'Shortlisted'})
        assert res1.status_code == 200

        # Check notification count for Cand A
        self._login(self.cand_a_id)
        res = self.client.get('/api/notifications?category=application')
        notifs_1 = [n for n in res.get_json()['notifications'] if 'Cloud Engineer' in n['message']]
        assert len(notifs_1) == 1
        assert 'Shortlisted' in notifs_1[0]['title'] or 'Shortlisted' in notifs_1[0]['message']

        # 2. Re-send identical status update (Shortlisted -> Shortlisted)
        self._login(self.hr_id, role='hr')
        res2 = self.client.post('/api/admin/update_status', json={'app_id': app_id, 'status': 'Shortlisted'})
        assert res2.status_code == 200

        # Check notification count for Cand A remains exactly 1 (no duplicate generated)
        self._login(self.cand_a_id)
        res = self.client.get('/api/notifications?category=application')
        notifs_2 = [n for n in res.get_json()['notifications'] if 'Cloud Engineer' in n['message']]
        assert len(notifs_2) == 1

    def test_pagination_bounds_and_page_param(self):
        """Verify pagination handles extreme limit values and page parameter safely."""
        self._login(self.cand_a_id)

        # Excessively large limit capped at 100
        res = self.client.get('/api/notifications?limit=999999')
        assert res.status_code == 200
        assert res.get_json()['limit'] == 100

        # Negative limit safely defaulted
        res = self.client.get('/api/notifications?limit=-10')
        assert res.status_code == 200
        assert res.get_json()['limit'] == 1

        # Page-based pagination
        res_p1 = self.client.get('/api/notifications?limit=2&page=1')
        assert res_p1.status_code == 200
        assert len(res_p1.get_json()['notifications']) == 2
        assert res_p1.get_json()['offset'] == 0

        res_p2 = self.client.get('/api/notifications?limit=2&page=2')
        assert res_p2.status_code == 200
        assert res_p2.get_json()['offset'] == 2

    def test_search_special_characters_and_sql_injection_safety(self):
        """Verify search query handles SQL special characters and injections securely."""
        self._login(self.cand_a_id)

        # SQL Injection attempt
        res = self.client.get("/api/notifications?search=' OR 1=1 --")
        assert res.status_code == 200
        assert isinstance(res.get_json()['notifications'], list)

        # SQL wildcard characters
        res = self.client.get("/api/notifications?search=%_%")
        assert res.status_code == 200
        assert isinstance(res.get_json()['notifications'], list)

        # Long search string
        long_str = "a" * 200
        res = self.client.get(f"/api/notifications?search={long_str}")
        assert res.status_code == 200
        assert len(res.get_json()['notifications']) == 0
