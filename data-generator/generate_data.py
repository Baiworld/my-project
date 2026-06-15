#!/usr/bin/env python3
"""
冷启动音乐与视频混合推荐系统 — 静态模拟数据生成器

根据业务需求文档 (FR-01) 和详细设计说明书 (§5.2) 定义的 JSON Schema，
为 3 个 Kafka Topic 各生成 10,000 条 JSONL 数据文件：

  Topic                输出文件                        说明
  ───────────────────  ──────────────────────────────  ──────────────────
  user_behavior        data/user_behavior.json         用户行为日志
  content_metadata     data/content_metadata.json      内容元数据 (音乐6:视频4)
  user_register        data/user_register.json         用户注册事件

用法:
  python generate_data.py                         # 批量生成 3×10,000 条
  python generate_data.py --topic user_behavior   # 仅生成指定 topic
  python generate_data.py --continuous --rate 5   # 持续生成，每秒 5 条 (Ctrl+C 停止)
"""

import json
import random
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── 固定随机种子，确保每次生成的数据一致 ──
random.seed(42)

DATA_DIR = Path(__file__).parent / "data"
RECORDS_PER_TOPIC = 10_000

# ============================================================================
# 数据池（与 MockDataGenerator.scala 保持一致）
# ============================================================================

USER_IDS = [str(i) for i in range(1, RECORDS_PER_TOPIC + 1)]
MUSIC_IDS = [str(i) for i in range(1, 6001)]
VIDEO_IDS = [str(i) for i in range(6001, 10001)]

# ── 音乐内容池 ──
MUSIC_TITLES = [
    "晴天", "七里香", "夜曲", "稻香", "青花瓷", "告白气球", "简单爱", "东风破",
    "平凡之路", "曾经的你", "蓝莲花", "故乡", "春天里", "怒放的生命", "存在",
    "演员", "丑八怪", "绅士", "刚刚好", "天外来物", "认真的雪", "暧昧",
    "光年之外", "泡沫", "喜欢你", "倒数", "来自天堂的魔鬼",
    "起风了", "芒种", "少年", "错位时空", "孤勇者", "星辰大海", "一路生花",
    "小幸运", "那些年", "后来", "可惜不是你", "十年", "好久不见", "浮夸",
    "Shape of You", "Blinding Lights", "Bohemian Rhapsody", "Hotel California",
    "Yesterday", "Imagine", "Hey Jude", "Rolling in the Deep", "Someone Like You",
    "See You Again", "Uptown Funk", "Dance Monkey", "Perfect", "Believer",
    "江南", "一千年以后", "修炼爱情", "可惜没如果", "不为谁而作的歌",
    "追光者", "体面", "说散就散", "凉凉", "知否知否", "左手指月",
    "夜空中最亮的星", "追梦赤子心", "我的天空", "太阳", "野子",
    "成都", "南山南", "斑马斑马", "理想三旬", "春风十里",
]

ARTISTS = [
    "周杰伦", "林俊杰", "陈奕迅", "薛之谦", "邓紫棋", "李荣浩", "许嵩",
    "Taylor Swift", "Ed Sheeran", "The Beatles", "Queen", "Coldplay", "Adele",
    "汪峰", "许巍", "朴树", "赵雷", "马頔", "宋冬野", "陈粒",
    "张杰", "华晨宇", "周深", "毛不易", "刘柏辛", "王以太",
    "Imagine Dragons", "Maroon 5", "Bruno Mars", "Billie Eilish", "Dua Lipa",
    "张国荣", "Beyond", "五月天", "苏打绿", "孙燕姿", "蔡依林", "张惠妹",
    "那英", "王菲", "刘若英", "莫文蔚", "梁静茹", "张韶涵",
]

ALBUMS = [
    "首发专辑", "精选集", "Live现场", "Remix版", "重置版", "周年纪念版",
    "录音室专辑", "EP", "单曲", "Demo合集", "不插电版", "交响乐版",
]

MUSIC_GENRES = ["流行", "摇滚", "古典", "爵士", "电子", "民谣", "R&B", "嘻哈"]

LANGUAGES = ["zh", "zh", "zh", "zh", "en", "en", "ja", "ko"]

QUALITIES = ["standard", "standard", "standard", "high", "high", "lossless"]

MUSIC_TAGS = [
    "治愈", "励志", "伤感", "甜蜜", "怀旧", "青春", "旅行", "深夜",
    "运动", "学习", "工作", "放松", "派对", "驾驶", "睡前", "起床",
    "经典", "新歌", "冷门", "热门", "华语", "欧美", "日语", "韩语",
    "钢琴", "吉他", "电子音", "中国风", "古风", "说唱", "轻音乐",
]

# ── 视频内容池 ──
VIDEO_TITLES = [
    "《晴天》官方MV", "《光年之外》现场版", "吉他教学入门第1课", "钢琴指法练习",
    "周末旅行Vlog", "城市夜景航拍", "美食探店：成都火锅", "健身教程：腹肌训练",
    "游戏实况：第20期", "搞笑集锦合集", "新闻早报", "科技新品开箱",
    "《演员》翻唱", "《平凡之路》指弹", "鼓教学：基础节奏",
    "电影解说：《肖申克的救赎》", "综艺精彩片段", "体育赛事集锦",
    "美妆教程：日常妆容", "穿搭分享：春季搭配", "家居改造vlog",
    "烹饪教程：宫保鸡丁", "手工艺制作", "绘画过程展示",
    "舞蹈教学：街舞入门", "瑜伽初级教程", "冥想引导",
    "产品测评：新耳机", "软件教程：Excel技巧", "面试经验分享",
    "留学日常vlog", "宠物搞笑视频", "魔术揭秘", "科普小知识",
    "《告白气球》舞蹈版", "乐团排练幕后", "音乐节现场回顾",
    "纪录片：中国美食", "动画短片", "微电影", "广告创意",
]

VIDEO_CATEGORIES = ["音乐MV", "直播", "教程", "生活Vlog", "娱乐", "体育", "新闻", "影视"]

VIDEO_QUALITIES = ["720p", "720p", "1080p", "1080p", "1080p", "4K"]

# ── 用户属性池 ──
SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
]

GIVEN_NAMES = [
    "伟", "芳", "敏", "静", "丽", "强", "磊", "洋",
    "勇", "艳", "杰", "军", "涛", "明", "超", "霞",
    "平", "刚", "文", "华", "飞", "斌", "浩",
    "宇", "然", "博", "涵", "萱", "怡", "琳", "瑞", "阳",
    "子轩", "子涵", "梓涵", "一诺", "欣怡", "雨桐", "宇轩", "诗涵",
    "嘉懿", "煜城", "思琪", "若曦", "浩宇", "皓轩", "乐瑶",
]

REGIONS = [
    "北京", "上海", "广州", "深圳", "杭州", "成都",
    "武汉", "南京", "西安", "重庆", "苏州", "天津",
    "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "大连",
]

# 城市名 → ISO 3166-2 省份代码映射
REGION_CODE_MAP = {
    "北京": "BJ", "上海": "SH", "广州": "GD", "深圳": "GD",
    "杭州": "ZJ", "成都": "SC", "武汉": "HB", "南京": "JS",
    "西安": "SN", "重庆": "CQ", "苏州": "JS", "天津": "TJ",
    "长沙": "HN", "郑州": "HA", "东莞": "GD", "青岛": "SD",
    "沈阳": "LN", "宁波": "ZJ", "昆明": "YN", "大连": "LN",
}

CHANNELS = ["app", "app", "app", "web", "web", "wechat_mini", "referral"]
AGE_GROUPS = ["18-24", "18-24", "25-34", "25-34", "25-34", "35-44", "35-44", "45+"]
GENDERS = ["male", "female", "female", "male", "unknown"]
DEVICES = ["android", "android", "android", "ios", "ios", "ios", "web"]
OS_VERSIONS = {"android": ["13.0", "14.0", "14.0", "14.0", "15.0"],
               "ios": ["16.0", "17.0", "17.0", "18.0"],
               "web": ["-"]}
APP_VERSIONS = ["3.1.0", "3.2.0", "3.2.1", "3.2.1", "3.2.1", "3.3.0"]
SOURCES = ["recommendation_feed", "recommendation_feed", "recommendation_feed",
           "search", "search", "hot_list", "related"]
SOURCE_STRATEGIES = ["coldstart_cluster", "coldstart_cluster", "als_cf", "item2vec",
                     "hot", "hot", "dpp_rerank", "epsilon_greedy"]
EVENT_TYPES = ["play", "play", "play", "play", "play", "play", "play", "play",
               "like", "like", "like",
               "favorite", "favorite",
               "skip", "skip", "skip",
               "complete", "complete",
               "share"]

# ============================================================================
# 幂律分布辅助函数（模拟马太效应）
# ============================================================================

def _zipf_index(max_idx: int) -> int:
    """幂律分布：小索引概率更高（模拟热门用户/内容）"""
    return min(int(abs(random.gauss(0, 1)) * max_idx * 0.25), max_idx - 1)


def _pick(arr: list) -> object:
    return random.choice(arr)


def _pick_n(arr: list, n: int) -> list:
    return random.sample(arr, min(n, len(arr)))


# ============================================================================
# 记录生成器
# ============================================================================

def generate_user_behavior(index: int) -> dict:
    """
    FR-01 / §5.2 — user_behavior 消息

    生成单条用户行为日志，音乐:视频 ≈ 6:4。
    """
    user_id = USER_IDS[_zipf_index(len(USER_IDS))]
    is_music = random.random() < 0.6
    content_id = (MUSIC_IDS if is_music else VIDEO_IDS)[_zipf_index(
        len(MUSIC_IDS) if is_music else len(VIDEO_IDS))]

    event_type = _pick(EVENT_TYPES)

    # 播放时长：音乐 120-360s，视频 30-600s
    if is_music:
        duration = round(random.uniform(120.0, 360.0), 1)
    else:
        duration = round(random.uniform(30.0, 600.0), 1)

    # 播放进度 (仅 play/complete 有意义)
    if event_type == "complete":
        progress = 1.0
    elif event_type == "play":
        progress = round(random.uniform(0.1, 0.95), 2)
    elif event_type == "skip":
        progress = round(random.uniform(0.0, 0.2), 2)
    else:
        progress = round(random.uniform(0.3, 1.0), 2)

    device = _pick(DEVICES)
    event_time = datetime.utcnow() - timedelta(
        seconds=random.randint(0, 600))  # 最近 10 分钟（实时数据）

    return {
        "event_id": f"evt_{event_time.strftime('%Y%m%d%H%M%S')}_{index:06x}",
        "user_id": user_id,
        "content_id": content_id,
        "content_type": "music" if is_music else "video",
        "event_type": event_type,
        "event_time": event_time.strftime("%Y-%m-%dT%H:%M:%S.") +
                      f"{event_time.microsecond // 1000:03d}Z",
        "duration": duration,
        "progress": progress,
        "device_type": device,
        "os_version": _pick(OS_VERSIONS[device]),
        "app_version": _pick(APP_VERSIONS),
        "channel": _pick(CHANNELS),
        "session_id": f"sess_{int(time.time() * 1000)}_{random.randint(10000000, 99999999)}",
        "region": f"CN-{REGION_CODE_MAP[_pick(REGIONS)]}",
        "source": _pick(SOURCES),
        "source_strategy": _pick(SOURCE_STRATEGIES),
        "source_rank": random.randint(1, 20),
        "extra": {
            "network": _pick(["wifi", "wifi", "wifi", "4g", "5g"]),
            "quality": _pick(["high", "high", "standard", "standard", "low"]),
        },
    }


def generate_music_metadata(content_id: str) -> dict:
    """FR-01 / §5.2 — content_metadata 消息 (音乐)"""
    tags = _pick_n(MUSIC_TAGS, random.randint(2, 5))
    return {
        "content_id": content_id,
        "content_type": "music",
        "title": _pick(MUSIC_TITLES),
        "artist_or_author": _pick(ARTISTS),
        "album": _pick(ALBUMS),
        "style_or_category": _pick(MUSIC_GENRES),
        "tags": tags,
        "duration": round(random.uniform(120.0, 360.0), 1),
        "language": _pick(LANGUAGES),
        "bpm": round(random.uniform(60.0, 180.0), 1),
        "release_date": f"{random.randint(2000, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "action": "create",
    }


def generate_video_metadata(content_id: str) -> dict:
    """FR-01 / §5.2 — content_metadata 消息 (视频)"""
    tags = _pick_n(MUSIC_TAGS, random.randint(2, 5))
    return {
        "content_id": content_id,
        "content_type": "video",
        "title": _pick(VIDEO_TITLES),
        "artist_or_author": _pick(ARTISTS[:20]),  # 视频作者
        "style_or_category": _pick(VIDEO_CATEGORIES),
        "tags": tags,
        "duration": round(random.uniform(30.0, 600.0), 1),
        "language": _pick(LANGUAGES),
        "quality": _pick(VIDEO_QUALITIES),
        "release_date": f"{random.randint(2018, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "action": "create",
    }


def generate_user_register(index: int) -> dict:
    """FR-01 / §5.2 — user_register 消息"""
    user_id = USER_IDS[index]
    surname = _pick(SURNAMES)
    given = _pick(GIVEN_NAMES)
    username = f"{surname}{given}{random.randint(1, 9999)}"
    device = _pick(DEVICES)
    register_time = datetime.utcnow() - timedelta(
        seconds=random.randint(0, 86400 * 7))  # 过去 7 天（注册时间可以分散一些）
    interest_tags = _pick_n(MUSIC_TAGS + VIDEO_CATEGORIES, random.randint(2, 5))

    return {
        "user_id": user_id,
        "username": username,
        "register_time": register_time.strftime("%Y-%m-%dT%H:%M:%S.") +
                         f"{register_time.microsecond // 1000:03d}Z",
        "device_type": device,
        "os_version": _pick(OS_VERSIONS[device]),
        "register_channel": _pick(CHANNELS),
        "interest_tags": interest_tags,
        "region": _pick(REGIONS),
        "age_group": _pick(AGE_GROUPS),
        "gender": _pick(GENDERS),
    }


# ============================================================================
# 文件生成
# ============================================================================

def write_jsonl(filename: str, generator, count: int, desc: str):
    """将生成器产生的记录逐行写入 JSONL 文件"""
    filepath = DATA_DIR / filename
    print(f"[生成] {desc} → {filepath}  ({count} 条)...")
    with open(filepath, "w", encoding="utf-8") as f:
        for i in range(count):
            record = generator(i)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            if (i + 1) % 2500 == 0:
                print(f"  ... {i + 1}/{count}")
    file_size = filepath.stat().st_size
    print(f"[完成] {filename}: {count} 条, {file_size:,} bytes")


def generate_user_behavior_file():
    write_jsonl("user_behavior.json", generate_user_behavior,
                RECORDS_PER_TOPIC, "user_behavior — 用户行为日志")


def generate_content_metadata_file():
    """生成 10,000 条内容元数据 (音乐 6000 + 视频 4000，保持 6:4 比例)"""
    filepath = DATA_DIR / "content_metadata.json"
    music_n = 6000
    video_n = 4000
    print(f"[生成] content_metadata — 内容元数据 (音乐{music_n}+视频{video_n}={music_n+video_n}) → {filepath}")

    with open(filepath, "w", encoding="utf-8") as f:
        # 音乐元数据
        for i in range(music_n):
            cid = MUSIC_IDS[i % len(MUSIC_IDS)]
            rec = generate_music_metadata(cid)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if (i + 1) % 2500 == 0:
                print(f"  [音乐] {i + 1}/{music_n}")

        # 视频元数据
        for i in range(video_n):
            cid = VIDEO_IDS[i % len(VIDEO_IDS)]
            rec = generate_video_metadata(cid)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if (i + 1) % 2000 == 0:
                print(f"  [视频] {i + 1}/{video_n}")

    file_size = filepath.stat().st_size
    print(f"[完成] content_metadata.json: {music_n + video_n} 条, {file_size:,} bytes")


def generate_user_register_file():
    write_jsonl("user_register.json", generate_user_register,
                RECORDS_PER_TOPIC, "user_register — 用户注册事件")


# ============================================================================
# 主入口
# ============================================================================

TOPIC_GENERATORS = {
    "user_behavior": generate_user_behavior_file,
    "content_metadata": generate_content_metadata_file,
    "user_register": generate_user_register_file,
}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 持续生成模式: python generate_data.py --continuous [--rate 5]
    if "--continuous" in sys.argv or "-c" in sys.argv:
        rate_idx = None
        if "--rate" in sys.argv:
            rate_idx = sys.argv.index("--rate")
        elif "-r" in sys.argv:
            rate_idx = sys.argv.index("-r")
        rate_per_sec = int(sys.argv[rate_idx + 1]) if rate_idx and rate_idx + 1 < len(sys.argv) else 3

        output_dir = os.environ.get("FLUME_OUTPUT_DIR", "/opt/data-generator/output")
        os.makedirs(output_dir, exist_ok=True)
        behavior_log = os.path.join(output_dir, "user_behavior.log")
        metadata_log = os.path.join(output_dir, "content_metadata.log")
        register_log = os.path.join(output_dir, "user_register.log")

        print(f"[持续生成] 速率: {rate_per_sec} 条/秒")
        print(f"[持续生成] 写入: {behavior_log}")
        print(f"[持续生成] 写入: {metadata_log}")
        print(f"[持续生成] 写入: {register_log}")
        print("[持续生成] Ctrl+C 停止")

        user_idx = 0
        music_idx = 0
        video_idx = 0
        try:
            while True:
                t_start = time.time()
                for _ in range(rate_per_sec):
                    # 用户行为 (主流量)
                    user_idx += 1
                    event = generate_user_behavior(user_idx)
                    # 使用当前时间覆盖 event_time
                    now = datetime.utcnow()
                    event["event_time"] = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
                    event["session_id"] = f"sess_{int(time.time() * 1000)}_{random.randint(10000000, 99999999)}"
                    with open(behavior_log, "a", encoding="utf-8") as f:
                        f.write(json.dumps(event, ensure_ascii=False) + "\n")

                    # 用户注册 (偶尔产生)
                    if random.random() < 0.15:
                        user_idx += 1
                        reg = generate_user_register(user_idx)
                        now2 = datetime.utcnow()
                        reg["register_time"] = now2.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now2.microsecond // 1000:03d}Z"
                        with open(register_log, "a", encoding="utf-8") as f:
                            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

                    # 内容元数据 (偶尔有新内容)
                    if random.random() < 0.05:
                        music_idx += 1
                        cid = MUSIC_IDS[music_idx % len(MUSIC_IDS)]
                        meta = generate_music_metadata(cid) if random.random() < 0.6 else generate_video_metadata(VIDEO_IDS[video_idx % len(VIDEO_IDS)])
                        if meta["content_type"] == "video":
                            video_idx += 1
                        meta["action"] = "create"
                        with open(metadata_log, "a", encoding="utf-8") as f:
                            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

                elapsed = time.time() - t_start
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
        except KeyboardInterrupt:
            print("\n[持续生成] 已停止")
        return

    # 支持 --topic 参数只生成指定 topic
    if "--topic" in sys.argv:
        idx = sys.argv.index("--topic")
        topic = sys.argv[idx + 1]
        if topic not in TOPIC_GENERATORS:
            print(f"未知 topic: {topic}，可选: {list(TOPIC_GENERATORS.keys())}")
            sys.exit(1)
        TOPIC_GENERATORS[topic]()
    else:
        for gen_func in TOPIC_GENERATORS.values():
            gen_func()
            print()

    print("=" * 60)
    print("全部数据文件生成完毕!")
    print(f"输出目录: {DATA_DIR}")
    for f in sorted(DATA_DIR.glob("*.json")):
        line_count = sum(1 for _ in open(f, encoding="utf-8"))
        print(f"  {f.name}: {line_count} 行")


if __name__ == "__main__":
    main()
