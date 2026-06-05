package com.recommend.producer

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.node.ObjectNode
import com.typesafe.config.ConfigFactory

import scala.util.Random
import scala.collection.mutable

/**
 * 模拟数据生成器 — 提供用户行为、内容元数据、用户注册的 Mock JSON 数据
 *
 * 所有数据通过 Jackson ObjectMapper 生成 JSON 字符串。
 * 用户和内容的选取采用幂律分布（高斯分布压缩到索引范围内），
 * 使编号较小的用户/内容出现频率更高，模拟真实场景中的马太效应。
 * 音乐与视频的内容比例为 6:4，与冷启动默认比例一致。
 */
object MockDataGenerator {

  private val mapper = new ObjectMapper()
  private val rng    = new Random()
  private val config = ConfigFactory.load()

  // ── 数据池规模 ──
  private val userCount  = config.getInt("producer.users.count")    // 用户总数
  private val musicCount = config.getInt("producer.contents.music.count")  // 音乐内容总数
  private val videoCount = config.getInt("producer.contents.video.count")  // 视频内容总数

  // ── ID 池 ──
  val userIds: Array[String]  = (1 to userCount).map(i => f"U$i%05d").toArray
  val musicIds: Array[String] = (1 to musicCount).map(i => f"M$i%05d").toArray
  val videoIds: Array[String] = (1 to videoCount).map(i => f"V$i%05d").toArray

  // ── 会话追踪（每个用户维持一个会话 ID，5% 概率切换） ──
  private val userSessions = mutable.Map.empty[String, String]

  // ======================== 音乐内容池 ========================

  private val musicTitles = Array(
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
    "成都", "南山南", "斑马斑马", "理想三旬", "春风十里"
  )

  private val artists = Array(
    "周杰伦", "林俊杰", "陈奕迅", "薛之谦", "邓紫棋", "李荣浩", "许嵩",
    "Taylor Swift", "Ed Sheeran", "The Beatles", "Queen", "Coldplay", "Adele",
    "汪峰", "许巍", "朴树", "赵雷", "马頔", "宋冬野", "陈粒",
    "张杰", "华晨宇", "周深", "毛不易", "刘柏辛", "王以太",
    "Imagine Dragons", "Maroon 5", "Bruno Mars", "Billie Eilish", "Dua Lipa",
    "张国荣", "Beyond", "五月天", "苏打绿", "孙燕姿", "蔡依林", "张惠妹",
    "那英", "王菲", "刘若英", "莫文蔚", "梁静茹", "张韶涵"
  )

  private val albums = Array(
    "首发专辑", "精选集", "Live现场", "Remix版", "重置版", "周年纪念版",
    "录音室专辑", "EP", "单曲", "Demo合集", "不插电版", "交响乐版"
  )

  private val musicGenres = Array(
    "流行", "摇滚", "古典", "爵士", "电子", "民谣", "R&B", "嘻哈"
  )

  private val languages = Array("zh", "zh", "zh", "zh", "en", "en", "ja", "ko")

  private val qualities = Array("standard", "standard", "standard", "high", "high", "lossless")

  private val musicTags = Array(
    "治愈", "励志", "伤感", "甜蜜", "怀旧", "青春", "旅行", "深夜",
    "运动", "学习", "工作", "放松", "派对", "驾驶", "睡前", "起床",
    "经典", "新歌", "冷门", "热门", "华语", "欧美", "日语", "韩语",
    "钢琴", "吉他", "电子音", "中国风", "古风", "说唱", "轻音乐"
  )

  // ======================== 视频内容池 ========================

  private val videoTitles = Array(
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
    "纪录片：中国美食", "动画短片", "微电影", "广告创意"
  )

  private val videoCategories = Array(
    "音乐MV", "直播", "教程", "生活Vlog", "娱乐", "体育", "新闻", "影视"
  )

  private val videoQualities = Array("720p", "720p", "1080p", "1080p", "1080p", "4K")

  // ======================== 用户池 ========================

  private val surnames = Array(
    "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧"
  )

  private val givenNames = Array(
    "伟", "芳", "敏", "静", "丽", "强", "磊", "洋",
    "勇", "艳", "杰", "军", "涛", "明", "超", "霞",
    "平", "刚", "文", "华", "飞", "斌", "浩",
    "宇", "然", "博", "涵", "萱", "怡", "琳", "瑞", "阳",
    "子轩", "子涵", "梓涵", "一诺", "欣怡", "雨桐", "宇轩", "诗涵",
    "嘉懿", "煜城", "思琪", "若曦", "浩宇", "皓轩", "乐瑶"
  )

  private val regions = Array(
    "北京", "上海", "广州", "深圳", "杭州", "成都",
    "武汉", "南京", "西安", "重庆", "苏州", "天津",
    "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "大连"
  )

  private val channels   = Array("app", "app", "app", "web", "web", "wechat_mini", "referral")
  private val ageGroups  = Array("18-24", "18-24", "25-34", "25-34", "25-34", "35-44", "35-44", "45+")
  private val genders    = Array("male", "female", "female", "male", "unknown")
  private val devices    = Array("android", "android", "android", "ios", "ios", "ios", "web")
  private val sources    = Array("recommend", "recommend", "recommend", "search", "search", "hot_list", "related")

  // 事件类型概率: play 高频 (8/15), like (3/15), collect (2/15), skip (3/15), share (1/15)
  private val eventTypes = Array(
    "play", "play", "play", "play", "play", "play", "play", "play",
    "like", "like", "like",
    "collect", "collect",
    "skip", "skip", "skip",
    "share"
  )

  // ======================== 公开 API ========================

  /**
   * 生成一条随机的用户行为事件 JSON
   *
   * 音乐内容占比 60%，视频 40%。用户和内容按幂律分布选取，热门内容更频繁出现。
   * 音乐时长 120-360 秒，视频时长 30-630 秒。
   */
  def generateUserBehavior(): String = {
    val userId    = pickUser()
    val sessionId = getOrCreateSession(userId)
    val isMusic   = rng.nextDouble() < 0.6   // 60% 音乐, 40% 视频
    val contentId = pickContent(isMusic)
    val durationMs = if (isMusic) 120000 + rng.nextInt(240000) else 30000 + rng.nextInt(600000)

    val node = mapper.createObjectNode()
    node.put("user_id", userId)
    node.put("session_id", sessionId)
    node.put("event_type", pick(eventTypes))
    node.put("content_id", contentId)
    node.put("content_type", if (isMusic) "music" else "video")
    node.put("duration_ms", durationMs)
    node.put("timestamp", System.currentTimeMillis())
    node.put("device", pick(devices))
    node.put("source", pick(sources))
    mapper.writeValueAsString(node)
  }

  /**
   * 为指定内容 ID 生成音乐元数据 JSON
   *
   * 包含标题、艺人、专辑、流派、时长、发行年份、语言、音质和随机标签（2-5个）
   */
  def generateMusicMetadata(contentId: String): String = {
    val node = mapper.createObjectNode()
    node.put("content_id", contentId)
    node.put("content_type", "music")
    node.put("title", pick(musicTitles))
    node.put("artist", pick(artists))
    node.put("album", pick(albums))
    node.put("genre", pick(musicGenres))
    node.put("duration_ms", 120000 + rng.nextInt(240000))
    node.put("release_year", 2000 + rng.nextInt(25))
    node.put("language", pick(languages))
    node.put("quality", pick(qualities))
    val tagsArr = node.putArray("tags")
    pickN(musicTags, 2 + rng.nextInt(4)).foreach(tagsArr.add)
    mapper.writeValueAsString(node)
  }

  /**
   * 为指定内容 ID 生成视频元数据 JSON
   *
   * 包含标题、分类、时长、语言、画质和随机标签（2-5个）
   */
  def generateVideoMetadata(contentId: String): String = {
    val node = mapper.createObjectNode()
    node.put("content_id", contentId)
    node.put("content_type", "video")
    node.put("title", pick(videoTitles))
    node.put("category", pick(videoCategories))
    node.put("duration_ms", 30000 + rng.nextInt(600000))
    node.put("language", pick(languages))
    node.put("quality", pick(videoQualities))
    val tagsArr = node.putArray("tags")
    pickN(musicTags, 2 + rng.nextInt(4)).foreach(tagsArr.add)
    mapper.writeValueAsString(node)
  }

  /**
   * 为指定用户 ID 生成注册信息 JSON
   *
   * 包含用户名（姓氏+名字+随机数字）、注册时间（过去一年内随机）、
   * 渠道、年龄段、性别、地区
   */
  def generateUserRegister(userId: String): String = {
    val surname  = pick(surnames)
    val given    = pick(givenNames)
    val username = s"$surname$given${rng.nextInt(9999)}"

    val node = mapper.createObjectNode()
    node.put("user_id", userId)
    node.put("username", username)
    // 注册时间: 过去 365 天内的随机时刻
    node.put("register_time", System.currentTimeMillis() - rng.nextInt(365 * 24 * 3600) * 1000L)
    node.put("channel", pick(channels))
    node.put("age_group", pick(ageGroups))
    node.put("gender", pick(genders))
    node.put("region", pick(regions))
    mapper.writeValueAsString(node)
  }

  // ======================== 私有辅助方法 ========================

  /** 从数组中随机选取一个元素 */
  private def pick[T](arr: Array[T]): T = arr(rng.nextInt(arr.length))

  /** 从数组中随机选取不重复的 N 个元素 */
  private def pickN[T](arr: Array[T], n: Int): List[T] =
    rng.shuffle(arr.toList).take(n)

  /**
   * 幂律用户选取 — 使用高斯分布的绝对值映射到用户索引
   *
   * 编号越小的用户被选中的概率越高，模拟头部用户的高活跃度
   */
  private def pickUser(): String = {
    val idx = (math.abs(rng.nextGaussian()) * userCount * 0.25).toInt min (userCount - 1)
    userIds(idx)
  }

  /**
   * 幂律内容选取 — 使用高斯分布映射到内容索引
   *
   * 编号越小的内容被选中的概率越高，模拟热门内容的高曝光率
   */
  private def pickContent(isMusic: Boolean): String = {
    val pool  = if (isMusic) musicIds else videoIds
    val count = pool.length
    val idx   = (math.abs(rng.nextGaussian()) * count * 0.25).toInt min (count - 1)
    pool(idx)
  }

  /**
   * 获取或创建用户会话
   *
   * 每个用户维持一个会话 ID，有 5% 的概率切换为新会话，模拟用户退出重登
   */
  private def getOrCreateSession(userId: String): String = {
    userSessions.get(userId) match {
      case Some(sid) =>
        if (rng.nextDouble() < 0.05) {
          val newSid = s"sess_${System.currentTimeMillis()}_${rng.alphanumeric.take(8).mkString}"
          userSessions(userId) = newSid
          newSid
        } else sid
      case None =>
        val newSid = s"sess_${System.currentTimeMillis()}_${rng.alphanumeric.take(8).mkString}"
        userSessions(userId) = newSid
        newSid
    }
  }
}
