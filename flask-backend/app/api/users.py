"""FR-12 GET /api/users/profile — query user portrait/profile"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.audit import write_audit

users_bp = Blueprint("users", __name__)


@users_bp.route("/users/profile", methods=["GET"])
@require_role("operator", "admin")
def get_user_profile():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"code": 400, "message": "user_id is required"}), 400

    rt_profile = db.session.execute(
        text(
            "SELECT * FROM rt_user_profile WHERE user_id = :user_id "
            "ORDER BY window_end DESC LIMIT 1"
        ),
        {"user_id": user_id},
    ).fetchone()

    offline_portrait = db.session.execute(
        text("SELECT * FROM offline_user_portrait WHERE user_id = :user_id"),
        {"user_id": user_id},
    ).fetchone()

    result = {"user_id": user_id, "real_time": None, "offline": None}

    if rt_profile:
        result["real_time"] = {
            "window_start": str(rt_profile.window_start),
            "window_end": str(rt_profile.window_end),
            "play_count": rt_profile.play_count,
            "completion_rate": float(rt_profile.completion_rate),
            "like_rate": float(rt_profile.like_rate),
            "favorite_rate": float(rt_profile.favorite_rate),
            "skip_rate": float(rt_profile.skip_rate),
            "share_count": rt_profile.share_count,
            "comment_count": rt_profile.comment_count,
            "preference_distribution": rt_profile.preference_distribution,
            "active_hours": rt_profile.active_hours,
            "is_cold_start": bool(rt_profile.is_cold_start),
            "behavior_count": rt_profile.behavior_count,
            "content_type_ratio": rt_profile.content_type_ratio,
        }

    if offline_portrait:
        result["offline"] = {
            "long_term_tags": offline_portrait.long_term_tags,
            "preference_vector": offline_portrait.preference_vector,
            "lifecycle_stage": offline_portrait.lifecycle_stage,
            "total_behaviors": offline_portrait.total_behaviors,
            "avg_session_duration": float(offline_portrait.avg_session_duration),
            "active_days_last_30": offline_portrait.active_days_last_30,
            "last_active_time": str(offline_portrait.last_active_time) if offline_portrait.last_active_time else None,
            "favorite_content_type": offline_portrait.favorite_content_type,
            "cluster_id": offline_portrait.cluster_id,
            "tag_version": offline_portrait.tag_version,
            "compute_time": str(offline_portrait.compute_time),
        }

    write_audit("query", "users/profile", {"user_id": user_id})
    return jsonify({"code": 200, "data": result}), 200
