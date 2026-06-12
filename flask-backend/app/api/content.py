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
        where.append("c.content_type = :content_type")
        params["content_type"] = content_type

    where_clause = " AND ".join(where)

    rows = db.session.execute(
        text(
            f"SELECT c.content_id, c.content_type, c.hot_score, c.play_count, c.like_count, "
            f"c.favorite_count, c.share_count, c.completion_rate, c.interaction_rate, "
            f"COALESCE(m.title, CONCAT(IF(c.content_type='music','音乐','视频'), ' #', c.content_id)) AS title "
            f"FROM rt_content_hot c "
            f"LEFT JOIN content_metadata m ON c.content_id = m.content_id AND c.content_type = m.content_type "
            f"WHERE {where_clause} "
            f"ORDER BY c.hot_score DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(f"SELECT COUNT(*) FROM rt_content_hot c WHERE {where_clause}"),
        params,
    ).scalar()

    result = []
    for r in rows:
        result.append({
            "id": r.content_id,
            "title": r.title,
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
        "SELECT h.content_id, h.content_type, h.play_count, h.like_count, "
        "h.favorite_count, h.share_count, h.completion_rate, "
        "h.interaction_rate, h.hot_score, "
        "COALESCE(m.title, CONCAT(IF(h.content_type='music','音乐','视频'), ' #', h.content_id)) AS title "
        "FROM rt_content_hot h "
        "LEFT JOIN content_metadata m ON h.content_id = m.content_id AND h.content_type = m.content_type "
    )
    params: dict = {}

    where = []
    if content_type in ("music", "video"):
        where.append("h.content_type = :content_type")
        params["content_type"] = content_type

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY h.hot_score DESC LIMIT :top_n"
    params["top_n"] = top_n

    rows = db.session.execute(text(sql), params).fetchall()

    result = []
    for c in rows:
        result.append({
            "content_id": c.content_id,
            "content_type": c.content_type,
            "title": c.title,
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


@content_bp.route("/content/<int:content_id>", methods=["GET"])
@require_role("operator", "admin")
def get_content_detail(content_id):
    content_type = request.args.get("type")
    where = ["m.content_id = :content_id"]
    params = {"content_id": content_id}
    if content_type in ("music", "video"):
        where.append("m.content_type = :content_type")
        params["content_type"] = content_type

    row = db.session.execute(
        text(
            "SELECT m.content_id, m.content_type, m.title, m.artist_or_author, "
            "m.style_or_category, m.tags, m.duration, m.language, m.bpm "
            "FROM content_metadata m WHERE " + " AND ".join(where) + " LIMIT 1"
        ), params
    ).fetchone()

    if not row:
        return jsonify({"code": 404, "message": "Content not found"}), 404

    return jsonify({"code": 200, "data": {
        "content_id": row.content_id,
        "content_type": row.content_type,
        "title": row.title,
        "artist_or_author": row.artist_or_author,
        "style_or_category": row.style_or_category,
        "tags": row.tags,
        "duration": float(row.duration) if row.duration else 0,
        "language": row.language,
        "bpm": float(row.bpm) if row.bpm else 0,
    }}), 200
