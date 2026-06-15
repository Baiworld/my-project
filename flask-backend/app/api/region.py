"""GET /api/region/heatmap — 地区活跃热力图（基于 rt_user_profile 真实地区数据）"""

from flask import Blueprint, jsonify
from sqlalchemy import text
from app.extensions import db

region_bp = Blueprint("region", __name__)

# 省份代码 → 主要城市坐标
REGION_COORDS = {
    "CN-BJ": ("北京", 116.46, 39.92), "CN-SH": ("上海", 121.48, 31.22),
    "CN-GD": ("广州", 113.23, 23.16), "CN-ZJ": ("杭州", 120.19, 30.26),
    "CN-SC": ("成都", 104.06, 30.67), "CN-CQ": ("重庆", 106.54, 29.59),
    "CN-HB": ("武汉", 114.31, 30.52), "CN-SN": ("西安", 108.95, 34.27),
    "CN-JS": ("南京", 118.78, 32.04), "CN-TJ": ("天津", 117.20, 39.13),
    "CN-HN": ("长沙", 112.97, 28.23), "CN-HA": ("郑州", 113.65, 34.76),
    "CN-SD": ("青岛", 120.33, 36.07), "CN-LN": ("大连", 121.62, 38.92),
    "CN-YN": ("昆明", 102.73, 25.04),
}


@region_bp.route("/region/heatmap", methods=["GET"])
def get_region_heatmap():
    # 从 rt_user_profile 获取各地区的活跃用户统计（去重取最新窗口）
    rows = db.session.execute(text(
        "SELECT p.region, COUNT(DISTINCT p.user_id) as user_count, "
        "SUM(p.play_count) as total_plays, "
        "AVG(p.behavior_count) as avg_behaviors, "
        "SUM(CASE WHEN p.is_cold_start = 1 THEN 1 ELSE 0 END) as cold_count "
        "FROM rt_user_profile p "
        "WHERE p.region IS NOT NULL AND p.region != '' "
        "AND p.window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR) "
        "AND p.id IN (SELECT MAX(id) FROM rt_user_profile "
        "            WHERE region IS NOT NULL AND region != '' GROUP BY user_id) "
        "GROUP BY p.region ORDER BY user_count DESC"
    )).fetchall()

    heat_points = []
    for r in rows:
        region_code = r[0]
        info = REGION_COORDS.get(region_code)
        if not info:
            continue
        city_name, lng, lat = info
        user_count = int(r[1] or 0)
        total_plays = int(float(r[2] or 0))
        avg_behaviors = round(float(r[3] or 0), 1)
        cold_count = int(r[4] or 0)

        # 活跃度分数：综合考虑用户数和播放量
        max_users = max(int(u[1] or 0) for u in rows) if rows else 1
        max_plays = max(int(float(u[2] or 0)) for u in rows) if rows else 1
        activity = min(100, round(
            float(user_count) / max(1, max_users) * 50.0 +
            float(total_plays) / max(1, max_plays) * 50.0, 1
        ))

        coldstart_ratio = round(cold_count / max(1, user_count) * 100, 1)

        heat_points.append({
            "name": city_name,
            "lng": lng,
            "lat": lat,
            "value": activity,
            "user_count": user_count,
            "total_plays": total_plays,
            "avg_behaviors": avg_behaviors,
            "cold_count": cold_count,
            "coldstart_ratio": coldstart_ratio,
        })

    # 整体统计
    all_users = sum(p["user_count"] for p in heat_points)
    all_cold = sum(p["cold_count"] for p in heat_points)

    return jsonify({
        "code": 200,
        "data": {
            "points": heat_points,
            "summary": {
                "total_active_users": all_users,
                "total_coldstart_users": all_cold,
                "region_count": len(heat_points),
            },
        },
    }), 200
