"""FR-15 DashboardPusher — push dashboard metrics to clients"""

import threading
import time
from datetime import datetime, timezone, date as date_cls
from app.extensions import db, socketio
from app.utils.cluster_utils import get_cluster_distribution

_push_running = False
_push_thread = None
_app = None


def _calc_trend(curr, prev) -> dict:
    """Calculate trend percentage between current and previous value."""
    if not prev or prev == 0:
        return {"value": "", "type": "up"}
    pct = ((curr - prev) / prev) * 100
    sign = "+" if pct >= 0 else ""
    return {"value": f"{sign}{pct:.1f}%", "type": "up" if pct >= 0 else "down"}


def _fetch_dashboard_snapshot() -> dict:
    try:
        today_date = date_cls.today()
        today_str = str(today_date)
        yesterday_str = str(today_date.replace(day=today_date.day - 1) if today_date.day > 1 else today_date.replace(month=today_date.month - 1, day=28))

        # ── Today's core metrics from rt_user_profile ──
        today_metrics = db.session.execute(db.text("""
            SELECT
                COUNT(DISTINCT user_id) as total_users,
                COUNT(DISTINCT CASE WHEN play_count > 0 THEN user_id END) as active_users,
                COALESCE(SUM(play_count), 0) as total_plays,
                COUNT(*) as total_rows,
                SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows,
                SUM(play_count * completion_rate * 180) as total_play_sec
            FROM rt_user_profile
            WHERE DATE(window_end) = :d
        """), {"d": today_str}).fetchone()
        # Fallback to empty row if no data for today
        if not today_metrics or today_metrics[0] == 0:
            today_metrics = type('obj', (object,), {'total_users': 0, 'active_users': 0, 'total_plays': 0,
                'total_rows': 0, 'active_rows': 0, 'total_play_sec': 0})()

        # ── Yesterday's core metrics (for trend calculation) ──
        yesterday_metrics = db.session.execute(db.text("""
            SELECT
                COUNT(DISTINCT user_id) as total_users,
                COALESCE(SUM(play_count), 0) as total_plays,
                COUNT(*) as total_rows,
                SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows,
                SUM(play_count * completion_rate * 180) as total_play_sec
            FROM rt_user_profile
            WHERE DATE(window_end) = :d
        """), {"d": yesterday_str}).fetchone()

        # ── Compute today's metric values ──
        today_total_users = int(today_metrics.total_users)
        today_total_plays = int(today_metrics.total_plays)
        today_total_rows = int(today_metrics.total_rows)
        today_active_rows = int(today_metrics.active_rows)
        today_active_users = int(today_metrics.active_users)
        today_play_sec = float(today_metrics.total_play_sec or 0)

        daily_recs = today_total_plays
        # 使用行级别 row-level 公式，与趋势线/Yesterday/API 统一
        est_impressions = today_total_rows * 10
        rt_ctr = round(today_active_rows / max(est_impressions, 1), 4) if est_impressions > 0 else 0.0
        rt_avg_watch = round(today_play_sec / max(today_total_users, 1), 2) if today_total_users > 0 else 0.0

        # ── Offline fallback for zero-data scenarios ──
        offline_row = db.session.execute(db.text(
            "SELECT ctr, avg_watch_duration, total_impressions, cvr, coverage, diversity "
            "FROM offline_metrics WHERE user_group = 'all' AND content_type = 'all' "
            "ORDER BY metric_date DESC LIMIT 1"
        )).fetchone()
        fallback_ctr = float(offline_row.ctr) if offline_row and offline_row.ctr else 0.0
        fallback_watch = float(offline_row.avg_watch_duration) if offline_row and offline_row.avg_watch_duration else 0.0
        fallback_recs = int(offline_row.total_impressions) if offline_row and offline_row.total_impressions else 0
        fallback_cvr = float(offline_row.cvr) if offline_row and offline_row.cvr else 0.0
        fallback_coverage = float(offline_row.coverage) if offline_row and offline_row.coverage else 0.0
        fallback_diversity = float(offline_row.diversity) if offline_row and offline_row.diversity else 0.0

        if daily_recs == 0:
            daily_recs = fallback_recs
        if rt_ctr == 0:
            rt_ctr = fallback_ctr
        if rt_avg_watch == 0:
            rt_avg_watch = fallback_watch

        # ── 24h online users ──
        online_users = int(db.session.execute(db.text(
            "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile "
            "WHERE window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        )).scalar() or 0)

        # Fallback: if rt is empty, use offline_metrics total_users
        online_users_fallback = False
        if online_users == 0:
            online_users = int(db.session.execute(db.text(
                "SELECT total_users FROM offline_metrics "
                "WHERE user_group = 'all' AND content_type = 'all' "
                "ORDER BY metric_date DESC LIMIT 1"
            )).scalar() or 0)
            online_users_fallback = True

        # ── Metrics trends (today vs yesterday) ──
        prev_total_users = int(yesterday_metrics.total_users) if yesterday_metrics and yesterday_metrics.total_users else 0
        prev_total_plays = int(yesterday_metrics.total_plays) if yesterday_metrics and yesterday_metrics.total_plays else 0
        prev_total_rows = int(yesterday_metrics.total_rows) if yesterday_metrics and yesterday_metrics.total_rows else 0
        prev_active_rows = int(yesterday_metrics.active_rows) if yesterday_metrics and yesterday_metrics.active_rows else 0
        prev_play_sec = float(yesterday_metrics.total_play_sec or 0) if yesterday_metrics else 0.0

        prev_ctr = round(prev_active_rows / max(prev_total_rows * 10, 1), 4) if prev_total_rows > 0 else 0.0
        prev_avg_watch = round(prev_play_sec / max(prev_total_users, 1), 2) if prev_total_users > 0 else 0.0

        metrics_trend = {
            "online_users": {"value": "0%", "type": "up"} if online_users_fallback
                            else _calc_trend(today_total_users, prev_total_users),
            "daily_recommendations": _calc_trend(daily_recs, prev_total_plays),
            "ctr": _calc_trend(rt_ctr, prev_ctr),
            "avg_watch_duration": _calc_trend(rt_avg_watch, prev_avg_watch),
            "coverage": {"value": "", "type": "up"},  # Computed below
        }

        # ── CTR & Play count trend (last 7 days) ──
        # 策略：rt_user_profile 有数据的日期优先用实时计算（统一公式），
        #       仅 rt 没有数据的日期才回退到 offline_metrics

        offline_ctr = db.session.execute(db.text(
            "SELECT metric_date, ctr FROM offline_metrics "
            "WHERE user_group = 'all' AND content_type = 'all' "
            "AND metric_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) ORDER BY metric_date"
        )).fetchall()

        offline_imp = db.session.execute(db.text(
            "SELECT metric_date, total_impressions FROM offline_metrics "
            "WHERE user_group = 'all' AND content_type = 'all' "
            "AND metric_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) ORDER BY metric_date"
        )).fetchall()

        rt_daily_rows = db.session.execute(db.text("""
            SELECT DATE(window_end) as d,
                   COUNT(*) as total_rows,
                   SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows
            FROM rt_user_profile
            WHERE window_end >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(window_end) ORDER BY d
        """)).fetchall()

        # 从 rt 数据构建同公式的 CTR 映射: date -> (ctr, impression_count)
        rt_ctr_map = {}
        rt_imp_map = {}
        for r in rt_daily_rows:
            d = str(r[0])
            total_rows_v = int(r[1])
            active_rows_v = int(r[2])
            est_imp = total_rows_v * 10
            ctr_val = round(active_rows_v / est_imp, 4) if est_imp > 0 else 0
            if ctr_val > 0:
                rt_ctr_map[d] = ctr_val
            rt_imp_map[d] = total_rows_v

        # 构建 unified trend：先收集所有日期，再统一填充
        all_dates = set()
        for r in offline_ctr:
            all_dates.add(str(r[0]))
        for r in rt_daily_rows:
            all_dates.add(str(r[0]))

        offline_ctr_map = {str(r[0]): float(r[1]) for r in offline_ctr}
        offline_imp_map = {str(r[0]): int(r[1]) if r[1] else 0 for r in offline_imp}

        ctr_trend = []
        play_count_trend = []
        for d in sorted(all_dates):
            # CTR: 优先用 rt 实时计算（统一公式），回退 offline
            if d in rt_ctr_map:
                ctr_val = rt_ctr_map[d]
            elif d in offline_ctr_map:
                ctr_val = offline_ctr_map[d]
            else:
                ctr_val = 0.0
            ctr_trend.append((d, ctr_val))

            # Play count: 优先用 rt 数据，回退 offline
            if d in rt_imp_map and rt_imp_map[d] > 0:
                imp_val = rt_imp_map[d]
            elif d in offline_imp_map:
                imp_val = offline_imp_map[d]
            else:
                imp_val = 0
            play_count_trend.append((d, imp_val))

        # Ensure today is always present
        today_in_ctr = any(str(r[0]) == today_str for r in ctr_trend)
        if not today_in_ctr:
            today_ctr_val = rt_ctr_map.get(today_str, 0.0)
            ctr_trend.append((today_str, today_ctr_val))
        today_in_play = any(str(r[0]) == today_str for r in play_count_trend)
        if not today_in_play:
            play_count_trend.append((today_str, rt_imp_map.get(today_str, 0)))

        ctr_trend.sort(key=lambda x: x[0])
        play_count_trend.sort(key=lambda x: x[0])

        # ── Funnel data ──
        # CVR (完播率) from rt, with offline fallback
        rt_cvr = float(db.session.execute(db.text(
            "SELECT ROUND(AVG(completion_rate), 4) FROM rt_user_profile WHERE DATE(window_end) = :d"
        ), {"d": today_str}).scalar() or 0.0)
        if rt_cvr == 0.0:
            rt_cvr = fallback_cvr

        coldstart_conversion = float(db.session.execute(db.text(
            "SELECT ROUND(SUM(CASE WHEN play_sum > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 4) "
            "FROM (SELECT user_id, SUM(play_count) as play_sum FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND DATE(window_end) = :d GROUP BY user_id) t"
        ), {"d": today_str}).scalar() or 0.0)

        funnel_data = [
            {"value": 100, "name": "推荐曝光", "itemStyle": {"color": "#6366F1"}},
            {"value": max(1, round(rt_ctr * 100)), "name": "用户点击", "itemStyle": {"color": "#818CF8"}},
            {"value": max(1, round(rt_cvr * 100)), "name": "完播转化", "itemStyle": {"color": "#34D399"}},
            {"value": max(1, round(coldstart_conversion * 100)), "name": "冷启活跃", "itemStyle": {"color": "#FBBF24"}},
        ]

        # ── Coldstart vs Existing comparison ──
        compare_queries = [
            ("coldstart", "is_cold_start = 1"),
            ("existing", "is_cold_start = 0 AND behavior_count > 50"),
        ]
        compare_data = {}
        for grp_name, grp_filter in compare_queries:
            grp_row = db.session.execute(db.text(f"""
                SELECT
                    COUNT(*) as total_rows,
                    SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows,
                    ROUND(AVG(completion_rate), 4) as avg_cvr,
                    ROUND(SUM(play_count * completion_rate * 180) / NULLIF(COUNT(DISTINCT user_id), 1), 2) as avg_watch
                FROM rt_user_profile
                WHERE DATE(window_end) = :d AND {grp_filter}
            """), {"d": today_str}).fetchone()

            # Fallback: if no data today, look back 30 days for most recent date
            if not grp_row or grp_row[0] == 0:
                grp_row = db.session.execute(db.text(f"""
                    SELECT
                        COUNT(*) as total_rows,
                        SUM(CASE WHEN play_count > 0 THEN 1 ELSE 0 END) as active_rows,
                        ROUND(AVG(completion_rate), 4) as avg_cvr,
                        ROUND(SUM(play_count * completion_rate * 180) / NULLIF(COUNT(DISTINCT user_id), 1), 2) as avg_watch
                    FROM rt_user_profile
                    WHERE DATE(window_end) >= DATE_SUB(:d, INTERVAL 30 DAY) AND {grp_filter}
                """), {"d": today_str}).fetchone()

            if grp_row and grp_row[0] > 0:
                grp_total = int(grp_row[0])
                grp_active = int(grp_row[1])
                grp_ctr = round(grp_active / (grp_total * 10), 4) if grp_total > 0 else 0.0
                compare_data[grp_name] = {
                    "ctr": float(grp_ctr),
                    "cvr": float(grp_row[2] or 0),
                    "avg_watch_duration": float(grp_row[3] or 0),
                }
            else:
                compare_data[grp_name] = {"ctr": 0.0, "cvr": 0.0, "avg_watch_duration": 0.0}

        # Final fallback: if rt data is completely empty, use offline_metrics
        if compare_data.get("coldstart", {}).get("ctr", 0) == 0.0 \
           and compare_data.get("existing", {}).get("ctr", 0) == 0.0:
            for grp_name in ["coldstart", "existing"]:
                off_row = db.session.execute(db.text("""
                    SELECT ctr, cvr, avg_watch_duration FROM offline_metrics
                    WHERE user_group = :g AND content_type = 'all'
                    ORDER BY metric_date DESC LIMIT 1
                """), {"g": grp_name}).fetchone()
                if off_row:
                    compare_data[grp_name] = {
                        "ctr": float(off_row[0] or 0),
                        "cvr": float(off_row[1] or 0),
                        "avg_watch_duration": float(off_row[2] or 0),
                    }

        # ── Coldstart detailed stats ──
        coldstart_count = int(db.session.execute(db.text(
            "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        )).scalar() or 0)

        cs_avg_behavior = round(float(db.session.execute(db.text(
            "SELECT AVG(behavior_count) FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND DATE(window_end) = :d"
        ), {"d": today_str}).scalar() or 0.0), 1)

        # Coldstart yesterday (for trend)
        cs_yesterday_count = int(db.session.execute(db.text(
            "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND DATE(window_end) = :d"
        ), {"d": yesterday_str}).scalar() or 0)

        cs_yesterday_behavior = round(float(db.session.execute(db.text(
            "SELECT AVG(behavior_count) FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND DATE(window_end) = :d"
        ), {"d": yesterday_str}).scalar() or 0.0), 1)

        cs_yesterday_conv = float(db.session.execute(db.text(
            "SELECT ROUND(SUM(CASE WHEN play_sum > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 4) "
            "FROM (SELECT user_id, SUM(play_count) as play_sum FROM rt_user_profile "
            "WHERE is_cold_start = 1 AND DATE(window_end) = :d GROUP BY user_id) t"
        ), {"d": yesterday_str}).scalar() or 0.0)

        coldstart_stats = {
            "new_users": coldstart_count,
            "conversion_rate": round(coldstart_conversion * 100, 2),
            "avg_behavior_count": cs_avg_behavior,
            "trends": {
                "new_users": _calc_trend(coldstart_count, cs_yesterday_count),
                "conversion_rate": _calc_trend(coldstart_conversion, cs_yesterday_conv),
                "avg_behavior_count": _calc_trend(cs_avg_behavior, cs_yesterday_behavior),
            },
        }

        # ── Cluster distribution ──
        cluster_dist = get_cluster_distribution()

        # ── Content ratio ──
        music_count = int(db.session.execute(db.text(
            "SELECT COUNT(*) FROM rt_content_hot WHERE content_type = 'music'"
        )).scalar() or 0)
        video_count = int(db.session.execute(db.text(
            "SELECT COUNT(*) FROM rt_content_hot WHERE content_type = 'video'"
        )).scalar() or 0)

        # ── Active users ranking (top 10 by play_count + interaction) ──
        active_rows = db.session.execute(db.text(
            "SELECT user_id, behavior_count, play_count, "
            "ROUND(like_rate, 2) as like_rate, ROUND(favorite_rate, 2) as fav_rate, "
            "ROUND(completion_rate, 2) as comp_rate, is_cold_start, region "
            "FROM rt_user_profile "
            "WHERE DATE(window_end) = :d "
            "ORDER BY play_count DESC, behavior_count DESC LIMIT 10"
        ), {"d": today_str}).fetchall()
        active_users = [
            {
                "user_id": int(r[0]), "behavior_count": int(r[1] or 0),
                "play_count": int(r[2] or 0), "like_rate": float(r[3] or 0),
                "favorite_rate": float(r[4] or 0), "completion_rate": float(r[5] or 0),
                "is_cold_start": bool(r[6]), "region": str(r[7] or ""),
            }
            for r in active_rows
        ]

        # ── Region distribution ──
        region_rows = db.session.execute(db.text(
            "SELECT region, COUNT(DISTINCT user_id) as cnt "
            "FROM rt_user_profile "
            "WHERE window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR) AND region IS NOT NULL "
            "GROUP BY region ORDER BY cnt DESC LIMIT 15"
        )).fetchall()
        region_distribution = [{"name": str(r[0]), "value": int(r[1])} for r in region_rows]

        # ── Strategy distribution ──
        # 优先实时 rt_user_profile（反映实际用户分布），offline_recommendations 兜底
        cold_cs = int(db.session.execute(db.text(
            "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile WHERE is_cold_start = 1"
        )).scalar() or 0)
        est_cs = int(db.session.execute(db.text(
            "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile WHERE is_cold_start = 0 AND behavior_count > 50"
        )).scalar() or 0)
        exp_cs = int(db.session.execute(db.text(
            "SELECT COUNT(DISTINCT user_id) FROM rt_user_profile WHERE is_cold_start = 0 AND behavior_count <= 50"
        )).scalar() or 0)

        if cold_cs > 0 or est_cs > 0 or exp_cs > 0:
            strategy_distribution = [
                {"name": "冷启动策略", "value": cold_cs},
                {"name": "存量策略", "value": est_cs},
                {"name": "探索策略", "value": exp_cs},
            ]
        else:
            # Fallback 1: offline_recommendations
            strategy_names = {
                "als_cf": "ALS协同过滤", "coldstart": "冷启动策略",
                "established": "存量策略", "exploration": "探索策略",
                "content_based": "内容推荐", "hybrid": "混合推荐",
            }
            strategy_rows = db.session.execute(db.text(
                "SELECT strategy, COUNT(*) as cnt FROM offline_recommendations "
                "GROUP BY strategy ORDER BY cnt DESC"
            )).fetchall()
            if strategy_rows:
                strategy_distribution = [
                    {"name": strategy_names.get(r[0], r[0]), "value": int(r[1])}
                    for r in strategy_rows
                ]
            else:
                # Fallback 2: offline_metrics user_group breakdown
                off_dist = db.session.execute(db.text("""
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
                else:
                    strategy_distribution = []

        # ── Hot content Top 10 ──
        hot_top5 = db.session.execute(db.text(
            "SELECT h.content_id, h.content_type, MAX(h.hot_score) as hot_score, "
            "COALESCE(MAX(m.title), CONCAT(IF(MAX(h.content_type)='music','音乐','视频'), ' #', MAX(h.content_id))) AS title, "
            "MAX(m.artist_or_author) as artist_or_author, MAX(m.style_or_category) as style_or_category, "
            "MAX(m.tags) as tags, MAX(m.duration) as duration, MAX(m.language) as language, MAX(m.bpm) as bpm "
            "FROM rt_content_hot h "
            "LEFT JOIN content_metadata m ON h.content_id = m.content_id AND h.content_type = m.content_type "
            "GROUP BY h.content_id, h.content_type "
            "ORDER BY MAX(h.hot_score) DESC LIMIT 10"
        )).fetchall()

        # ── Coverage & Diversity ──
        cov_row = db.session.execute(db.text(
            "SELECT (SELECT COUNT(DISTINCT content_id) FROM rt_content_hot) as covered, "
            "(SELECT COUNT(*) FROM content_metadata) as total"
        )).fetchone()
        real_coverage = round(float(cov_row[0]) / max(cov_row[1], 1), 4) if cov_row else 0.0
        if real_coverage == 0.0:
            real_coverage = fallback_coverage
        div_rows = db.session.execute(db.text(
            "SELECT content_type, COUNT(*) as cnt FROM rt_content_hot GROUP BY content_type"
        )).fetchall()
        total_hot = sum(r[1] for r in div_rows)
        real_diversity = round(1 - sum((r[1] / max(total_hot, 1)) ** 2 for r in div_rows), 4) if total_hot > 0 else 0.0
        if real_diversity == 0.0:
            real_diversity = fallback_diversity

        # Coverage trend
        prev_coverage = 0.0
        if yesterday_metrics:
            prev_cov_row = db.session.execute(db.text(
                "SELECT (SELECT COUNT(DISTINCT content_id) FROM rt_content_hot WHERE DATE(window_end) = :d) as covered"
            ), {"d": yesterday_str}).scalar()
            if prev_cov_row:
                prev_coverage = round(float(prev_cov_row) / max(cov_row[1], 1), 4)
        metrics_trend["coverage"] = _calc_trend(real_coverage, prev_coverage)

        return {
            "data_date": today_str,
            "online_users": online_users,
            "daily_recommendations": daily_recs,
            "ctr": float(rt_ctr),
            "avg_watch_duration": float(rt_avg_watch),
            "coverage": float(real_coverage),
            "diversity": float(real_diversity),

            "metrics_trend": metrics_trend,

            "coldstart_stats": coldstart_stats,

            "ctr_trend": [
                {"date": str(r[0]), "value": float(r[1]) if r[1] else 0.0}
                for r in ctr_trend
            ],
            "play_count_trend": [
                {"date": str(r[0]), "value": int(r[1]) if r[1] else 0}
                for r in play_count_trend
            ],

            "funnel_data": funnel_data,
            "compare_data": compare_data,

            "hot_content_top5": [
                {
                    "content_id": int(r[0]), "content_type": str(r[1]), "hot_score": float(r[2]),
                    "title": str(r[3]), "artist_or_author": str(r[4] or ""),
                    "style_or_category": str(r[5] or ""), "tags": str(r[6] or ""),
                    "duration": float(r[7] or 0), "language": str(r[8] or ""), "bpm": float(r[9] or 0),
                }
                for r in hot_top5
            ],
            "cluster_distribution": [
                {"cluster_name": str(d["cluster_name"]), "count": int(d["count"])}
                for d in cluster_dist
            ],
            "content_ratio": {
                "music": music_count,
                "video": video_count,
            },
            "region_distribution": [
                {"name": str(d["name"]), "value": int(d["value"])}
                for d in region_distribution
            ],
            "active_users": active_users,
            "strategy_distribution": [
                {"name": str(d["name"]), "value": int(d["value"])}
                for d in strategy_distribution
            ],

            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[DashboardPusher] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _push_loop(interval: float = 5.0):
    global _push_running, _app
    print("[DashboardPusher] Push loop started")
    with _app.app_context():
        while _push_running:
            try:
                snapshot = _fetch_dashboard_snapshot()
                if snapshot:
                    socketio.emit("dashboard_update", {"type": "dashboard_snapshot", "data": snapshot})
            except Exception as e:
                print(f"[DashboardPusher] Error in loop: {e}")
            finally:
                db.session.remove()
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
