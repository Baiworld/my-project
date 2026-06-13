package com.recommend.offline

/**
 * 离线分析数据模型 — 定义所有离线 Job 的输入输出数据结构
 *
 * 对应 MySQL 表: offline_user_portrait / offline_recommendations / offline_metrics
 */

/** 实时用户画像行 — 对应 rt_user_profile 表，由 Spark Streaming 写入，离线 Job 读取 */
case class UserProfileRow(
  user_id: Long, play_count: Int, completion_rate: Double, like_rate: Double,
  favorite_rate: Double, skip_rate: Double, share_count: Int,
  comment_count: Int, preference_distribution: String,
  active_hours: String, is_cold_start: Int, behavior_count: Int,
  content_type_ratio: String, window_start: java.sql.Timestamp,
  window_end: java.sql.Timestamp
)

/** 用户全量画像 — 对应 offline_user_portrait 表，FR-06 离线构建 */
case class UserPortrait(
  user_id: Long, long_term_tags: String, preference_vector: String,
  lifecycle_stage: String, total_behaviors: Int,
  avg_session_duration: Double, active_days_last_30: Int,
  last_active_time: java.sql.Timestamp, favorite_content_type: String,
  cluster_id: Option[Int], tag_version: String, compute_time: java.sql.Timestamp
)

/** 内容特征 — 用于相似度计算和推荐特征工程 */
case class ContentFeature(
  content_id: Long, content_type: String, style_or_category: String,
  tags: Seq[String], duration: Double, language: String, bpm: Double
)

/**
 * 推荐结果 — 对应 offline_recommendations 表，FR-08 混合推荐引擎输出
 *
 * @param strategy 推荐策略: coldstart / transition / established
 * @param reason   推荐原因: cluster_hot / als_cf / hot_score
 * @param batch_id 批次标识，格式: batch_yyyyMMddHHmm
 */
case class Recommendation(
  user_id: Long, content_id: Long, content_type: String,
  rank: Int, score: Double, strategy: String, reason: String,
  batch_id: String, compute_time: java.sql.Timestamp,
  expire_time: java.sql.Timestamp
)

/**
 * 每日指标 — 对应 offline_metrics 表，FR-09 效果评估结果
 *
 * 按 user_group（all / coldstart / existing）和 content_type 分组记录
 */
case class DailyMetric(
  metric_date: java.sql.Date, user_group: String, content_type: String,
  ctr: Option[Double], cvr: Option[Double],
  avg_watch_duration: Option[Double], avg_interactions: Option[Double],
  coverage: Option[Double], diversity: Option[Double],
  coldstart_conversion: Option[Double],
  total_impressions: Long, total_clicks: Long, total_users: Int,
  compute_time: java.sql.Timestamp
)
