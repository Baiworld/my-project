"""FR-12 GET /api/coldstart/analysis — coldstart user cluster analysis"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.audit import write_audit
from app.utils.validators import validate_pagination
from app.utils.cluster_utils import get_cluster_distribution

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


@coldstart_bp.route("/coldstart/stats", methods=["GET"])
@require_role("operator", "admin")
def get_coldstart_stats():
    # 冷启动用户总数（不去重所有 rt_user_profile 中标记为冷启动的 user_id）
    total_cold = db.session.execute(
        text("SELECT COUNT(*) FROM rt_user_profile WHERE is_cold_start = 1")
    ).scalar() or 0

    # 近 24 小时活跃冷启动用户
    active_24h = db.session.execute(
        text("SELECT COUNT(*) FROM rt_user_profile "
             "WHERE is_cold_start = 1 "
             "AND window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
    ).scalar() or 0

    # 冷启动用户平均行为次数
    avg_behavior = db.session.execute(
        text("SELECT ROUND(AVG(behavior_count), 1) FROM rt_user_profile "
             "WHERE is_cold_start = 1")
    ).scalar() or 0.0

    # 冷启动转化率: 实时计算冷启动用户中有播放行为的比例
    conv_row = db.session.execute(text(
        "SELECT ROUND(SUM(CASE WHEN play_sum > 0 THEN 1 ELSE 0 END) * 1.0 "
        "/ NULLIF(COUNT(*), 0), 4) FROM ("
        "  SELECT user_id, SUM(play_count) as play_sum "
        "  FROM rt_user_profile WHERE is_cold_start = 1 GROUP BY user_id"
        ") t"
    )).fetchone()
    if conv_row and conv_row[0]:
        conversion_rate = round(float(conv_row[0]) * 100, 1)
    else:
        # 回退到离线指标
        conv_row = db.session.execute(
            text("SELECT coldstart_conversion FROM offline_metrics "
                 "WHERE user_group = 'coldstart' AND content_type = 'all' "
                 "ORDER BY metric_date DESC LIMIT 1")
        ).fetchone()
        conversion_rate = round(float(conv_row[0]) * 100, 1) if conv_row and conv_row[0] else 0.0

    cluster_distribution = get_cluster_distribution()

    # 推荐策略分布 — 实时从用户画像计算
    cold_cs = db.session.execute(text(
        "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile WHERE is_cold_start = 1"
    )).scalar() or 0
    est_cs = db.session.execute(text(
        "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile WHERE is_cold_start = 0 AND behavior_count > 50"
    )).scalar() or 0
    exp_cs = db.session.execute(text(
        "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile WHERE is_cold_start = 0 AND behavior_count <= 50"
    )).scalar() or 0
    strategy_distribution = [
        {"name": "冷启动策略", "value": cold_cs},
        {"name": "存量策略", "value": est_cs},
        {"name": "探索策略", "value": exp_cs},
    ]

    write_audit("query", "coldstart/stats")
    return jsonify({
        "code": 200,
        "data": {
            "total_coldstart_users_24h": total_cold,
            "cluster_distribution": cluster_distribution,
            "avg_behavior_count": float(avg_behavior),
            "conversion_rate": conversion_rate,
            "strategy_distribution": strategy_distribution,
        },
    }), 200
