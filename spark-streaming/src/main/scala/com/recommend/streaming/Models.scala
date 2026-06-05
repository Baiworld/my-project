package com.recommend.streaming

/**
 * 流式处理数据模型 — 定义所有实时计算 Job 的输入输出数据结构
 *
 * 输入模型: Kafka 消费解析后的数据（UserBehaviorEvent / ContentMetaEvent / UserRegisterEvent）
 * 输出模型: 聚合结果后写入 MySQL rt_* 表（UserProfile / ContentHot / ClusterResult）
 */

// ── 输入数据模型（从 Kafka 消费并解析） ──

/** 用户行为事件 — 对应 Kafka Topic: user_behavior */
case class UserBehaviorEvent(
  eventId:        String,
  userId:         Long,
  contentId:      Long,
  contentType:    String,
  eventType:      String,       // play / like / favorite / comment / skip / complete / share
  eventTime:      Long,
  duration:       Double,
  progress:       Double,
  deviceType:     String,
  osVersion:      String,
  appVersion:     String,
  channel:        String,
  sessionId:      String,
  region:         String,
  source:         String,
  sourceStrategy: String,
  sourceRank:     Int,
  extra:          Map[String, String]
)

/** 内容元数据事件 — 对应 Kafka Topic: content_metadata */
case class ContentMetaEvent(
  contentId:        Long,
  contentType:      String,
  title:            String,
  artistOrAuthor:   String,
  styleOrCategory:  String,
  tags:             Seq[String],
  duration:         Double,
  language:         String,
  bpm:              Double,
  releaseDate:      String,
  action:           String        // create / update / delete
)

/** 用户注册事件 — 对应 Kafka Topic: user_register */
case class UserRegisterEvent(
  userId:          Long,
  registerTime:    Long,
  deviceType:      String,
  osVersion:       String,
  registerChannel: String,
  interestTags:    Seq[String],
  region:          String,
  ageGroup:        String,
  gender:          String
)

// ── 输出数据模型（写入 MySQL rt_* 表） ──

/** 实时用户画像 — 写入 rt_user_profile 表 */
case class UserProfile(
  userId:                 Long,
  windowStart:            Long,
  windowEnd:              Long,
  playCount:              Int,
  completionRate:         Double,
  likeRate:               Double,
  favoriteRate:           Double,
  skipRate:               Double,
  shareCount:             Int,
  commentCount:           Int,
  preferenceDistribution: String,   // JSON: 按内容类型的播放占比
  activeHours:            String,   // JSON: 按小时的活跃分布
  isColdStart:            Boolean,  // behaviorCount <= 50 为冷启动
  behaviorCount:          Int,
  contentTypeRatio:       String    // JSON: {"music": 0.6, "video": 0.4}
)

/** 实时内容热度 — 写入 rt_content_hot 表 */
case class ContentHot(
  contentId:       Long,
  contentType:     String,
  playCount:       Long,
  likeCount:       Long,
  favoriteCount:   Long,
  shareCount:      Long,
  completionRate:  Double,
  interactionRate: Double,          // (点赞+收藏+分享+评论) / 播放
  hotScore:        Double,          // 加权热度分
  windowStart:     Long,
  windowEnd:       Long
)

/** 冷启动聚类结果 — 写入 rt_coldstart_cluster 表 */
case class ClusterResult(
  userId:          Long,
  clusterId:       Int,
  clusterCenter:   String,          // JSON: 聚类中心向量
  clusterSize:     Int,
  deviceType:      String,
  registerChannel: String,
  interestTags:    String,          // JSON: 用户兴趣标签
  computeTime:     Long
)
