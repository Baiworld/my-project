"""FR-12 GET /api/coldstart/analysis — coldstart user cluster analysis"""

import json
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
    keyword = request.args.get("keyword")
    cluster_id = request.args.get("cluster_id", type=int)

    page, size = validate_pagination(
        request.args.get("page"), request.args.get("size")
    )
    offset = (page - 1) * size

    sort_by = request.args.get("sort_by", "behavior_count")  # behavior_count, play_count, like_rate, completion_rate
    time_filter = request.args.get("time_filter")  # 24h, 7d, all (default all)

    where = ["rt.is_cold_start = 1"]
    params: dict = {}
    if content_type == "music":
        where.append("(JSON_EXTRACT(rt.content_type_ratio, '$.music') > 0.5 OR JSON_EXTRACT(rt.content_type_ratio, '$.music') IS NULL)")
    elif content_type == "video":
        where.append("JSON_EXTRACT(rt.content_type_ratio, '$.video') >= 0.5")
    if cluster_id is not None:
        where.append("cl.cluster_id = :cluster_id")
        params["cluster_id"] = cluster_id
    if keyword:
        where.append("(cl.interest_tags LIKE :kw OR cl.device_type LIKE :kw OR cl.register_channel LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if time_filter == "24h":
        where.append("rt.window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
    elif time_filter == "7d":
        where.append("rt.window_end >= DATE_SUB(NOW(), INTERVAL 7 DAY)")

    where_clause = " AND ".join(where)

    # 合法排序字段白名单
    valid_sorts = {"behavior_count": "behavior_count", "play_count": "play_count",
                   "like_rate": "like_rate", "completion_rate": "completion_rate",
                   "favorite_rate": "favorite_rate"}
    sort_col = valid_sorts.get(sort_by, "behavior_count")

    # 子查询取每个用户最新一条记录（去重）
    rows = db.session.execute(
        text(
            f"SELECT rt.user_id, rt.behavior_count, rt.play_count, rt.like_rate, "
            f"rt.favorite_rate, rt.share_count, rt.comment_count, rt.content_type_ratio, "
            f"rt.completion_rate, rt.skip_rate, rt.is_cold_start, rt.window_end, "
            f"cl.cluster_id, cl.device_type, cl.register_channel, cl.interest_tags "
            f"FROM rt_user_profile rt "
            f"LEFT JOIN rt_coldstart_cluster cl ON rt.user_id = cl.user_id "
            f"WHERE {where_clause} "
            f"AND rt.id IN (SELECT MAX(id) FROM rt_user_profile WHERE is_cold_start = 1 GROUP BY user_id) "
            f"ORDER BY rt.{sort_col} ASC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": size, "offset": offset},
    ).fetchall()

    total = db.session.execute(
        text(
            f"SELECT COUNT(DISTINCT rt.user_id) FROM rt_user_profile rt "
            f"LEFT JOIN rt_coldstart_cluster cl ON rt.user_id = cl.user_id "
            f"WHERE {where_clause}"
        ),
        params,
    ).scalar()

    # 加载集群名称映射（使用 cluster_utils 的现有逻辑）
    cluster_dist = get_cluster_distribution()
    cluster_id_to_name: dict = {i: c["cluster_name"] for i, c in enumerate(cluster_dist)}

    threshold = 50
    result = []
    for r in rows:
        coldstart_pct = min(round(r.behavior_count / threshold * 100, 1), 100.0) if threshold > 0 else 0
        cid = r.cluster_id
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
            "completion_rate": float(r.completion_rate or 0),
            "skip_rate": float(r.skip_rate or 0),
            "content_type_ratio": r.content_type_ratio,
            "is_cold_start": bool(r.is_cold_start),
            "cluster_id": cid,
            "cluster_name": cluster_id_to_name.get(cid, "未分配") if cid is not None else "未分配",
            "device_type": r.device_type or "",
            "register_channel": r.register_channel or "",
            "interest_tags": r.interest_tags,
            "coldstart_progress": coldstart_pct,
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
    # 一次查询获取冷启动统计
    stats_row = db.session.execute(text(
        "SELECT "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 1 THEN user_id END) as total_cold, "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 1 AND window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN user_id END) as active_24h, "
        "ROUND(AVG(CASE WHEN is_cold_start = 1 THEN behavior_count END), 1) as avg_behavior, "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 0 AND behavior_count > 50 THEN user_id END) as est_cs, "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 0 AND behavior_count <= 50 THEN user_id END) as exp_cs, "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 1 THEN user_id END) as cold_cs "
        "FROM rt_user_profile"
    )).fetchone()
    total_cold = int(stats_row[0] or 0)
    active_24h = int(stats_row[1] or 0)
    avg_behavior = float(stats_row[2] or 0)
    est_cs = int(stats_row[3] or 0)
    exp_cs = int(stats_row[4] or 0)
    cold_cs = int(stats_row[5] or 0)

    # 冷启动转化率
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
        conv_row = db.session.execute(
            text("SELECT coldstart_conversion FROM offline_metrics "
                 "WHERE user_group = 'coldstart' AND content_type = 'all' "
                 "ORDER BY metric_date DESC LIMIT 1")
        ).fetchone()
        conversion_rate = round(float(conv_row[0]) * 100, 1) if conv_row and conv_row[0] else 0.0

    cluster_distribution = get_cluster_distribution()
    strategy_distribution = [
        {"name": "冷启动策略", "value": cold_cs},
        {"name": "存量策略", "value": est_cs},
        {"name": "探索策略", "value": exp_cs},
    ]

    # Fallback: if rt data is empty, use offline_metrics
    if cold_cs == 0 and est_cs == 0 and exp_cs == 0:
        off_dist = db.session.execute(text("""
            SELECT user_group, SUM(total_users) as cnt FROM offline_metrics
            WHERE user_group IN ('coldstart', 'existing')
            AND metric_date = (SELECT MAX(metric_date) FROM offline_metrics)
            GROUP BY user_group
        """)).fetchall()
        if off_dist:
            name_map = {"coldstart": "冷启动策略", "existing": "存量策略"}
            strategy_distribution = [
                {"name": name_map.get(r[0], r[0]), "value": int(r[1])}
                for r in off_dist
            ]

    write_audit("query", "coldstart/stats")
    return jsonify({
        "code": 200,
        "data": {
            "total_coldstart_users": cold_cs,
            "active_coldstart_users_24h": active_24h,
            "cluster_distribution": cluster_distribution,
            "avg_behavior_count": float(avg_behavior),
            "conversion_rate": conversion_rate,
            "strategy_distribution": strategy_distribution,
        },
    }), 200
