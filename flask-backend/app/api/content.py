"""FR-12 Content API — query hot content ranking"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.audit import write_audit
from app.utils.validators import validate_pagination

content_bp = Blueprint("content", __name__)


@content_bp.route("/content", methods=["GET"])
@require_role("operator", "admin")
def list_content():
    """Paginated content list for the query page (content management tab)."""
    content_type = request.args.get("content_type")
    user_id = request.args.get("user_id", type=int)

    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    where = ["1=1"]
    params: dict = {}
    if content_type in ("music", "video"):
        where.append("content_type = :content_type")
        params["content_type"] = content_type

    where_clause = " AND ".join(where)

    rows = db.session.execute(
        text(
            f"SELECT content_id, content_type, hot_score, play_count, like_count, "
            f"favorite_count, share_count, completion_rate, interaction_rate "
            f"FROM rt_content_hot "
            f"WHERE {where_clause} "
            f"ORDER BY hot_score DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM rt_content_hot WHERE {where_clause}"),
        params,
    ).scalar()

    result = []
    for r in rows:
        result.append({
            "id": r.content_id,
            "title": f"{'音乐' if r.content_type == 'music' else '视频'} #{r.content_id}",
            "type": r.content_type,
            "hot_score": float(r.hot_score) if r.hot_score else 0,
            "score": float(r.hot_score) if r.hot_score else 0,
            "play_count": r.play_count,
            "like_count": r.like_count,
            "favorite_count": r.favorite_count,
            "share_count": r.share_count,
        })

    write_audit("query", "content", {"type": content_type})
    return jsonify({
        "code": 200,
        "data": result,
        "pagination": {"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size)},
    }), 200


@content_bp.route("/content/hot", methods=["GET"])
@require_role("operator", "admin")
def get_hot_content():
    content_type = request.args.get("type")  # music, video, or None for all
    top_n = min(max(int(request.args.get("top_n", 10)), 1), 100)

    sql = (
        "SELECT content_id, content_type, play_count, like_count, "
        "favorite_count, share_count, completion_rate, "
        "interaction_rate, hot_score "
        "FROM rt_content_hot "
        "WHERE window_end = (SELECT MAX(window_end) FROM rt_content_hot)"
    )
    params: dict = {}

    if content_type in ("music", "video"):
        sql += " AND content_type = :content_type"
        params["content_type"] = content_type

    sql += " ORDER BY hot_score DESC LIMIT :top_n"
    params["top_n"] = top_n

    rows = db.session.execute(text(sql), params).fetchall()

    result = []
    for c in rows:
        result.append({
            "content_id": c.content_id,
            "content_type": c.content_type,
            "play_count": c.play_count,
            "like_count": c.like_count,
            "favorite_count": c.favorite_count,
            "share_count": c.share_count,
            "completion_rate": float(c.completion_rate) if c.completion_rate else 0,
            "interaction_rate": float(c.interaction_rate) if c.interaction_rate else 0,
            "hot_score": float(c.hot_score) if c.hot_score else 0,
        })

    write_audit("query", "content/hot", {"type": content_type, "top_n": top_n})
    return jsonify({"code": 200, "data": result}), 200
