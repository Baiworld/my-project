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
    keyword = request.args.get("keyword")

    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    where = ["1=1"]
    params: dict = {}
    if content_type in ("music", "video"):
        where.append("c.content_type = :content_type")
        params["content_type"] = content_type
    if keyword:
        where.append("(m.title LIKE :kw OR m.artist_or_author LIKE :kw OR m.tags LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    where_clause = " AND ".join(where)

    rows = db.session.execute(
        text(
            f"SELECT c.content_id, c.content_type, MAX(c.hot_score) as hot_score, MAX(c.play_count) as play_count, "
            f"MAX(c.like_count) as like_count, MAX(c.favorite_count) as favorite_count, "
            f"MAX(c.share_count) as share_count, AVG(c.completion_rate) as completion_rate, "
            f"AVG(c.interaction_rate) as interaction_rate, "
            f"COALESCE(MAX(m.title), CONCAT(IF(MAX(c.content_type)='music','音乐','视频'), ' #', MAX(c.content_id))) AS title, "
            f"MAX(m.artist_or_author) as artist_or_author, MAX(m.style_or_category) as style_or_category, "
            f"MAX(m.tags) as tags, MAX(m.duration) as duration, MAX(m.language) as language, MAX(m.bpm) as bpm "
            f"FROM rt_content_hot c "
            f"LEFT JOIN content_metadata m ON c.content_id = m.content_id AND c.content_type = m.content_type "
            f"WHERE {where_clause} "
            f"GROUP BY c.content_id, c.content_type "
            f"ORDER BY MAX(c.hot_score) DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(
            f"SELECT COUNT(DISTINCT c.content_id, c.content_type) FROM rt_content_hot c "
            f"LEFT JOIN content_metadata m ON c.content_id = m.content_id AND c.content_type = m.content_type "
            f"WHERE {where_clause}"
        ),
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
            "completion_rate": float(r.completion_rate) if r.completion_rate else 0,
            "interaction_rate": float(r.interaction_rate) if r.interaction_rate else 0,
            "artist_or_author": r.artist_or_author,
            "style_or_category": r.style_or_category,
            "tags": r.tags,
            "duration": float(r.duration) if r.duration else 0,
            "language": r.language,
            "bpm": float(r.bpm) if r.bpm else 0,
        })

    write_audit("query", "content", {"type": content_type, "keyword": keyword})
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
        "SELECT h.content_id, h.content_type, MAX(h.play_count) as play_count, MAX(h.like_count) as like_count, "
        "MAX(h.favorite_count) as favorite_count, MAX(h.share_count) as share_count, "
        "AVG(h.completion_rate) as completion_rate, AVG(h.interaction_rate) as interaction_rate, "
        "MAX(h.hot_score) as hot_score, "
        "COALESCE(MAX(m.title), CONCAT(IF(MAX(h.content_type)='music','音乐','视频'), ' #', MAX(h.content_id))) AS title "
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

    sql += " GROUP BY h.content_id, h.content_type ORDER BY MAX(h.hot_score) DESC LIMIT :top_n"
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
            "m.style_or_category, m.tags, m.duration, m.language, m.bpm, "
            "MAX(h.hot_score) as hot_score, MAX(h.play_count) as play_count, "
            "AVG(h.completion_rate) as completion_rate, AVG(h.interaction_rate) as interaction_rate, "
            "MAX(r.score) as rec_score, MAX(r.strategy) as rec_strategy, MAX(r.reason) as rec_reason, "
            "MAX(r.rank) as rec_rank "
            "FROM content_metadata m "
            "LEFT JOIN rt_content_hot h ON m.content_id = h.content_id AND m.content_type = h.content_type "
            "LEFT JOIN offline_recommendations r ON m.content_id = r.content_id AND m.content_type = r.content_type "
            "WHERE " + " AND ".join(where) + " LIMIT 1"
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
        "hot_score": float(row.hot_score or 0),
        "play_count": int(row.play_count or 0),
        "completion_rate": float(row.completion_rate or 0),
        "interaction_rate": float(row.interaction_rate or 0),
        "score": float(row.rec_score) if row.rec_score else None,
        "source_strategy": row.rec_strategy,
        "reason": row.rec_reason,
        "source_rank": int(row.rec_rank) if row.rec_rank else None,
    }}), 200
