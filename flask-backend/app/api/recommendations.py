"""FR-12 GET /api/recommendations — query user recommendation list (offline + real-time fallback)"""

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
    content_type = request.args.get("content_type")
    keyword = request.args.get("keyword")
    strategy = request.args.get("strategy")
    sort_by = request.args.get("sort_by", "rank")  # rank, score

    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    # ── 优先离线推荐，如果离线表有数据直接使用 ──
    offline_has_data = db.session.execute(
        text("SELECT EXISTS(SELECT 1 FROM offline_recommendations LIMIT 1)")
    ).scalar()

    valid_strategies = {"coldstart", "coldstart_cluster", "als_cf", "item2vec", "hot", "dpp_rerank", "epsilon_greedy"}

    if offline_has_data:
        where = ["1=1"]
        params: dict = {}
        if user_id:
            where.append("r.user_id = :user_id")
            params["user_id"] = user_id
        if content_type in ("music", "video"):
            where.append("r.content_type = :content_type")
            params["content_type"] = content_type
        if keyword:
            where.append("(m.title LIKE :kw OR m.artist_or_author LIKE :kw OR m.tags LIKE :kw)")
            params["kw"] = f"%{keyword}%"
        if strategy and strategy in valid_strategies:
            where.append("r.strategy = :strategy")
            params["strategy"] = strategy

        where_clause = " AND ".join(where)

        order_col = "r.`rank`" if sort_by == "rank" else "r.score DESC"

        rows = db.session.execute(
            text(
                f"SELECT r.user_id, r.content_id, r.content_type, r.`rank`, r.score, r.reason, r.strategy, "
                f"COALESCE(m.title, CONCAT(IF(r.content_type='music','音乐','视频'), ' #', r.content_id)) AS title, "
                f"m.artist_or_author, m.style_or_category, m.tags, m.duration "
                f"FROM offline_recommendations r "
                f"LEFT JOIN content_metadata m ON r.content_id = m.content_id AND r.content_type = m.content_type "
                f"WHERE {where_clause} "
                f"ORDER BY {order_col} LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": size, "offset": offset},
        ).fetchall()

        total = db.session.execute(
            text(f"SELECT COUNT(*) FROM offline_recommendations r "
                 f"LEFT JOIN content_metadata m ON r.content_id = m.content_id AND r.content_type = m.content_type "
                 f"WHERE {where_clause}"),
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
                "artist_or_author": r.artist_or_author,
                "style_or_category": r.style_or_category,
                "tags": r.tags,
                "duration": float(r.duration) if r.duration else 0,
            })
    else:
        # ── 实时兜底：用 rt_content_hot 热度排行 ──
        where = ["1=1"]
        params: dict = {}
        if content_type in ("music", "video"):
            where.append("c.content_type = :content_type")
            params["content_type"] = content_type
        if keyword:
            where.append("(m.title LIKE :kw OR m.artist_or_author LIKE :kw OR m.tags LIKE :kw)")
            params["kw"] = f"%{keyword}%"

        where_clause = " AND ".join(where)

        realtime_sort = "MAX(c.hot_score) DESC" if sort_by == "score" else "MAX(c.hot_score) DESC"

        rows = db.session.execute(
            text(
                f"SELECT c.content_id, c.content_type, MAX(c.hot_score) as hot_score, "
                f"MAX(c.play_count) as play_count, MAX(c.like_count) as like_count, "
                f"COALESCE(MAX(m.title), CONCAT(IF(MAX(c.content_type)='music','音乐','视频'), ' #', MAX(c.content_id))) AS title, "
                f"MAX(m.artist_or_author) as artist_or_author, MAX(m.style_or_category) as style_or_category, "
                f"MAX(m.tags) as tags, MAX(m.duration) as duration "
                f"FROM rt_content_hot c "
                f"LEFT JOIN content_metadata m ON c.content_id = m.content_id AND c.content_type = m.content_type "
                f"WHERE {where_clause} "
                f"GROUP BY c.content_id, c.content_type "
                f"ORDER BY {realtime_sort} LIMIT :limit OFFSET :offset"
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
                "user_id": None,
                "title": r.title,
                "type": r.content_type,
                "rank": 0,
                "score": float(r.hot_score) if r.hot_score else 0,
                "hot_score": float(r.hot_score) if r.hot_score else 0,
                "play_count": r.play_count,
                "like_count": r.like_count,
                "reason": "实时热度推荐",
                "strategy": "hot_rt",
                "artist_or_author": r.artist_or_author,
                "style_or_category": r.style_or_category,
                "tags": r.tags,
                "duration": float(r.duration) if r.duration else 0,
            })

    write_audit("query", "recommendations", {"user_id": user_id, "keyword": keyword})
    return jsonify({
        "code": 200,
        "data": result,
        "pagination": {"page": page, "size": size, "total": total, "pages": max(1, (total + size - 1) // size)},
    }), 200
