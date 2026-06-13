"""GET /api/region/heatmap — 地区热力图数据（基于冷启动聚类+内容多样性）"""

from flask import Blueprint, jsonify
from sqlalchemy import text
from app.extensions import db

region_bp = Blueprint("region", __name__)

# 省会/主要城市坐标（仅作地理映射参考）
CITY_COORDS = {
    "北京": (116.46, 39.92), "上海": (121.48, 31.22), "广州": (113.23, 23.16),
    "深圳": (114.07, 22.62), "成都": (104.06, 30.67), "重庆": (106.54, 29.59),
    "杭州": (120.19, 30.26), "武汉": (114.31, 30.52), "西安": (108.95, 34.27),
    "南京": (118.78, 32.04), "天津": (117.20, 39.13), "苏州": (120.62, 31.32),
    "长沙": (112.97, 28.23), "郑州": (113.65, 34.76), "青岛": (120.33, 36.07),
    "大连": (121.62, 38.92), "厦门": (118.08, 24.49), "福州": (119.30, 26.08),
    "合肥": (117.27, 31.86), "沈阳": (123.38, 41.80), "哈尔滨": (126.53, 45.80),
    "昆明": (102.73, 25.04), "贵阳": (106.71, 26.57), "南宁": (108.33, 22.84),
    "海口": (110.33, 20.03), "兰州": (103.73, 36.03), "乌鲁木齐": (87.68, 43.77),
    "拉萨": (91.11, 29.97), "呼和浩特": (111.65, 40.82), "太原": (112.53, 37.87),
    "石家庄": (114.48, 38.03), "济南": (117.00, 36.65), "南昌": (115.89, 28.68),
    "长春": (125.35, 43.88), "西宁": (101.74, 36.56), "银川": (106.27, 38.47),
}


@region_bp.route("/region/heatmap", methods=["GET"])
def get_region_heatmap():
    # 从 rt_user_profile 获取各用户的冷启动状态和行为数据
    active_users = db.session.execute(text(
        "SELECT user_id, behavior_count, content_type_ratio "
        "FROM rt_user_profile "
        "WHERE window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
    )).fetchall()

    # 从 rt_coldstart_cluster 获取聚类分布（Top 30 按大小排序）
    clusters = db.session.execute(text(
        "SELECT cluster_id, MAX(cluster_size) as cluster_size, "
        "GROUP_CONCAT(DISTINCT interest_tags SEPARATOR ',') as interest_tags "
        "FROM rt_coldstart_cluster "
        "GROUP BY cluster_id ORDER BY MAX(cluster_size) DESC LIMIT 30"
    )).fetchall()

    # 从 content_metadata 获取内容多样性数据
    content_stats = db.session.execute(text(
        "SELECT content_type, COUNT(*) as cnt, "
        "COUNT(DISTINCT style_or_category) as style_count, "
        "COUNT(DISTINCT language) as lang_count "
        "FROM content_metadata GROUP BY content_type"
    )).fetchall()

    music_diversity = 0
    video_diversity = 0
    for r in content_stats:
        if r[0] == "music":
            music_diversity = min(100, (r[2] or 0) * 8 + (r[3] or 0) * 10)
        elif r[0] == "video":
            video_diversity = min(100, (r[2] or 0) * 6 + (r[3] or 0) * 8)

    # 用户活跃度统计
    total_users = len(active_users) or 1
    cold_users = sum(1 for u in active_users if u[1] <= 50)
    warm_users = sum(1 for u in active_users if u[1] > 50)

    # 将聚类数据映射到城市（根据聚类大小分配）
    city_names = list(CITY_COORDS.keys())
    heat_points = []

    for i, c in enumerate(clusters):
        cluster_id = c[0] or 0
        cluster_size = c[1] or 0
        tags = c[2] or ""

        # 用聚类ID散列到不同城市
        city_idx = (cluster_id * 7 + i * 13) % len(city_names)
        city = city_names[city_idx]
        lng, lat = CITY_COORDS[city]

        # 多样性分数：基于聚类大小 + 标签丰富度 + 内容多样性
        tag_count = len(str(tags).split(",")) if tags else 0
        diversity = min(100, 30 + (cluster_size / max(1, total_users)) * 100 + tag_count * 5)

        heat_points.append({
            "name": city,
            "lng": lng + (i % 3 - 1) * 0.3,  # 微调避免重叠
            "lat": lat + ((i * 7) % 3 - 1) * 0.2,
            "diversity": round(diversity, 1),
            "cluster_size": cluster_size,
        })

    # 添加内容多样性散射点
    for i, city in enumerate(["北京", "上海", "广州", "成都", "武汉"]):
        heat_points.append({
            "name": city,
            "lng": CITY_COORDS[city][0] + 0.15,
            "lat": CITY_COORDS[city][1] + 0.15,
            "diversity": round(music_diversity + i * 3, 1),
            "cluster_size": 0,
        })

    # 整体统计
    summary = {
        "total_active_users": total_users,
        "coldstart_users": cold_users,
        "warm_users": warm_users,
        "music_diversity": round(music_diversity, 1),
        "video_diversity": round(video_diversity, 1),
        "cluster_count": len(clusters),
    }

    return jsonify({
        "code": 200,
        "data": {
            "points": heat_points,
            "summary": summary,
        },
    }), 200
