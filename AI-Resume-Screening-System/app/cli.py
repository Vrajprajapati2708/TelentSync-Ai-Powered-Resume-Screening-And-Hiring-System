# ============================================================
#  TalentSync / HireAI — Management CLI
#  Secure server-side bootstrap and administrative tooling.
#  Usage:
#    python -m app.cli create-admin [OPTIONS]
# ============================================================

import argparse
import getpass
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from werkzeug.security import generate_password_hash

from app.database.connection import get_db, is_postgres
from app.utils.logger import get_logger
from app.utils.validators import validate_email, validate_password

logger = get_logger(__name__)


def bootstrap_admin(
    email: str,
    password: Optional[str] = None,
    name: Optional[str] = None,
    promote: bool = False,
    db_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Atomically provision or promote a Platform Administrator account.

    Safety invariants enforced:
      1. Validates email format strictly using existing validator.
      2. If account already has role='admin', safe idempotent no-op (no duplicates).
      3. If account exists with role in ('candidate', 'hr'):
         - Rejects promotion if account is unverified (is_verified != 1).
         - Requires explicit promote=True confirmation.
         - Atomically promotes role to 'admin' and sets is_verified=1.
      4. If account does not exist:
         - Requires valid password conforming to existing policy (10-128 chars).
         - Securely hashes password via werkzeug generate_password_hash.
         - Atomically inserts new user with role='admin' and is_verified=1.
      5. Plaintext passwords and hashes are never printed or logged.
      6. Rollback on any failure ensures atomic database state.

    Returns:
      dict with keys: 'success' (bool), 'message' (str), 'action' (str),
      'user_id' (Optional[int]), and optional 'status_code' (int).
    """
    if not email or not isinstance(email, str) or not email.strip():
        return {
            'success': False,
            'message': 'Email address is required.',
            'action': 'invalid_email',
            'status_code': 400
        }

    clean_email = email.strip().lower()
    if not validate_email(clean_email):
        return {
            'success': False,
            'message': 'Invalid email address format.',
            'action': 'invalid_email',
            'status_code': 400
        }

    if db_file:
        if is_postgres():
            return {
                'success': False,
                'message': "Cannot use '--db' SQLite file override when PostgreSQL (DATABASE_URL) is configured.",
                'action': 'invalid_db_engine',
                'status_code': 400
            }
        if not os.path.isfile(db_file):
            return {
                'success': False,
                'message': f"Target database file not found: '{db_file}'. The bootstrap command will not create an uninitialized database.",
                'action': 'db_not_found',
                'status_code': 404
            }

    try:
        with get_db(db_file=db_file) as conn:
            user = conn.execute(
                "SELECT id, name, email, role, is_verified FROM users WHERE LOWER(email) = ?",
                (clean_email,)
            ).fetchone()

            # CASE 1: Account already exists as an administrator
            if user and user['role'] == 'admin':
                logger.info(f"Admin bootstrap: Account '{clean_email}' is already an admin (id={user['id']})")
                return {
                    'success': True,
                    'message': f"Account '{clean_email}' is already a Platform Administrator. No changes made.",
                    'action': 'already_admin',
                    'user_id': user['id'],
                    'status_code': 200
                }

            # CASE 2: Account exists as candidate or HR
            if user:
                current_role = user['role']
                is_ver = user['is_verified']

                # Reject unverified account promotion
                if is_ver != 1:
                    logger.warning(f"Admin bootstrap rejected: Account '{clean_email}' is unverified (is_verified={is_ver})")
                    return {
                        'success': False,
                        'message': f"Cannot promote unverified account '{clean_email}' to administrator. Account must be verified first.",
                        'action': 'rejected_unverified',
                        'user_id': user['id'],
                        'status_code': 400
                    }

                if not promote:
                    return {
                        'success': False,
                        'message': f"Account '{clean_email}' already exists with role '{current_role}'. Specify --promote to elevate this verified user.",
                        'action': 'requires_promote',
                        'user_id': user['id'],
                        'status_code': 409
                    }

                # Atomic promotion of verified account
                conn.execute(
                    "UPDATE users SET role = 'admin', is_verified = 1 WHERE id = ?",
                    (user['id'],)
                )

                # Insert audit notification
                conn.execute(
                    """INSERT INTO notifications (user_id, title, message, type, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        user['id'],
                        'Role Elevated to Platform Administrator 🛡️',
                        'Your account has been granted Platform Administrator privileges via secure management bootstrap.',
                        'info',
                        datetime.now().strftime('%Y-%m-%d %H:%M')
                    )
                )
                conn.commit()

                logger.info(f"Admin bootstrap: User '{clean_email}' (id={user['id']}) promoted from {current_role} to admin")
                return {
                    'success': True,
                    'message': f"Verified user '{clean_email}' successfully promoted to Platform Administrator.",
                    'action': 'promoted',
                    'user_id': user['id'],
                    'status_code': 200
                }

            # CASE 3: Account does not exist (Create new admin user)
            if promote:
                return {
                    'success': False,
                    'message': f"Account '{clean_email}' not found. Cannot promote non-existent user.",
                    'action': 'not_found',
                    'status_code': 404
                }

            if not password:
                return {
                    'success': False,
                    'message': 'Password is required to create a new administrator account.',
                    'action': 'missing_password',
                    'status_code': 400
                }

            # Validate password against project policy
            ok, err = validate_password(password)
            if not ok:
                return {
                    'success': False,
                    'message': err,
                    'action': 'invalid_password',
                    'status_code': 400
                }

            hashed_password = generate_password_hash(password)
            admin_name = (name or "Platform Administrator").strip()

            cur = conn.execute(
                """INSERT INTO users (name, email, password, role, is_verified, created_at)
                   VALUES (?, ?, ?, 'admin', 1, ?)""",
                (
                    admin_name,
                    clean_email,
                    hashed_password,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            user_id = cur.lastrowid

            conn.execute(
                """INSERT INTO notifications (user_id, title, message, type, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    'Welcome Platform Administrator 🛡️',
                    'Platform Administrator account provisioned via secure management bootstrap.',
                    'info',
                    datetime.now().strftime('%Y-%m-%d %H:%M')
                )
            )
            conn.commit()

            logger.info(f"Admin bootstrap: New Platform Administrator created: {clean_email} (id={user_id})")
            return {
                'success': True,
                'message': f"Platform Administrator '{clean_email}' created successfully.",
                'action': 'created',
                'user_id': user_id,
                'status_code': 201
            }

    except Exception as e:
        logger.error(f"Admin bootstrap transaction failed: {e}")
        return {
            'success': False,
            'message': 'Database transaction failed during administrator provisioning.',
            'action': 'db_error',
            'error': str(e),
            'status_code': 500
        }


def main():
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="TalentSync / HireAI Management & Administrative CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available management commands")

    # Command: create-admin
    admin_parser = subparsers.add_parser(
        "create-admin",
        help="Securely provision or promote a Platform Administrator"
    )
    admin_parser.add_argument("--email", "-e", help="Administrator email address")
    admin_parser.add_argument("--password", "-p", help="Administrator password (prompted securely if omitted)")
    admin_parser.add_argument("--name", "-n", help="Administrator full name (default: Platform Administrator)")
    admin_parser.add_argument("--promote", action="store_true", help="Promote existing verified user if email exists")
    admin_parser.add_argument("--db", help="Path to SQLite database file (optional override; defaults to active configured database)")

    args = parser.parse_args()

    if not args.command or args.command == "create-admin":
        email = args.email
        password = args.password
        name = args.name
        promote = args.promote
        db_file = args.db

        if db_file:
            if is_postgres():
                print("[ERROR] Cannot use '--db' SQLite file override when PostgreSQL (DATABASE_URL) is configured.", file=sys.stderr)
                sys.exit(1)
            if not os.path.isfile(db_file):
                print(f"[ERROR] Target database file not found: '{db_file}'. The bootstrap command will not create an uninitialized database.", file=sys.stderr)
                sys.exit(1)

        try:
            # Interactive collection if email not provided
            if not email:
                try:
                    email = input("Administrator email: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n[ABORTED] Operation cancelled by user.")
                    sys.exit(130)

            # Check if user already exists
            user_exists = False
            user_role = None
            user_verified = False
            try:
                with get_db(db_file=db_file) as conn:
                    row = conn.execute(
                        "SELECT role, is_verified FROM users WHERE LOWER(email) = ?",
                        (email.strip().lower(),)
                    ).fetchone()
                    if row:
                        user_exists = True
                        user_role = row['role']
                        user_verified = bool(row['is_verified'])
            except Exception as e:
                print(f"[ERROR] Database access failed: {e}", file=sys.stderr)
                sys.exit(1)

            # If user exists as candidate/hr, check promotion intent
            if user_exists and user_role in ('candidate', 'hr') and not promote:
                if sys.stdin.isatty():
                    try:
                        resp = input(f"Account exists with role '{user_role}'. Promote to admin? [y/N]: ").strip().lower()
                        if resp == 'y':
                            promote = True
                        else:
                            print("[CANCELLED] Promotion cancelled.")
                            sys.exit(0)
                    except (EOFError, KeyboardInterrupt):
                        print("\n[ABORTED] Operation cancelled by user.")
                        sys.exit(130)

            # If new user and password not provided, collect securely via getpass
            if not user_exists and not password:
                if sys.stdin.isatty():
                    try:
                        pw1 = getpass.getpass("Administrator password: ")
                        pw2 = getpass.getpass("Confirm password: ")
                        if pw1 != pw2:
                            print("[ERROR] Passwords do not match.", file=sys.stderr)
                            sys.exit(1)
                        password = pw1
                    except (EOFError, KeyboardInterrupt):
                        print("\n[ABORTED] Operation cancelled by user.")
                        sys.exit(130)
                else:
                    print("[ERROR] Password is required in non-interactive mode. Use --password.", file=sys.stderr)
                    sys.exit(1)

            # Execute bootstrap
            result = bootstrap_admin(
                email=email,
                password=password,
                name=name,
                promote=promote,
                db_file=db_file
            )

            if result['success']:
                print(f"[SUCCESS] {result['message']}")
                sys.exit(0)
            else:
                print(f"[ERROR] {result['message']}", file=sys.stderr)
                sys.exit(1)

        except KeyboardInterrupt:
            print("\n[ABORTED] Operation cancelled by user.")
            sys.exit(130)
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
