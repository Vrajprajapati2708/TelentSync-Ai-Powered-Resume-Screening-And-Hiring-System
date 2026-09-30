# ============================================================
#  TalentSync — System Health Endpoint (/api/health)
#  Provides automated healthcheck monitoring for Docker, K8s,
#  and load balancers. Safe: Zero secret or credential disclosure.
# ============================================================

from flask import Blueprint, jsonify
from app.services.health_service import get_system_health

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Liveness and readiness health check probe."""
    payload, code = get_system_health()
    return jsonify(payload), code
