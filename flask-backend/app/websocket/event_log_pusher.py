"""FR-15 EventLogPusher — push user behavior events to clients in real time"""

import json
import threading
import time
from collections import deque
from datetime import datetime, timezone
from app.extensions import db, socketio

_push_running = False
_push_thread = None
_last_event_id = 0
_app = None

# Cache recent events so new clients get immediate data
_recent_events = deque(maxlen=50)


def _poll_and_push():
    global _last_event_id

    try:
        rows = db.session.execute(
            db.text(
                "SELECT id, user_id, play_count, like_rate, favorite_rate, "
                "share_count, comment_count, content_type_ratio "
                "FROM rt_user_profile "
                "WHERE id > :last_id "
                "ORDER BY id ASC LIMIT 50"
            ),
            {"last_id": _last_event_id}
        ).fetchall()

        if not rows:
            return

        for row in rows:
            rid = row[0]
            user_id = row[1]
            play_count = row[2] or 0
            like_rate = row[3] or 0
            favorite_rate = row[4] or 0
            share_count = row[5] or 0
            comment_count = row[6] or 0
            content_type_ratio = row[7]

            content_type = "音乐"
            if content_type_ratio:
                try:
                    ratio = json.loads(content_type_ratio) if isinstance(content_type_ratio, str) else content_type_ratio
                    if isinstance(ratio, dict) and ratio.get("video", 0) > 0.5:
                        content_type = "视频"
                except Exception:
                    pass

            events = []
            if play_count > 0:
                events.append(("播放", play_count))
            if like_rate > 0:
                events.append(("点赞", int(like_rate * 100)))
            if favorite_rate > 0:
                events.append(("收藏", int(favorite_rate * 100)))
            if share_count > 0:
                events.append(("分享", share_count))
            if comment_count > 0:
                events.append(("评论", comment_count))

            for event_type, _count in events:
                payload = {
                    "type": "user_event",
                    "data": {
                        "user_id": user_id,
                        "event_type": event_type,
                        "content_type": content_type,
                        "content_id": rid,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }
                _recent_events.append(payload)
                socketio.emit("user_event", payload)

            if rid > _last_event_id:
                _last_event_id = rid

    except Exception as e:
        print(f"[EventLogPusher] Error: {e}")


def _event_loop(interval: float = 2.0):
    global _push_running, _app
    print("[EventLogPusher] Push loop started")
    with _app.app_context():
        # Process all existing data first
        _poll_and_push()
        while _push_running:
            _poll_and_push()
            time.sleep(interval)


def _on_client_connect():
    """Send cached recent events to newly connected client."""
    for event in _recent_events:
        socketio.emit("user_event", event, to=None)


def start_event_push(app, interval: float = 2.0):
    global _push_running, _push_thread, _app
    if _push_running:
        return
    _app = app
    _push_running = True
    _push_thread = threading.Thread(target=_event_loop, args=(interval,), daemon=True)
    _push_thread.start()


def stop_event_push():
    global _push_running
    _push_running = False


def push_event_log(event: dict):
    payload = {
        "type": "user_event",
        "data": {
            "user_id": event.get("user_id"),
            "event_type": event.get("event_type"),
            "content_type": event.get("content_type"),
            "content_title": event.get("content_title", ""),
            "region": event.get("region", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    _recent_events.append(payload)
    socketio.emit("user_event", payload)


def push_batch_events(events: list[dict]):
    for event in events:
        push_event_log(event)


def send_cached_events():
    """Send cached events to all clients (called when a new client connects)."""
    for event in _recent_events:
        socketio.emit("user_event", event)
