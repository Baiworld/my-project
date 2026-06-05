"""FR-12 GET /api/coldstart/analysis — coldstart user cluster analysis"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.audit import write_audit
from app.utils.validators import validate_pagination

coldstart_bp = Blueprint("coldstart", __name__)


@coldstart_bp.route("/coldstart/analysis", methods=["GET"])
@require_role("operator", "admin")
def get_coldstart_analysis():
    content_type = request.args.get("content_type")

    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    # Query coldstart user profiles with pagination
    where = ["is_cold_start = 1"]
    params: dict = {}
    if content_type in ("music", "video"):
        where.append("JSON_EXTRACT(content_type_ratio, '$.video') IS NOT NULL")
        params["content_type"] = content_type

    where_clause = " AND ".join(where)

    rows = db.session.execute(
        text(
            f"SELECT id, user_id, behavior_count, play_count, like_rate, "
            f"favorite_rate, share_count, comment_count, content_type_ratio "
            f"FROM rt_user_profile "
            f"WHERE {where_clause} "
            f"ORDER BY id DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM rt_user_profile WHERE {where_clause}"),
        params,
    ).scalar()

    result = []
    for r in rows:
        result.append({
            "id": r.user_id,
            "user_id": r.user_id,
            "title": f"冷启动用户 #{r.user_id}",
            "type": "music",
            "hot_score": float(r.play_count or 0),
            "score": float(r.like_rate or 0) * 100,
            "behavior_count": r.behavior_count,
            "play_count": r.play_count,
            "like_rate": float(r.like_rate or 0),
            "favorite_rate": float(r.favorite_rate or 0),
            "share_count": r.share_count,
            "comment_count": r.comment_count,
        })

    write_audit("query", "coldstart/analysis")
    return jsonify({
        "code": 200,
        "data": result,
        "pagination": {"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size)},
    }), 200
