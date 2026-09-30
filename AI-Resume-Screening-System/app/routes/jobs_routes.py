"""
Jobs Routes — Unified Search Endpoint
GET /api/jobs/search (auth required, candidate role)
"""
from flask import Blueprint, request, jsonify, session
from app import limiter
from app.utils.security import login_required, role_required
from app.services.jobs_search_service import JobsSearchService
from app.utils.logger import get_logger

logger = get_logger(__name__)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')
jobs_v1_bp = Blueprint('jobs_v1', __name__, url_prefix='/api/v1/jobs')

search_service = JobsSearchService()

VALID_WORK_MODES = {'any', 'remote', 'onsite', 'hybrid'}
VALID_EXPERIENCE = {'any', '0-1', '1-3', '3-5', '5-8', '8+'}
VALID_SOURCES = {'all', 'adzuna', 'internal'}
VALID_SORTS = {'relevance', 'newest', 'salary'}


def handle_jobs_search():
    """
    Search jobs with comprehensive validation and error hierarchy.
    """
    # 1. Parse & Sanitize 'q' (max 100 chars, stripped)
    q = request.args.get('q', '').strip()
    if len(q) > 100:
        q = q[:100].strip()

    # 2. Parse & Sanitize 'location' (max 100 chars, stripped)
    location = request.args.get('location', '').strip()
    if len(location) > 100:
        location = location[:100].strip()

    # 3. Validate 'work_mode' enum
    work_mode = request.args.get('work_mode', 'any').strip().lower()
    if work_mode not in VALID_WORK_MODES:
        return jsonify({
            'success': False,
            'message': f"Invalid work_mode '{work_mode}'. Must be one of: {', '.join(sorted(VALID_WORK_MODES))}."
        }), 400

    # 4. Validate 'min_salary' integer (annual INR)
    raw_salary = request.args.get('min_salary', '0').strip()
    try:
        min_salary = int(raw_salary)
        if min_salary < 0:
            return jsonify({
                'success': False,
                'message': "min_salary must be a non-negative integer."
            }), 400
    except ValueError:
        return jsonify({
            'success': False,
            'message': f"Invalid min_salary '{raw_salary}'. Must be an integer."
        }), 400

    # 5. Validate 'experience' enum
    experience = request.args.get('experience', 'any').strip().lower()
    if experience == 'fresher':
        experience = '0-1'
    if experience not in VALID_EXPERIENCE:
        return jsonify({
            'success': False,
            'message': f"Invalid experience '{experience}'. Must be one of: {', '.join(sorted(VALID_EXPERIENCE))}."
        }), 400

    # 6. Validate 'source' enum
    source = request.args.get('source', 'all').strip().lower()
    if source not in VALID_SOURCES:
        return jsonify({
            'success': False,
            'message': f"Invalid source '{source}'. Must be one of: {', '.join(sorted(VALID_SOURCES))}."
        }), 400

    # 7. Validate 'sort' enum
    sort_by = request.args.get('sort', 'relevance').strip().lower()
    if sort_by not in VALID_SORTS:
        return jsonify({
            'success': False,
            'message': f"Invalid sort '{sort_by}'. Must be one of: {', '.join(sorted(VALID_SORTS))}."
        }), 400

    # 8. Validate 'page' int
    raw_page = request.args.get('page', '1').strip()
    try:
        page = int(raw_page)
        if page < 1:
            return jsonify({
                'success': False,
                'message': "page must be greater than or equal to 1."
            }), 400
    except ValueError:
        return jsonify({
            'success': False,
            'message': f"Invalid page '{raw_page}'. Must be an integer."
        }), 400

    # 9. Validate 'per_page' int (clamp 1..50)
    raw_per_page = request.args.get('per_page', '10').strip()
    try:
        per_page = int(raw_per_page)
        if per_page < 1:
            return jsonify({
                'success': False,
                'message': "per_page must be greater than or equal to 1."
            }), 400
        per_page = min(per_page, 50)
    except ValueError:
        return jsonify({
            'success': False,
            'message': f"Invalid per_page '{raw_per_page}'. Must be an integer."
        }), 400

    # 10. Execute search via service
    user_id = session.get('user_id')
    params = {
        'q': q,
        'location': location,
        'work_mode': work_mode,
        'min_salary': min_salary,
        'experience': experience,
        'source': source,
        'sort': sort_by,
        'page': page,
        'per_page': per_page
    }

    try:
        result = search_service.search(params, user_id=user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error executing jobs search: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': "An unexpected error occurred while searching for jobs. Please try again."
        }), 500


@jobs_bp.route('/search', methods=['GET'])
@login_required
@role_required('candidate', 'hr', 'admin')
@limiter.limit("30 per minute")
def api_jobs_search():
    return handle_jobs_search()


@jobs_v1_bp.route('/search', methods=['GET'])
@login_required
@role_required('candidate', 'hr', 'admin')
@limiter.limit("30 per minute")
def api_jobs_search_v1():
    return handle_jobs_search()
