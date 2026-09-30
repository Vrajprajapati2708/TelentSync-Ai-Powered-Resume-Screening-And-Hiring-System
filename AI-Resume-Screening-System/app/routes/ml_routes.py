# ============================================================
#  TalentSync — ML Status & Training Routes
#
#  Exposes REST endpoints for:
#    GET  /api/ml/status   — Check which models are trained
#    POST /api/ml/train    — Trigger model training (admin only)
#    POST /api/ml/pipeline — Run full inference on raw text
# ============================================================

import threading
from flask import Blueprint, jsonify, request
from app.ml.ml_pipeline import get_pipeline_status, run_full_pipeline
from app.utils.logger import get_logger
from app.utils.security import login_required, role_required
from app import limiter

logger = get_logger(__name__)

ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")

# Track background training status
_training_status = {"running": False, "last_result": None}


@ml_bp.route("/status", methods=["GET"])
def ml_status():
    """
    GET /api/ml/status

    Returns the training status and metadata for all ML models.

    Response:
        {
            "status": "ready" | "not_trained",
            "models": {
                "spacy_ner":         { trained, best_f1, epochs },
                "tfidf_recommender": { trained, vocab_size, hit_rate }
            },
            "dataset":          { num_resumes, num_jobs, ... },
            "extraction_method": "spaCy NER (Trained Model)" | "Regex Fallback"
        }
    """
    try:
        status = get_pipeline_status()
        status["training_running"] = _training_status["running"]
        status["last_training"]    = _training_status["last_result"]
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"/api/ml/status error: {e}")
        return jsonify({"error": str(e)}), 500


@ml_bp.route("/train", methods=["POST"])
@login_required
@role_required('hr')
@limiter.limit("2 per hour")
def trigger_training():
    """
    POST /api/ml/train

    Triggers model training in a background thread.
    Body (JSON, optional):
        { "skip_ner": false }

    Returns immediately with a task started message.
    Poll /api/ml/status to check progress.
    """
    if _training_status["running"]:
        return jsonify({"message": "Training already in progress.", "running": True}), 200

    data     = request.get_json(silent=True) or {}
    skip_ner = data.get("skip_ner", False)

    def _train_thread():
        import time
        _training_status["running"]     = True
        _training_status["last_result"] = None
        t_start = time.time()

        try:
            from app.ml.training.train_all import train_all
            train_all(skip_ner=skip_ner)
            elapsed = round(time.time() - t_start, 1)
            _training_status["last_result"] = {
                "success":    True,
                "elapsed_s":  elapsed,
                "message":    f"Training completed in {elapsed}s."
            }
            logger.info(f"Background training completed in {elapsed}s.")
        except Exception as e:
            logger.error(f"Background training failed: {e}")
            _training_status["last_result"] = {
                "success": False,
                "error":   str(e)
            }
        finally:
            _training_status["running"] = False

    thread = threading.Thread(target=_train_thread, daemon=True)
    thread.start()

    return jsonify({
        "message": "Training started in background. Poll /api/ml/status for updates.",
        "running": True,
        "skip_ner": skip_ner,
    }), 202


@ml_bp.route("/pipeline", methods=["POST"])
@login_required
@role_required('hr')
def run_pipeline():
    """
    POST /api/ml/pipeline

    Run the full ML inference pipeline on provided resume text.
    Useful for testing and debugging.

    Body (JSON):
        { "resume_text": "...", "jobs": [...], "top_n": 10 }

    Returns:
        Full pipeline result including skills, ATS score, recommendations.
    """
    data = request.get_json(silent=True) or {}
    resume_text = data.get("resume_text", "")
    jobs        = data.get("jobs", [])
    top_n       = data.get("top_n", 10)

    if not resume_text:
        return jsonify({"error": "resume_text is required."}), 400

    try:
        result = run_full_pipeline(resume_text, jobs, top_n=top_n)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"/api/ml/pipeline error: {e}")
        return jsonify({"error": str(e)}), 500
