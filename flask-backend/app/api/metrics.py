"""FR-12 GET /api/metrics — 实时计算 + 离线历史混合查询"""

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.permissions.decorators import require_role
from app.utils.validators import validate_date_range
from app.utils.audit import write_audit
from datetime import date, timedelta

metrics_bp = Blueprint("metrics", __name__)


def _realtime_for_date(target_date: str) -> list[dict]:
    """从 rt_ 表为单个日期计算实时指标。CTR 用 row 级别: 有播放行/总行数。"""

    groups = [
        ("all",       "is_cold_start IN (0, 1)"),
        ("coldstart", "is_cold_start = 1"),
        ("existing",  "is_cold_start = 0"),
    ]

    cov_row = db.session.execute(text(
        "SELECT (SELECT COUNT(DISTINCT content_id) FROM rt_content_hot) as covered, "
        "(SELECT COUNT(*) FROM content_metadata) as total"
    )).fetchone()
    coverage = round(float(cov_row[0]) / max(cov_row[1], 1), 4) if cov_row else 0

    div_rows = db.session.execute(text(
        "SELECT content_type, COUNT(*) as cnt FROM rt_content_hot GROUP BY content_type"
    )).fetchall()
    total_hot = sum(r[1] for r in div_rows)
    diversity = round(1 - sum((r[1] / max(total_hot, 1)) ** 2 for r in div_rows), 4)

    result = []
    for ug_name, ug_filter in groups:
        row = db.session.execute(text(
            "SELECT COUNT(*) as total_rows, "
            "SUM(play_count) as total_plays, "
            "SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows, "
            "COUNT(DISTINCT user_id) as total_users, "
            "ROUND(AVG(completion_rate), 4) as avg_cvr, "
            "ROUND(AVG(like_rate + favorite_rate) * 5, 2) as avg_inter "
            "FROM rt_user_profile "
            "WHERE DATE(window_end) = :d AND " + ug_filter
        ), {"d": target_date}).fetchone()

        if not row or row[0] == 0:
            continue

        total_rows = int(row[0])
        total_plays = int(row[1])
        active_rows = int(row[2])
        total_users = int(row[3])
        avg_cvr = float(row[4] or 0)
        avg_inter = float(row[5] or 0)

        # CTR: 假设每个user-window有~10条推荐曝光
        est_impressions = total_rows * 10
        ctr = round(active_rows / est_impressions, 4) if est_impressions > 0 else 0
        avg_watch = round(total_plays / max(total_users, 1) * avg_cvr * 180, 2)

        cold_conv = 0.0
        if ug_name in ("all", "coldstart"):
            cr = db.session.execute(text(
                "SELECT ROUND(SUM(CASE WHEN play_sum > 0 THEN 1 ELSE 0 END) * 1.0 "
                "/ NULLIF(COUNT(*), 0), 4) FROM ("
                "  SELECT user_id, SUM(play_count) as play_sum FROM rt_user_profile "
                "  WHERE is_cold_start = 1 AND DATE(window_end) = :d GROUP BY user_id"
                ") t"
            ), {"d": target_date}).fetchone()
            cold_conv = float(cr[0]) if cr and cr[0] else 0.0

        result.append({
            "metric_date": target_date,
            "user_group": ug_name,
            "content_type": "all",
            "ctr": ctr,
            "cvr": avg_cvr,
            "avg_watch_duration": avg_watch,
            "avg_interactions": avg_inter,
            "coverage": coverage,
            "diversity": diversity,
            "coldstart_conversion": cold_conv,
            "total_impressions": total_rows,
            "total_clicks": active_rows,
            "total_users": total_users,
        })

        # music / video 子分组
        for ct_name, ct_json in [("music", "music"), ("video", "video")]:
            ct_row = db.session.execute(text(
                "SELECT COUNT(*) as tr, SUM(play_count) as tp, "
                "SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as ar, "
                "COUNT(DISTINCT user_id) as tu "
                "FROM rt_user_profile "
                "WHERE DATE(window_end) = :d AND " + ug_filter + " "
                "AND JSON_EXTRACT(content_type_ratio, :json_path) > 0.5"
            ), {"d": target_date, "json_path": "$." + ct_json}).fetchone()
            if ct_row and ct_row[0] > 0:
                result.append({
                    "metric_date": target_date,
                    "user_group": ug_name,
                    "content_type": ct_name,
                    "ctr": round(int(ct_row[2]) / (int(ct_row[0]) * 10), 4) if ct_row[0] > 0 else 0,
                    "cvr": avg_cvr,
                    "avg_watch_duration": avg_watch,
                    "avg_interactions": avg_inter,
                    "coverage": coverage,
                    "diversity": diversity,
                    "coldstart_conversion": cold_conv,
                    "total_impressions": int(ct_row[0]),
                    "total_clicks": int(ct_row[2]),
                    "total_users": int(ct_row[3]),
                })
    return result


@metrics_bp.route("/metrics", methods=["GET"])
@require_role("operator", "admin")
def get_metrics():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    group_by = request.args.get("group_by", "date")

    valid, msg = validate_date_range(start_date, end_date)
    if not valid:
        return jsonify({"code": 400, "message": msg}), 400

    today_str = str(date.today())
    result = []
    seen_keys = set()

    # 1. 离线历史数据 (不含今天)
    order_clause = {"date": "ORDER BY metric_date",
                    "user_group": "ORDER BY user_group, metric_date",
                    "content_type": "ORDER BY content_type, metric_date"}.get(group_by, "ORDER BY metric_date")

    offline_rows = db.session.execute(text(
        "SELECT metric_date, user_group, content_type, ctr, cvr, "
        "avg_watch_duration, avg_interactions, coverage, diversity, "
        "coldstart_conversion, total_impressions, total_clicks, total_users "
        "FROM offline_metrics "
        "WHERE metric_date BETWEEN :s AND :e AND metric_date < :t " + order_clause
    ), {"s": start_date, "e": end_date, "t": today_str}).fetchall()

    for m in offline_rows:
        key = (str(m.metric_date), m.user_group, m.content_type)
        seen_keys.add(key)
        result.append(_row_to_dict(m))

    # 2. 实时数据: 为请求范围内没有离线数据的日期计算
    cur = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    while cur <= end:
        ds = str(cur)
        if ds >= today_str:
            for item in _realtime_for_date(ds):
                key = (item["metric_date"], item["user_group"], item["content_type"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    result.append(item)
        cur += timedelta(days=1)

    # 3. 空结果兜底
    if not result:
        for m in db.session.execute(text(
            "SELECT metric_date, user_group, content_type, ctr, cvr, "
            "avg_watch_duration, avg_interactions, coverage, diversity, "
            "coldstart_conversion, total_impressions, total_clicks, total_users "
            "FROM offline_metrics WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) "
            + order_clause
        )).fetchall():
            result.append(_row_to_dict(m))

    write_audit("query", "metrics", {"start_date": start_date, "end_date": end_date})
    return jsonify({"code": 200, "data": result}), 200


def _row_to_dict(m):
    return {
        "metric_date": str(m.metric_date),
        "user_group": m.user_group,
        "content_type": m.content_type,
        "ctr": float(m.ctr) if m.ctr is not None else 0,
        "cvr": float(m.cvr) if m.cvr is not None else 0,
        "avg_watch_duration": float(m.avg_watch_duration) if m.avg_watch_duration is not None else 0,
        "avg_interactions": float(m.avg_interactions) if m.avg_interactions is not None else 0,
        "coverage": float(m.coverage) if m.coverage is not None else 0,
        "diversity": float(m.diversity) if m.diversity is not None else 0,
        "coldstart_conversion": float(m.coldstart_conversion) if m.coldstart_conversion is not None else 0,
        "total_impressions": m.total_impressions,
        "total_clicks": m.total_clicks,
        "total_users": m.total_users,
    }
