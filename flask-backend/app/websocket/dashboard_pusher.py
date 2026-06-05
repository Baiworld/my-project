"""FR-15 DashboardPusher — push dashboard metrics to clients"""

import threading
import time
from datetime import datetime, timezone
from flask import current_app
from app.extensions import db, socketio

_push_running = False
_push_thread = None
_app = None


def _fetch_dashboard_snapshot() -> dict:
    try:
        online_users = db.session.execute(
            db.text("SELECT COUNT(DISTINCT user_id) FROM rt_user_profile "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)")
        ).scalar() or 0

        daily_recs = db.session.execute(
            db.text("SELECT COUNT(*) FROM offline_recommendations "
            "WHERE DATE(compute_time) = CURDATE()")
        ).scalar() or 0

        ctr_row = db.session.execute(
            db.text("SELECT ctr FROM offline_metrics WHERE metric_date = CURDATE() "
            "AND user_group = 'all' AND content_type = 'all' LIMIT 1")
        ).fetchone()

        hot_top5 = db.session.execute(
            db.text("SELECT content_id, content_type, hot_score FROM rt_content_hot "
            "WHERE window_end = (SELECT MAX(window_end) FROM rt_content_hot) "
            "ORDER BY hot_score DESC LIMIT 5")
        ).fetchall()

        coldstart_count = db.session.execute(
            db.text("SELECT COUNT(*) FROM rt_user_profile "
            "WHERE is_cold_start = 1 "
            "AND window_end >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        ).scalar() or 0

        return {
            "online_users": online_users,
            "daily_recommendations": daily_recs,
            "ctr": float(ctr_row[0]) if ctr_row else 0.0,
            "avg_watch_duration": 0,
            "hot_content_top5": [
                {"content_id": r[0], "content_type": r[1], "hot_score": float(r[2])}
                for r in hot_top5
            ],
            "coldstart_new_today": coldstart_count,
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
