package com.recommend.streaming

import org.apache.spark.streaming.Seconds
import org.apache.spark.streaming.dstream.DStream

/**
 * FR-04 内容实时热度统计 — 1分钟滚动窗口
 *
 * 热度评分公式:
 *   hotScore = wPlay * ln(1 + 播放数) + wCompletion * 完播率 * 100 + wInteraction * 互动率 * 100
 *
 * 权重: wPlay = 1.0, wCompletion = 1.5, wInteraction = 2.0
 * 互动率 = (点赞数 + 收藏数 + 分享数 + 评论数) / 播放数
 */
object ContentHotStats extends Serializable {

  val weightPlay        = 1.0   // 播放量权重
  val weightCompletion  = 1.5   // 完播率权重
  val weightInteraction = 2.0   // 互动率权重（最高，体现互动的重要性）

  private val windowDuration = Seconds(60)  // 1 分钟滚动窗口

  /**
   * 对用户行为流进行滚动窗口热度计算
   *
   * @param stream 用户行为事件流
   * @return 内容热度 DStream
   */
  def compute(stream: DStream[UserBehaviorEvent]): DStream[ContentHot] = {
    stream
      .map(e => ((e.contentId, e.contentType), e))
      .window(windowDuration, windowDuration)
      .groupByKey()
      .map { case ((contentId, contentType), events) => buildHot(contentId, contentType, events.toSeq) }
  }

  /** 根据事件序列构建内容热度对象 */
  private def buildHot(contentId: Long, contentType: String, events: Seq[UserBehaviorEvent]): ContentHot = {
    val playCount     = events.count(_.eventType == "play").toLong
    val likeCount     = events.count(_.eventType == "like").toLong
    val favoriteCount = events.count(_.eventType == "favorite").toLong
    val shareCount    = events.count(_.eventType == "share").toLong
    val commentCount  = events.count(_.eventType == "comment").toLong
    val completeCount = events.count(_.eventType == "complete").toLong

    // 完播率 = 完成播放次数 / 总播放次数
    val completionRate  = if (playCount > 0) completeCount.toDouble / playCount else 0.0
    // 互动率 = (点赞+收藏+分享+评论) / 总播放次数
    val interactionRate = if (playCount > 0) (likeCount + favoriteCount + shareCount + commentCount).toDouble / playCount else 0.0

    val hotScore = calcHotScore(playCount, completionRate, interactionRate)

    val epoch = System.currentTimeMillis()
    ContentHot(
      contentId       = contentId,
      contentType     = contentType,
      playCount       = playCount,
      likeCount       = likeCount,
      favoriteCount   = favoriteCount,
      shareCount      = shareCount,
      completionRate  = round4(completionRate),
      interactionRate = round4(interactionRate),
      hotScore        = round4(hotScore),
      windowStart     = epoch - windowDuration.milliseconds,
      windowEnd       = epoch
    )
  }

  /**
   * 热度评分公式
   *
   * hotScore = wPlay * log1p(playCount) + wCompletion * completionRate * 100 + wInteraction * interactionRate * 100
   *
   * log1p 对播放量取对数，避免头部内容分数过大。完播率和互动率乘以 100 统一量纲。
   */
  def calcHotScore(playCount: Long, completionRate: Double, interactionRate: Double): Double = {
    weightPlay        * math.log1p(playCount) +
    weightCompletion  * completionRate * 100.0 +
    weightInteraction * interactionRate * 100.0
  }

  /** 保留 4 位小数 */
  private def round4(d: Double): Double = Math.round(d * 10000.0) / 10000.0
}
