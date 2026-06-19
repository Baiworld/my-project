"""FR-15 EventLogPusher — push user behavior events to clients in real time"""

import json
import random
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

# Content title cache
_content_titles_cache = {"music": [], "video": []}


def _refresh_content_cache():
    """Preload content titles for random event display"""
    try:
        rows = db.session.execute(db.text(
            "SELECT h.content_id, h.content_type, "
            "COALESCE(MAX(m.title), CONCAT(IF(MAX(h.content_type)='music','音乐','视频'), ' #', MAX(h.content_id))) AS title, "
            "MAX(m.artist_or_author) as artist "
            "FROM rt_content_hot h "
            "LEFT JOIN content_metadata m ON h.content_id = m.content_id AND h.content_type = m.content_type "
            "GROUP BY h.content_id, h.content_type "
            "ORDER BY MAX(h.hot_score) DESC LIMIT 200"
        )).fetchall()
        music_list = []
        video_list = []
        for r in rows:
            item = {"content_id": int(r[0]), "title": str(r[2]), "artist": str(r[3] or "")}
            if str(r[1]) == "music":
                music_list.append(item)
            else:
                video_list.append(item)
        if music_list:
            _content_titles_cache["music"] = music_list
        if video_list:
            _content_titles_cache["video"] = video_list
    except Exception as e:
        print(f"[EventLogPusher] Content cache refresh failed: {e}")


def _pick_content(content_type: str) -> dict:
    """Pick a random content from the cache for the given type"""
    items = _content_titles_cache.get(content_type, [])
    if not items:
        items = _content_titles_cache.get("music", []) or _content_titles_cache.get("video", [])
    if items:
        return random.choice(items)
    return {"content_id": 0, "title": "", "artist": ""}


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

        # Refresh content cache periodically
        if random.random() < 0.1:  # ~10% chance per poll
            _refresh_content_cache()

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
                content = _pick_content(content_type)
                payload = {
                    "type": "user_event",
                    "data": {
                        "user_id": user_id,
                        "event_type": event_type,
                        "content_type": content_type,
                        "content_id": content["content_id"],
                        "content_title": content["title"],
                        "content_artist": content["artist"],
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
        db.session.remove()
        while _push_running:
            _poll_and_push()
            db.session.remove()
            time.sleep(interval)


def _seed_recent_events():
    """从数据库加载最近 20 条有行为的事件到缓存，新客户端连接即可看到"""
    global _recent_events
    try:
        rows = db.session.execute(
            db.text(
                "SELECT id, user_id, play_count, like_rate, favorite_rate, "
                "share_count, comment_count, content_type_ratio "
                "FROM rt_user_profile "
                "WHERE play_count > 0 OR like_rate > 0 OR favorite_rate > 0 "
                "OR share_count > 0 OR comment_count > 0 "
                "ORDER BY id DESC LIMIT 20"
            )
        ).fetchall()
        import json
        for row in reversed(rows):
            rid, user_id, play_count, like_rate, fav_rate, share, comment, ratio = row
            content_type = "音乐"
            if ratio:
                try:
                    r = json.loads(ratio) if isinstance(ratio, str) else ratio
                    if isinstance(r, dict) and r.get("video", 0) > 0.5:
                        content_type = "视频"
                except Exception:
                    pass
            events = []
            if play_count and play_count > 0:
                events.append(("播放", play_count))
            if like_rate and float(like_rate) > 0:
                events.append(("点赞", int(float(like_rate) * 100)))
            if fav_rate and float(fav_rate) > 0:
                events.append(("收藏", int(float(fav_rate) * 100)))
            if share and int(share) > 0:
                events.append(("分享", int(share)))
            if comment and int(comment) > 0:
                events.append(("评论", int(comment)))
            for event_type, count in events:
                from datetime import datetime, timezone
                _recent_events.append({
                    "type": "user_event",
                    "data": {
                        "user_id": user_id,
                        "event_type": event_type,
                        "content_type": content_type,
                        "content_id": rid,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                })
    except Exception as e:
        print(f"[EventLogPusher] Seed cache error: {e}")


def start_event_push(app, interval: float = 2.0):
    global _push_running, _push_thread, _app, _last_event_id
    if _push_running:
        return
    _app = app
    with app.app_context():
        max_id = db.session.execute(
            db.text("SELECT COALESCE(MAX(id), 0) FROM rt_user_profile")
        ).scalar() or 0
        _last_event_id = int(max_id)
        # 预加载最近 20 条有行为的事件到缓存，新客户端立即可见
        _seed_recent_events()
        db.session.remove()
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


def send_cached_events(sid: str = None):
    """Send cached events to a specific client (called when a new client connects).

    If sid is provided, events are sent only to that client.
    If sid is None, sends to all (backward compatible).
    """
    for event in _recent_events:
        socketio.emit("user_event", event, to=sid)
