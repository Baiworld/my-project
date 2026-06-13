"""FR-15 DashboardPusher — push dashboard metrics to clients"""

import threading
import time
from datetime import datetime, timezone
from app.extensions import db, socketio
from app.utils.cluster_utils import get_cluster_distribution

_push_running = False
_push_thread = None
_app = None


def _fetch_dashboard_snapshot() -> dict:
    try:
        # 在线用户：优先用最近一天指标中的 total_users，回退到 rt_user_profile 总数
        online_users = db.session.execute(
            db.text("SELECT COUNT(DISTINCT user_id) FROM rt_user_profile "
            "WHERE window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        ).scalar() or 0

        # 昨日离线 all/all 指标 — 作为实时数据为 0 时的降级兜底
        # 优先查昨天，回退到最近一条可用数据
        offline_row = db.session.execute(
            db.text("SELECT ctr, avg_watch_duration, cvr, coverage, diversity, total_impressions "
            "FROM offline_metrics WHERE metric_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY) "
            "AND user_group = 'all' AND content_type = 'all' LIMIT 1")
        ).fetchone()
        if not offline_row:
            offline_row = db.session.execute(
                db.text("SELECT ctr, avg_watch_duration, cvr, coverage, diversity, total_impressions "
                "FROM offline_metrics WHERE user_group = 'all' AND content_type = 'all' "
                "ORDER BY metric_date DESC LIMIT 1")
            ).fetchone()
        fallback_ctr = float(offline_row.ctr) if offline_row and offline_row.ctr else 0.0
        fallback_watch = float(offline_row.avg_watch_duration) if offline_row and offline_row.avg_watch_duration else 0.0
        fallback_recs = offline_row.total_impressions if offline_row and offline_row.total_impressions else 0

        # 实时: 今日推荐总数 = rt_user_profile 今日总播放量，为 0 时用昨日离线值
        daily_recs = db.session.execute(
            db.text("SELECT COALESCE(SUM(play_count), 0) FROM rt_user_profile "
            "WHERE DATE(window_end) = CURDATE()")
        ).scalar() or 0
        if daily_recs == 0:
            daily_recs = fallback_recs

        # 实时: 今日 CTR = 有播放的用户 / 活跃用户总数，为 0 时用昨日离线值
        rt_ctr = db.session.execute(
            db.text("SELECT ROUND("
            "COUNT(DISTINCT CASE WHEN play_count > 0 THEN user_id END) * 1.0 / "
            "NULLIF(COUNT(DISTINCT user_id), 0), 4) "
            "FROM rt_user_profile WHERE DATE(window_end) = CURDATE()")
        ).scalar() or 0.0
        if rt_ctr == 0:
            rt_ctr = fallback_ctr

        # 实时: 人均播放时长 = 各用户播放秒数均值，为 0 时用昨日离线值
        rt_avg_watch = db.session.execute(
            db.text("SELECT ROUND(COALESCE("
            "SUM(user_play_sec) / NULLIF(COUNT(*), 0), 0), 2) "
            "FROM (SELECT user_id, SUM(play_count * completion_rate * 180) AS user_play_sec "
            "FROM rt_user_profile WHERE DATE(window_end) = CURDATE() "
            "GROUP BY user_id) t")
        ).scalar() or 0.0
        if rt_avg_watch == 0:
            rt_avg_watch = fallback_watch

        hot_top5 = db.session.execute(
            db.text("SELECT content_id, content_type, MAX(hot_score) as hot_score FROM rt_content_hot "
            "GROUP BY content_id, content_type ORDER BY MAX(hot_score) DESC LIMIT 5")
        ).fetchall()

        coldstart_count = db.session.execute(
            db.text("SELECT COUNT(*) FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        ).scalar() or 0

        # CTR trend (last 7 days) — 离线 + 实时混合，保证每天都有数据
        offline_ctr = db.session.execute(
            db.text("SELECT metric_date, ctr FROM offline_metrics "
            "WHERE user_group = 'all' AND content_type = 'all' "
            "AND metric_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) "
            "ORDER BY metric_date")
        ).fetchall()
        offline_dates = {str(r[0]) for r in offline_ctr}
        ctr_trend = list(offline_ctr)

        # 对最近7天中没有离线数据的日期，从 rt_user_profile 实时计算补全
        # 使用与 /api/metrics 一致的 CTR 公式: active_rows / (total_rows * 10)
        rt_ctr_rows = db.session.execute(
            db.text("""
                SELECT DATE(window_end) as d,
                       COUNT(*) as total_rows,
                       SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows
                FROM rt_user_profile
                WHERE window_end >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(window_end) ORDER BY d
            """)
        ).fetchall()
        for r in rt_ctr_rows:
            d = str(r[0])
            if d not in offline_dates:
                total_rows = int(r[1])
                active_rows = int(r[2])
                est_impressions = total_rows * 10
                rt_ctr = round(active_rows / est_impressions, 4) if est_impressions > 0 else 0
                if rt_ctr > 0:
                    ctr_trend.append((r[0], rt_ctr))
        ctr_trend.sort(key=lambda x: str(x[0]))

        # Cluster distribution (with semantic names from interest tags)
        cluster_dist = get_cluster_distribution()

        # Content type ratio
        music_count = db.session.execute(
            db.text("SELECT COUNT(*) FROM rt_content_hot "
            "WHERE content_type = 'music'")
        ).scalar() or 0
        video_count = db.session.execute(
            db.text("SELECT COUNT(*) FROM rt_content_hot "
            "WHERE content_type = 'video'")
        ).scalar() or 0

        # 推荐策略分布 — 基于冷启动聚类实时计算
        strategy_names = {"als_cf": "ALS协同过滤", "coldstart": "冷启动策略", "established": "存量策略", "exploration": "探索策略", "content_based": "内容推荐", "hybrid": "混合推荐"}
        # 先尝试离线表，为空时使用聚类分布
        strategy_rows = db.session.execute(
            db.text("SELECT strategy, COUNT(*) as cnt FROM offline_recommendations "
            "GROUP BY strategy ORDER BY cnt DESC")
        ).fetchall()
        if strategy_rows:
            strategy_distribution = [
                {"name": strategy_names.get(r[0], r[0]), "value": r[1]} for r in strategy_rows
            ]
        else:
            # 实时：从冷启动聚类 + 用户画像推算
            cold_cs = db.session.execute(db.text(
                "SELECT COUNT(*) FROM rt_user_profile WHERE is_cold_start = 1"
            )).scalar() or 0
            est_cs = db.session.execute(db.text(
                "SELECT COUNT(*) FROM rt_user_profile WHERE is_cold_start = 0 AND behavior_count > 50"
            )).scalar() or 0
            exp_cs = db.session.execute(db.text(
                "SELECT COUNT(*) FROM rt_user_profile WHERE is_cold_start = 0 AND behavior_count <= 50"
            )).scalar() or 0
            strategy_distribution = [
                {"name": "冷启动策略", "value": cold_cs},
                {"name": "存量策略", "value": est_cs},
                {"name": "探索策略", "value": exp_cs},
            ]

        # 覆盖率 & 多样性 — 实时计算
        cov_row = db.session.execute(db.text(
            "SELECT (SELECT COUNT(DISTINCT content_id) FROM rt_content_hot) as covered, "
            "(SELECT COUNT(*) FROM content_metadata) as total"
        )).fetchone()
        real_coverage = round(float(cov_row[0]) / max(cov_row[1], 1), 4) if cov_row else 0.0
        div_rows = db.session.execute(db.text(
            "SELECT content_type, COUNT(*) as cnt FROM rt_content_hot GROUP BY content_type"
        )).fetchall()
        total_hot = sum(r[1] for r in div_rows)
        real_diversity = round(1 - sum((r[1] / total_hot) ** 2 for r in div_rows), 4) if total_hot > 0 else 0.0

        return {
            "online_users": online_users,
            "daily_recommendations": daily_recs,
            "ctr": float(rt_ctr) if rt_ctr else 0.0,
            "avg_watch_duration": float(rt_avg_watch) if rt_avg_watch else 0.0,
            "coverage": real_coverage,
            "diversity": real_diversity,
            "hot_content_top5": [
                {"content_id": r[0], "content_type": r[1], "hot_score": float(r[2])}
                for r in hot_top5
            ],
            "coldstart_new_today": coldstart_count,
            "ctr_trend": [
                {"date": str(r[0]), "value": float(r[1]) if r[1] else 0}
                for r in ctr_trend
            ],
            "cluster_distribution": cluster_dist,
            "content_ratio": {
                "music": music_count,
                "video": video_count,
            },
            "strategy_distribution": strategy_distribution,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[DashboardPusher] Error: {e}")
        return None


def _push_loop(interval: float = 5.0):
    global _push_running, _app
    print("[DashboardPusher] Push loop started")
    with _app.app_context():
        while _push_running:
            snapshot = _fetch_dashboard_snapshot()
            if snapshot:
                socketio.emit("dashboard_update", {"type": "dashboard_snapshot", "data": snapshot})
            time.sleep(interval)


def start_dashboard_push(app, interval: float = 5.0):
    global _push_running, _push_thread, _app
    if _push_running:
        return
    _app = app
    _push_running = True
    _push_thread = threading.Thread(target=_push_loop, args=(interval,), daemon=True)
    _push_thread.start()


def stop_dashboard_push():
    global _push_running
    _push_running = False


def push_metric_update(metric_name: str, value: float):
    socketio.emit("dashboard_update", {
        "type": "metric_update",
        "data": {"name": metric_name, "value": value},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
