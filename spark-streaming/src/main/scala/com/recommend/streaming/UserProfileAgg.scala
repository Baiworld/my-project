package com.recommend.streaming

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import org.apache.spark.streaming.Seconds
import org.apache.spark.streaming.dstream.DStream

/**
 * FR-03 实时用户画像聚合 — 5分钟滑动窗口 (2.5分钟步长)
 *
 * 对用户行为事件流进行窗口聚合，计算:
 * - 播放次数 / 完播率 / 点赞率 / 收藏率 / 跳过率
 * - 偏好分布（按内容类型）
 * - 活跃时段分布（按小时）
 * - 内容类型比例（音乐 vs 视频）
 * - 冷启动标记（行为数 ≤ 50）
 */
object UserProfileAgg extends Serializable {

  private val windowDuration  = Seconds(300)  // 5 分钟窗口
  private val slideDuration   = Seconds(150)  // 2.5 分钟步长
  private val coldStartThreshold = 50          // 冷启动阈值

  private val mapper = new ObjectMapper().registerModule(DefaultScalaModule)

  /**
   * 对用户行为流进行滑动窗口聚合，输出用户画像
   *
   * @param stream 用户行为事件流
   * @return 用户画像 DStream
   */
  def aggregate(stream: DStream[UserBehaviorEvent]): DStream[UserProfile] = {
    stream
      .map(e => (e.userId, e))
      .window(windowDuration, slideDuration)
      .groupByKey()
      .map { case (userId, events) => buildProfile(userId, events.toSeq) }
  }

  /**
   * 根据用户事件序列构建用户画像对象
   *
   * 按事件类型分类统计，计算各项比率（以播放数为分母），生成偏好分布和活跃时段。
   */
  private def buildProfile(userId: Long, events: Seq[UserBehaviorEvent]): UserProfile = {
    // 按事件类型分类
    val playEvents     = events.filter(_.eventType == "play")
    val likeEvents     = events.filter(_.eventType == "like")
    val favoriteEvents = events.filter(_.eventType == "favorite")
    val skipEvents     = events.filter(_.eventType == "skip")
    val completeEvents = events.filter(_.eventType == "complete")
    val shareEvents    = events.filter(_.eventType == "share")
    val commentEvents  = events.filter(_.eventType == "comment")

    val playCount      = playEvents.size
    val likeCount      = likeEvents.size
    val favoriteCount  = favoriteEvents.size
    val skipCount      = skipEvents.size
    val completeCount  = completeEvents.size
    val shareCount     = shareEvents.size
    val commentCount   = commentEvents.size
    val totalBehaviors = events.size

    // 计算比率（以播放次数为分母）
    val completionRate = if (playCount > 0) completeCount.toDouble / playCount else 0.0
    val likeRate       = if (playCount > 0) likeCount.toDouble / playCount else 0.0
    val favoriteRate   = if (playCount > 0) favoriteCount.toDouble / playCount else 0.0
    val skipRate       = if (playCount > 0) skipCount.toDouble / playCount else 0.0

    val prefDist  = calcPreferenceDistribution(events)  // 偏好分布
    val activeHrs = calcActiveHours(events)              // 活跃时段
    val typeRatio = calcContentTypeRatio(events)         // 内容类型比例

    val epoch = System.currentTimeMillis()
    val windowStart = if (events.nonEmpty) events.map(_.eventTime).min else epoch - 300000L
    val windowEnd   = if (events.nonEmpty) events.map(_.eventTime).max else epoch

    UserProfile(
      userId                 = userId,
      windowStart            = windowStart,
      windowEnd              = windowEnd,
      playCount              = playCount,
      completionRate         = round4(completionRate),
      likeRate               = round4(likeRate),
      favoriteRate           = round4(favoriteRate),
      skipRate               = round4(skipRate),
      shareCount             = shareCount,
      commentCount           = commentCount,
      preferenceDistribution = mapper.writeValueAsString(prefDist),
      activeHours            = mapper.writeValueAsString(activeHrs),
      isColdStart            = totalBehaviors <= coldStartThreshold,
      behaviorCount          = totalBehaviors,
      contentTypeRatio       = mapper.writeValueAsString(typeRatio)
    )
  }

  /** 计算用户的偏好分布 — 各内容类型的播放占比 */
  private def calcPreferenceDistribution(events: Seq[UserBehaviorEvent]): Map[String, Double] = {
    val playEvents = events.filter(_.eventType == "play")
    if (playEvents.isEmpty) return Map.empty
    val grouped = playEvents.groupBy(e => s"${e.contentType}")
    val total = playEvents.size.toDouble
    grouped.map { case (k, v) => k -> round4(v.size / total) }
  }

  /** 计算用户的活跃时段分布 — 各小时的事件数量 */
  private def calcActiveHours(events: Seq[UserBehaviorEvent]): Map[Int, Int] = {
    events
      .map(e => java.time.Instant.ofEpochMilli(e.eventTime).atZone(java.time.ZoneId.of("UTC")).getHour)
      .groupBy(identity)
      .map { case (h, list) => h -> list.size }
  }

  /**
   * 计算内容类型偏好比（音乐 vs 视频）
   *
   * 没有播放事件时返回默认比例：音乐 0.6 : 视频 0.4
   */
  private def calcContentTypeRatio(events: Seq[UserBehaviorEvent]): Map[String, Double] = {
    val playEvents = events.filter(e => e.eventType == "play" && (e.contentType == "music" || e.contentType == "video"))
    if (playEvents.isEmpty) return Map("music" -> 0.6, "video" -> 0.4)
    val musicCount = playEvents.count(_.contentType == "music")
    val total = playEvents.size.toDouble
    Map(
      "music" -> round4(musicCount / total),
      "video" -> round4((playEvents.size - musicCount) / total)
    )
  }

  /** 保留 4 位小数 */
  private def round4(d: Double): Double = Math.round(d * 10000.0) / 10000.0

  def windowDurationMs: Long = windowDuration.milliseconds
  def slideDurationMs: Long  = slideDuration.milliseconds
}
