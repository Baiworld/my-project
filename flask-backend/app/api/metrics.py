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
    """单日实时指标 — 使用 >= < 区间以利用索引"""
    next_day = str(date.fromisoformat(target_date) + timedelta(days=1))

    cov_row = db.session.execute(text(
        "SELECT (SELECT COUNT(DISTINCT content_id) FROM rt_content_hot) as covered, "
        "(SELECT COUNT(*) FROM content_metadata) as total"
    )).fetchone()
    coverage = round(float(cov_row[0]) / max(cov_row[1], 1), 4) if cov_row else 0

    div_rows = db.session.execute(text("SELECT content_type, COUNT(*) as cnt FROM rt_content_hot GROUP BY content_type")).fetchall()
    total_hot = sum(r[1] for r in div_rows)
    diversity = round(1 - sum((r[1] / max(total_hot, 1)) ** 2 for r in div_rows), 4)

    # 一次查询获取 all / coldstart / existing 三个分组的聚合数据
    row = db.session.execute(text(
        "SELECT "
        "COUNT(*) as total_rows, "
        "SUM(play_count) as total_plays, "
        "SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows, "
        "COUNT(DISTINCT user_id) as total_users, "
        "ROUND(AVG(completion_rate), 4) as avg_cvr, "
        "ROUND(AVG(like_rate + favorite_rate) * 5, 2) as avg_inter, "
        "SUM(CASE WHEN is_cold_start = 1 THEN 1 ELSE 0 END) as cold_rows, "
        "SUM(CASE WHEN is_cold_start = 1 AND play_count > 0 THEN 1 ELSE 0 END) as cold_active_rows, "
        "SUM(CASE WHEN is_cold_start = 1 THEN play_count ELSE 0 END) as cold_plays, "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 1 THEN user_id END) as cold_users, "
        "SUM(CASE WHEN is_cold_start = 0 THEN 1 ELSE 0 END) as est_rows, "
        "SUM(CASE WHEN is_cold_start = 0 AND play_count > 0 THEN 1 ELSE 0 END) as est_active_rows, "
        "SUM(CASE WHEN is_cold_start = 0 THEN play_count ELSE 0 END) as est_plays, "
        "COUNT(DISTINCT CASE WHEN is_cold_start = 0 THEN user_id END) as est_users "
        "FROM rt_user_profile "
        "WHERE window_end >= :d AND window_end < :n"
    ), {"d": target_date, "n": next_day}).fetchone()

    if not row or row[0] == 0:
        return []

    total_rows = int(row[0])
    total_plays = int(row[1])
    active_rows = int(row[2])
    total_users = int(row[3])
    avg_cvr = float(row[4] or 0)
    avg_inter = float(row[5] or 0)
    cold_rows = int(row[6] or 0)
    cold_active = int(row[7] or 0)
    cold_plays = int(row[8] or 0)
    cold_users = int(row[9] or 0)
    est_rows = int(row[10] or 0)
    est_active = int(row[11] or 0)
    est_plays = int(row[12] or 0)
    est_users = int(row[13] or 0)

    est_imp = total_rows * 10
    ctr = round(active_rows / est_imp, 4) if est_imp > 0 else 0
    avg_watch = round(total_plays / max(total_users, 1) * avg_cvr * 180, 2)
    cold_ctr = round(cold_active / max(cold_rows * 10, 1), 4)
    est_ctr = round(est_active / max(est_rows * 10, 1), 4)

    # 冷启动转化率
    cold_conv = 0.0
    cr = db.session.execute(text(
        "SELECT ROUND(SUM(CASE WHEN play_sum > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 4) "
        "FROM (SELECT user_id, SUM(play_count) as play_sum FROM rt_user_profile "
        "WHERE is_cold_start = 1 AND window_end >= :d AND window_end < :n GROUP BY user_id) t"
    ), {"d": target_date, "n": next_day}).fetchone()
    cold_conv = float(cr[0]) if cr and cr[0] else 0.0

    result = [
        {"metric_date": target_date, "user_group": "all", "content_type": "all",
         "ctr": ctr, "cvr": avg_cvr, "avg_watch_duration": avg_watch, "avg_interactions": avg_inter,
         "coverage": coverage, "diversity": diversity, "coldstart_conversion": cold_conv,
         "total_impressions": total_rows, "total_clicks": active_rows, "total_users": total_users},
        {"metric_date": target_date, "user_group": "coldstart", "content_type": "all",
         "ctr": cold_ctr, "cvr": avg_cvr, "avg_watch_duration": round(cold_plays / max(cold_users, 1) * avg_cvr * 180, 2),
         "avg_interactions": avg_inter, "coverage": coverage, "diversity": diversity,
         "coldstart_conversion": cold_conv, "total_impressions": cold_rows, "total_clicks": cold_active, "total_users": cold_users},
        {"metric_date": target_date, "user_group": "existing", "content_type": "all",
         "ctr": est_ctr, "cvr": avg_cvr, "avg_watch_duration": round(est_plays / max(est_users, 1) * avg_cvr * 180, 2),
         "avg_interactions": avg_inter, "coverage": coverage, "diversity": diversity,
         "coldstart_conversion": cold_conv, "total_impressions": est_rows, "total_clicks": est_active, "total_users": est_users},
    ]
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

    # 离线历史数据
    offline_rows = db.session.execute(text(
        "SELECT * FROM offline_metrics WHERE metric_date BETWEEN :s AND :e AND metric_date < :t ORDER BY metric_date"
    ), {"s": start_date, "e": end_date, "t": today_str}).fetchall()
    for m in offline_rows:
        key = (str(m.metric_date), m.user_group, m.content_type)
        seen_keys.add(key)
        result.append(_row_to_dict(m))

    # 实时数据（只补今天及以后）
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

    if not result:
        for m in db.session.execute(text(
            "SELECT * FROM offline_metrics WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) ORDER BY metric_date"
        )).fetchall():
            result.append(_row_to_dict(m))

    write_audit("query", "metrics", {"start_date": start_date, "end_date": end_date})
    return jsonify({"code": 200, "data": result}), 200


def _row_to_dict(m):
    return {
        "metric_date": str(m.metric_date),
        "user_group": m.user_group,
        "content_type": m.content_type,
        "ctr": float(m.ctr or 0),
        "cvr": float(m.cvr or 0),
        "avg_watch_duration": float(m.avg_watch_duration or 0),
        "avg_interactions": float(m.avg_interactions or 0),
        "coverage": float(m.coverage or 0),
        "diversity": float(m.diversity or 0),
        "coldstart_conversion": float(m.coldstart_conversion or 0),
        "total_impressions": m.total_impressions,
        "total_clicks": m.total_clicks,
        "total_users": m.total_users,
    }
