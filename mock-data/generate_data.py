#!/usr/bin/env python3
"""模拟数据生成器 — 生成3类JSON Lines文件供Flume→Kafka管道使用"""

import json
import random
import uuid
import os
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
#  配置参数
# ============================================================
NUM_USERS = 10000          # 注册用户数
NUM_CONTENTS = 8000        # 内容数（音乐+视频）
NUM_BEHAVIORS = 50000      # 行为事件数

MUSIC_RATIO = 0.6          # 音乐占内容比例

# 常量池
DEVICE_TYPES = ["android", "ios", "web", "ipad"]
OS_VERSIONS = {"android": ["12.0", "13.0", "14.0"], "ios": ["16.0", "17.0", "18.0"], "web": ["-"], "ipad": ["17.0"]}
APP_VERSIONS = ["3.0.0", "3.1.0", "3.2.0", "3.2.1"]
CHANNELS = ["organic", "app_store_search", "ad_google", "ad_facebook", "wechat_mini", "douyin_campaign", "referral", "seo"]
REGIONS = ["CN-BJ", "CN-SH", "CN-GD", "CN-ZJ", "CN-SC", "CN-HB", "CN-HN", "CN-FJ", "CN-SD", "CN-JS"]
AGE_GROUPS = ["<18", "18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["male", "female", "unknown"]

MUSIC_STYLES = ["pop", "rock", "jazz", "classical", "electronic", "hip-hop", "r&b", "folk", "indie", "metal",
                "punk", "reggae", "blues", "country", "latin", "k-pop", "anime", "lofi", "ambient", "disco"]
VIDEO_CATEGORIES = ["gaming", "cooking", "travel", "fitness", "education", "tech_review", "vlog", "comedy",
                    "music_video", "movie_clip", "news", "sports", "animation", "dance", "pet"]
TAGS_POOL = ["华语", "欧美", "日韩", "流行", "经典", "治愈", "励志", "伤感", "甜蜜", "燃向",
             "古风", "电子", "摇滚", "民谣", "说唱", "二次元", "影视", "游戏", "运动", "美食",
             "旅行", "时尚", "科技", "学习", "生活", "搞笑", "萌宠", "舞蹈", "翻唱", "原创",
             "2024", "2025", "怀旧", "新歌", "热歌", "冷门", "小众", "网红", "校园", "职场",
             "轻音乐", "纯音乐", "DJ", "串烧", "混音", "教程", "开箱", "测评", "挑战", "日常"]

MUSIC_TITLES = ["{}的旋律".format(i) for i in range(1, 500)] + \
               ["{}{}".format(style.capitalize(), i) for style in MUSIC_STYLES for i in range(1, 20)]
MUSIC_ARTISTS = ["歌手{}".format(i) for i in range(1, 200)] + \
                ["Artist_{}".format(i) for i in range(1, 100)]
VIDEO_TITLES = ["{}视频{}".format(cat, i) for cat in VIDEO_CATEGORIES for i in range(1, 40)] + \
               ["精彩{}合集{}".format(cat, i) for cat in VIDEO_CATEGORIES for i in range(1, 30)]
VIDEO_AUTHORS = ["UP主{}".format(i) for i in range(1, 300)] + \
                ["创作者_{}".format(i) for i in range(1, 100)]

EVENT_TYPES = ["play", "like", "favorite", "comment", "skip", "complete", "share"]
EVENT_WEIGHTS = [0.40, 0.15, 0.08, 0.05, 0.12, 0.12, 0.08]  # 播放最多

SOURCE_STRATEGIES = ["coldstart_cluster", "als_cf", "item2vec", "hot_trending", "dp_diversity", "epsilon_explore"]

NETWORKS = ["wifi", "4g", "5g"]
QUALITIES = ["low", "medium", "high"]


def generate_content_metadata():
    """生成内容元数据 (content_metadata topic)"""
    records = []
    music_count = int(NUM_CONTENTS * MUSIC_RATIO)
    video_count = NUM_CONTENTS - music_count

    for i in range(1, music_count + 1):
        style = random.choice(MUSIC_STYLES)
        tags = random.sample(TAGS_POOL, random.randint(3, 6))
        records.append({
            "content_id": i,
            "content_type": "music",
            "title": random.choice(MUSIC_TITLES) if i <= len(MUSIC_TITLES) else f"歌曲_{i}",
            "artist_or_author": random.choice(MUSIC_ARTISTS),
            "style_or_category": style,
            "tags": tags,
            "duration": round(random.uniform(120.0, 360.0), 1),
            "language": random.choices(["zh-CN", "en-US", "ja-JP", "ko-KR"], weights=[0.5, 0.3, 0.1, 0.1])[0],
            "bpm": round(random.uniform(60.0, 180.0), 1),
            "release_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 2000))).strftime("%Y-%m-%d"),
            "action": "create"
        })

    for i in range(music_count + 1, NUM_CONTENTS + 1):
        cat = random.choice(VIDEO_CATEGORIES)
        tags = random.sample(TAGS_POOL, random.randint(2, 5))
        records.append({
            "content_id": i,
            "content_type": "video",
            "title": random.choice(VIDEO_TITLES) if (i - music_count) <= len(VIDEO_TITLES) else f"视频_{i}",
            "artist_or_author": random.choice(VIDEO_AUTHORS),
            "style_or_category": cat,
            "tags": tags,
            "duration": round(random.uniform(15.0, 1800.0), 1),
            "language": random.choices(["zh-CN", "en-US", "ja-JP"], weights=[0.6, 0.3, 0.1])[0],
            "bpm": 0.0,
            "release_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 2000))).strftime("%Y-%m-%d"),
            "action": "create"
        })

    random.shuffle(records)
    return records


def generate_user_register():
    """生成用户注册事件 (user_register topic)"""
    records = []
    base_time = datetime.now() - timedelta(days=180)

    for i in range(1, NUM_USERS + 1):
        device = random.choices(DEVICE_TYPES, weights=[0.45, 0.35, 0.15, 0.05])[0]
        os_ver = random.choice(OS_VERSIONS[device])
        register_time = base_time + timedelta(
            days=random.randint(0, 179),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        records.append({
            "user_id": 1000000 + i,
            "register_time": register_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "device_type": device,
            "os_version": os_ver,
            "register_channel": random.choices(CHANNELS, weights=[0.25, 0.15, 0.12, 0.10, 0.12, 0.08, 0.10, 0.08])[0],
            "interest_tags": random.sample(TAGS_POOL, random.randint(2, 6)),
            "region": random.choice(REGIONS),
            "age_group": random.choices(AGE_GROUPS, weights=[0.05, 0.25, 0.35, 0.20, 0.10, 0.05])[0],
            "gender": random.choices(GENDERS, weights=[0.48, 0.48, 0.04])[0]
        })

    return records


def generate_user_behavior(users, contents):
    """生成用户行为事件 (user_behavior topic)"""
    records = []
    base_time = datetime.now() - timedelta(hours=24)
    user_ids = [u["user_id"] for u in users]
    content_list = [(c["content_id"], c["content_type"]) for c in contents]

    for i in range(NUM_BEHAVIORS):
        user_id = random.choice(user_ids)
        content_id, content_type = random.choice(content_list)
        event_type = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS)[0]
        event_time = base_time + timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
            microseconds=random.randint(0, 999999)
        )
        device = random.choices(DEVICE_TYPES, weights=[0.45, 0.35, 0.15, 0.05])[0]
        duration = random.uniform(15, 360) if content_type == "music" else random.uniform(30, 1800)
        progress = random.uniform(0.05, 1.0)

        records.append({
            "event_id": f"evt_{event_time.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "content_id": content_id,
            "content_type": content_type,
            "event_type": event_type,
            "event_time": event_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{event_time.microsecond:06d}"[:3] + "Z",
            "duration": round(duration, 1),
            "progress": round(min(progress, 1.0), 4),
            "device_type": device,
            "os_version": random.choice(OS_VERSIONS[device]),
            "app_version": random.choice(APP_VERSIONS),
            "channel": random.choices(CHANNELS, weights=[0.25, 0.15, 0.12, 0.10, 0.12, 0.08, 0.10, 0.08])[0],
            "session_id": f"sess_{uuid.uuid4().hex[:8]}",
            "region": random.choice(REGIONS),
            "source": "recommendation_feed",
            "source_strategy": random.choice(SOURCE_STRATEGIES),
            "source_rank": random.randint(1, 50),
            "extra": {
                "network": random.choice(NETWORKS),
                "quality": random.choice(QUALITIES)
            }
        })

    # 按时间排序
    records.sort(key=lambda x: x["event_time"])
    return records


def write_jsonl(filename, records):
    """写入JSON Lines格式文件"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  ✓ {filename} — {len(records):,} 条记录")


def main():
    print("=" * 60)
    print("  冷启动推荐系统 — 模拟数据生成器")
    print("=" * 60)

    # 1. 内容元数据
    print("\n[1/3] 生成内容元数据...")
    contents = generate_content_metadata()
    write_jsonl("content_metadata.json", contents)

    # 2. 用户注册
    print("\n[2/3] 生成用户注册事件...")
    users = generate_user_register()
    write_jsonl("user_register.json", users)

    # 3. 用户行为
    print("\n[3/3] 生成用户行为事件...")
    behaviors = generate_user_behavior(users, contents)
    write_jsonl("user_behavior.json", behaviors)

    # 统计
    print("\n" + "=" * 60)
    print(f"  总计: {len(contents) + len(users) + len(behaviors):,} 条记录")
    print(f"  输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
