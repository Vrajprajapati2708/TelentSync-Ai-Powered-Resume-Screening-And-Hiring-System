# ============================================================
#  TalentSync — Resume Controller
#  Orchestrates: file upload → parse → ATS score → DB save
# ============================================================

import os
import uuid
import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from werkzeug.utils import secure_filename
from app.ml.parsers.resume_parser import parse_resume
from app.ml.resume_intelligence.resume_json_builder import build_resume_intelligence
from app.ml.ats.ats_checker import compute_ats_score
from app.database.connection import get_db
from app.utils.validators import validate_file_extension, validate_file_bytes
from app.utils.logger import get_logger
from app.config.settings import ActiveConfig

logger = get_logger(__name__)

# Persistent local disk storage location outside web root
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'resumes'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_upload_folder() -> str:
    """Return active upload folder (respecting testing configuration when in app context)."""
    from flask import has_app_context, current_app
    if has_app_context() and current_app.config.get("UPLOAD_FOLDER"):
        return current_app.config["UPLOAD_FOLDER"]
    from app.config.settings import _detect_testing, TestingConfig
    if _detect_testing():
        return TestingConfig.UPLOAD_FOLDER
    return getattr(ActiveConfig, "UPLOAD_FOLDER", UPLOAD_FOLDER)



def calculate_file_hash(file_stream) -> str:
    """
    Calculate 256-bit SHA-256 hash of a file stream in 64KB chunks.
    Resets stream pointer before and after calculation.
    """
    if not file_stream:
        return ""

    file_stream.seek(0)
    hasher = hashlib.sha256()

    for chunk in iter(lambda: file_stream.read(65536), b''):
        hasher.update(chunk)

    file_stream.seek(0)  # Reset pointer
    return hasher.hexdigest()


def check_duplicate_resume(user_id: int, file_hash: str) -> dict | None:
    """
    Query the resumes table for an existing upload matching (user_id, file_hash).
    Returns existing resume record dict if duplicate found, or None if unique.
    """
    if not user_id or not file_hash:
        return None

    with get_db() as conn:
        record = conn.execute(
            "SELECT * FROM resumes WHERE user_id=? AND file_hash=?",
            (user_id, file_hash)
        ).fetchone()

        if record:
            logger.info(f"Duplicate resume detected for user_id={user_id}, hash={file_hash[:8]}")
            return dict(record)

    return None



def save_resume_file_to_disk(file_stream, filename: str, user_id: int = 0) -> tuple:
    """
    Save an uploaded resume stream to persistent disk with a secure UUID filename.
    Preserves original filename in metadata while avoiding path traversal risks.
    Returns (success, result_dict_or_error_msg).
    """
    if not file_stream or not filename:
        return False, "File stream and filename are required."

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    stored_filename = f"res_{user_id}_{uuid.uuid4().hex[:12]}.{ext}"
    target_folder = get_upload_folder()
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, stored_filename)

    # Preserve Unicode original filename cleanly
    clean_original = os.path.basename(filename).strip()
    if not clean_original:
        clean_original = secure_filename(filename) or f"resume.{ext}"

    try:
        file_stream.seek(0)
        with open(file_path, 'wb') as out_f:
            out_f.write(file_stream.read())
        file_stream.seek(0)  # Reset pointer for downstream text parsing

        file_size_bytes = os.path.getsize(file_path)
        mime_type = 'application/pdf' if ext == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        logger.info(f"File saved to disk: {stored_filename} ({file_size_bytes} bytes)")
        return True, {
            'stored_filename': stored_filename,
            'file_path': file_path,
            'original_name': clean_original,
            'file_size_bytes': file_size_bytes,
            'mime_type': mime_type
        }
    except Exception as e:
        logger.error(f"Disk write error for {filename}: {e}")
        return False, "Failed to save file to server storage."



def process_resume_upload(file, user_id: int | None = None) -> dict:
    """
    Full production resume processing pipeline (v1.0 Core Integration):
      1. Validate file stream, extension, size, and magic-bytes (`validate_file_bytes`)
      2. Compute SHA-256 hash and check duplicate status (`calculate_file_hash`, `check_duplicate_resume`)
      3. Orchestrate Resume Intelligence pipeline (`build_resume_intelligence`)
      4. Compute ATS score (`compute_ats_score`)
      5. Save binary file stream to persistent UUID storage (`save_resume_file_to_disk`)
      6. Perform DB transactional write to `resumes` table (including `structured_json`) & sync candidate profile `users` record.
    """
    if file is None or not getattr(file, 'filename', ''):
        return {'success': False, 'message': 'No file selected for upload.'}

    raw_filename = file.filename
    file_stream  = getattr(file, 'stream', file)

    # Step 1: Magic-Byte, Size, and Extension Validation
    valid, val_msg = validate_file_bytes(file_stream, raw_filename)
    if not valid:
        return {'success': False, 'message': val_msg}

    # Step 2: Calculate SHA-256 hash & Check Duplicate Status
    file_hash = calculate_file_hash(file_stream)

    if user_id:
        existing_dup = check_duplicate_resume(user_id, file_hash)
        if existing_dup:
            logger.info(f"Duplicate resume detected for user_id={user_id}, resume_id={existing_dup['id']}")
            return {
                'success': True,
                'is_duplicate': True,
                'message': 'Duplicate resume file detected. Profile synced with existing upload.',
                'resume_id': existing_dup['id'],
                'stored_filename': existing_dup['stored_filename'],
                'data': {
                    'skills': existing_dup['extracted_skills'].split(',') if existing_dup['extracted_skills'] else [],
                    'ats_score': existing_dup['ats_score'],
                    'word_count': existing_dup['word_count'],
                }
            }

    # Step 3: Resume Intelligence Orchestration (RI-08)
    intel = build_resume_intelligence(file_stream, raw_filename)
    meta = intel.get('metadata', {})
    if meta.get('parse_status') == 'failed' or not intel.get('raw_text', '').strip():
        err_msg = meta.get('parse_errors', ['Could not extract text from resume.'])[0] if meta.get('parse_errors') else 'Could not extract text from resume.'
        return {'success': False, 'message': err_msg}

    raw_text = intel['raw_text']

    # Step 4: Compute ATS Score & Serialize Canonical Intelligence JSON
    ats_result = compute_ats_score(raw_text)
    ats_score  = ats_result['score']

    skills_list = [s['name'] for s in intel.get('skills', [])] if intel.get('skills') else []
    skills_str  = ','.join(skills_list)
    word_count  = len(raw_text.split())

    # UTF-8 safe deterministic JSON serialization
    structured_json_str = json.dumps(intel, ensure_ascii=False)

    # Map contact and degree for legacy response format
    email = intel['contact']['email'] or ''
    phone = intel['contact']['phone'] or ''
    linkedin = intel['contact']['linkedin'] or ''
    github = intel['contact']['github'] or ''

    degree = ''
    if intel.get('education'):
        first_degree = intel['education'][0].get('degree')
        if first_degree:
            degree = str(first_degree).upper()

    skill_categories = {}
    for s in intel.get('skills', []):
        cat = s.get('category', 'General Technical')
        skill_categories.setdefault(cat, []).append(s['name'])

    # Step 5: Save Binary to Storage Engine
    saved_ok, save_res = save_resume_file_to_disk(file_stream, raw_filename, user_id=user_id or 0)
    if not saved_ok:
        return {'success': False, 'message': save_res}

    # Step 6: Transactional DB Insertion & Profile Sync
    resume_id = None
    if user_id:
        try:
            with get_db() as conn:
                # 6a. Insert into resumes metadata table (including structured_json)
                cur = conn.execute(
                    """INSERT INTO resumes 
                       (user_id, original_name, stored_filename, file_path, file_hash, file_size_bytes, mime_type, parsed_text, word_count, ats_score, extracted_skills, structured_json, status, version)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', 1)""",
                    (
                        user_id,
                        save_res['original_name'],
                        save_res['stored_filename'],
                        save_res['file_path'],
                        file_hash,
                        save_res['file_size_bytes'],
                        save_res['mime_type'],
                        raw_text,
                        word_count,
                        ats_score,
                        skills_str,
                        structured_json_str
                    )
                )
                resume_id = cur.lastrowid

                # 6b. Update user candidate profile
                conn.execute(
                    "UPDATE users SET skills=?, ats_score=? WHERE id=?",
                    (skills_str, ats_score, user_id)
                )

                # 6c. Insert event notification
                cur_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                conn.execute(
                    """INSERT INTO notifications 
                       (user_id, title, message, type, action_type, action_target, metadata, created_at)
                       VALUES (?, ?, ?, 'system', 'view_ats', '#cand-ats', ?, ?)""",
                    (
                        user_id,
                        'Resume Processed & Scored ✨',
                        f"Your resume was analyzed with an ATS Score of {ats_score}/100 and {len(skills_list)} extracted skills.",
                        json.dumps({'resume_id': resume_id, 'ats_score': ats_score, 'skills_count': len(skills_list)}),
                        cur_time
                    )
                )
                conn.commit()

            logger.info(f"Resume uploaded & inserted: resume_id={resume_id}, user_id={user_id}, score={ats_score}")
        except Exception as db_err:
            logger.error(f"DB transaction failed, removing disk file {save_res['file_path']}: {db_err}")
            if os.path.exists(save_res['file_path']):
                try:
                    os.remove(save_res['file_path'])
                except Exception:
                    pass
            return {'success': False, 'message': 'Database operation failed.'}

    return {
        'success': True,
        'message': 'Resume parsed, scored, and saved successfully.',
        'resume_id': resume_id,
        'data': {
            'skills':           skills_list,
            'ats_score':        ats_score,
            'ats_grade':        ats_result['grade'],
            'suggestions':      ats_result['suggestions'],
            'breakdown':        ats_result['breakdown'],
            'email':            email,
            'phone':            phone,
            'linkedin':         linkedin,
            'github':           github,
            'degree':           degree,
            'skill_categories': skill_categories,
            'word_count':       word_count,
            'intel':            intel
        }
    }


def delete_resume_by_id(
    resume_id: int,
    current_user_id: Optional[int] = None,
    current_user_role: Optional[str] = None
) -> dict:
    """
    Securely delete a resume record and its physical storage file.

    Invariants:
      1. Authentication & Ownership:
         - Candidate can delete only their own resume (resume['user_id'] == current_user_id).
         - HR cannot delete candidate resumes (returns 403).
         - Admin can delete any resume (moderation / oversight).
      2. Path Traversal & Disk Safety:
         - Canonicalizes upload folder and stored_filename.
         - Strictly ensures target path is jailed inside the upload folder.
         - Removes physical file safely; if already missing on disk, succeeds gracefully.
      3. Referential Integrity & Database Atomicity:
         - Atomically removes resume record inside a transaction.
         - Recalculates candidate's latest ats_score and skills from remaining resumes.
         - Leaves applications table and candidate profile intact.
      4. Cache & Audit:
         - Invalidates per-user ranked jobs cache.
         - Inserts an audit notification into notifications table.
    """
    if not resume_id or not isinstance(resume_id, int):
        return {'success': False, 'message': 'Invalid resume ID.', 'status_code': 400}

    try:
        with get_db() as conn:
            resume = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
    except Exception as e:
        logger.error(f"Database error fetching resume {resume_id}: {e}")
        return {'success': False, 'message': 'Database error during resume deletion.', 'status_code': 500}

    if not resume:
        return {'success': False, 'message': 'Resume not found.', 'status_code': 404}

    owner_id = resume['user_id']

    if not current_user_id:
        return {
            'success': False,
            'message': 'Authentication required. Please log in.',
            'status_code': 401
        }

    # Ownership Authorization Guard
    if current_user_role == 'candidate' and owner_id != current_user_id:
        logger.warning(f"IDOR attempt: User {current_user_id} tried to delete resume {resume_id} belonging to user {owner_id}")
        return {
            'success': False,
            'message': 'Unauthorized. You do not have permission to delete this resume.',
            'status_code': 403
        }

    if current_user_role == 'hr' and owner_id != current_user_id:
        logger.warning(f"HR unauthorized delete attempt: HR user {current_user_id} tried to delete candidate resume {resume_id}")
        return {
            'success': False,
            'message': 'Unauthorized. HR recruiters cannot delete candidate resumes.',
            'status_code': 403
        }

    if current_user_role not in ('candidate', 'hr', 'admin'):
        return {
            'success': False,
            'message': 'Unauthorized. Insufficient permissions.',
            'status_code': 403
        }

    # Path Traversal & Jail Protection
    upload_dir = os.path.realpath(get_upload_folder())
    raw_filename = resume['stored_filename'] or ''
    base_filename = os.path.basename(raw_filename)

    if not base_filename or base_filename != raw_filename or '..' in raw_filename:
        logger.error(f"Path traversal attempt detected in stored_filename: {raw_filename}")
        return {
            'success': False,
            'message': 'Security error. Invalid stored filename.',
            'status_code': 400
        }

    target_path = os.path.realpath(os.path.join(upload_dir, base_filename))
    if not target_path.startswith(upload_dir + os.sep) and target_path != upload_dir:
        logger.error(f"Path escape detected: {target_path} is outside upload directory {upload_dir}")
        return {
            'success': False,
            'message': 'Security error. File path escape detected.',
            'status_code': 400
        }

    # Transactional Database Deletion & Candidate Profile Sync
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM resumes WHERE id=?", (resume_id,))

            # Recalculate profile state from remaining resumes for this user
            remaining = conn.execute(
                "SELECT ats_score, extracted_skills FROM resumes WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (owner_id,)
            ).fetchone()

            if remaining:
                conn.execute(
                    "UPDATE users SET ats_score=?, skills=? WHERE id=?",
                    (remaining['ats_score'] or 0, remaining['extracted_skills'] or '', owner_id)
                )
            else:
                conn.execute(
                    "UPDATE users SET ats_score=0, skills='' WHERE id=?",
                    (owner_id,)
                )

            # Insert audit notification
            conn.execute(
                """INSERT INTO notifications (user_id, title, message, type, created_at)
                   VALUES (?, ?, ?, 'info', ?)""",
                (
                    owner_id,
                    'Resume Deleted 🗑️',
                    f"Resume '{resume['original_name']}' was successfully deleted.",
                    datetime.now().strftime('%Y-%m-%d %H:%M')
                )
            )
            conn.commit()

    except Exception as e:
        logger.error(f"Database error deleting resume {resume_id}: {e}")
        return {
            'success': False,
            'message': 'Database error during resume deletion.',
            'status_code': 500
        }

    # Physical File Deletion (after DB commit)
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
            logger.info(f"Physical resume file removed: {target_path}")
        except Exception as file_err:
            logger.warning(f"Could not remove physical resume file {target_path}: {file_err}")
    else:
        logger.info(f"Physical resume file was already absent on disk: {target_path}")

    # Invalidate user ranked cache
    try:
        from app.routes.resume_routes import invalidate_user_ranked_cache
        invalidate_user_ranked_cache(owner_id)
    except Exception:
        pass

    logger.info(f"Resume {resume_id} deleted successfully by user {current_user_id} ({current_user_role})")
    return {
        'success': True,
        'message': 'Resume deleted successfully.',
        'deleted_id': resume_id,
        'status_code': 200
    }


