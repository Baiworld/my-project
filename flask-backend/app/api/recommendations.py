"""FR-12 GET /api/recommendations — query user recommendation list"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.validators import validate_pagination
from app.utils.audit import write_audit

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.route("/recommendations", methods=["GET"])
@require_role("operator", "admin")
def get_recommendations():
    user_id = request.args.get("user_id", type=int)
    content_type = request.args.get("content_type")  # music, video, or None for all

    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    where = ["1=1"]
    params: dict = {}
    if user_id:
        where.append("r.user_id = :user_id")
        params["user_id"] = user_id
    if content_type in ("music", "video"):
        where.append("r.content_type = :content_type")
        params["content_type"] = content_type

    where_clause = " AND ".join(where)

    rows = db.session.execute(
        text(
            f"SELECT r.user_id, r.content_id, r.content_type, r.`rank`, r.score, r.reason, r.strategy, "
            f"COALESCE(m.title, CONCAT(IF(r.content_type='music','音乐','视频'), ' #', r.content_id)) AS title "
            f"FROM offline_recommendations r "
            f"LEFT JOIN content_metadata m ON r.content_id = m.content_id AND r.content_type = m.content_type "
            f"WHERE {where_clause} "
            f"ORDER BY r.`rank` LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(
            f"SELECT COUNT(*) FROM offline_recommendations r WHERE {where_clause}"
        ),
        params,
    ).scalar()

    result = []
    for r in rows:
        result.append({
            "id": r.content_id,
            "user_id": r.user_id,
            "title": r.title,
            "type": r.content_type,
            "rank": r.rank,
            "score": float(r.score),
            "hot_score": float(r.score),
            "reason": r.reason,
            "strategy": r.strategy,
        })

    write_audit("query", "recommendations", {"user_id": user_id})
    return jsonify({
        "code": 200,
        "data": result,
        "pagination": {"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size)},
    }), 200
