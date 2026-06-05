package com.recommend.offline

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.typesafe.config.ConfigFactory
import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import java.sql.Timestamp
import java.time.{LocalDateTime, ZoneId}

/**
 * FR-06 用户全量画像构建 — 每 6 小时运行
 *
 * 从 rt_user_profile 聚合用户行为数据，构建全量画像写入 offline_user_portrait。
 * 包含: 长期兴趣标签（Top-10）、128 维偏好向量、生命周期阶段分类（new/active/silent/churned）、
 * 冷启动聚类 ID 关联。
 */
object UserPortraitBuilder {

  private val mapper = new ObjectMapper().registerModule(DefaultScalaModule)

  /**
   * 构建用户全量画像
   *
   * 步骤: 读取实时画像 → 按 user_id 聚合所有窗口 → 关联冷启动聚类 →
   *       提取长期标签/偏好向量/生命周期 → 写入 offline_user_portrait
   */
  def build(spark: SparkSession): Unit = {
    import spark.implicits._

    val cfg     = ConfigFactory.load().getConfig("mysql")
    val jdbcUrl = cfg.getString("url") + "?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true"
    val dbProps = new java.util.Properties()
    dbProps.setProperty("user", cfg.getString("user"))
    dbProps.setProperty("password", cfg.getString("password"))
    dbProps.setProperty("driver", "com.mysql.cj.jdbc.Driver")

    // 读取实时用户画像
    val profileDF = spark.read.jdbc(jdbcUrl, "rt_user_profile", dbProps)
    val now = new Timestamp(System.currentTimeMillis())

    // 按 user_id 聚合所有窗口数据
    val aggDF = profileDF.groupBy("user_id").agg(
      org.apache.spark.sql.functions.max("behavior_count").as("total_behaviors"),
      org.apache.spark.sql.functions.max("window_end").as("last_active"),
      org.apache.spark.sql.functions.count(
        org.apache.spark.sql.functions.when(
          org.apache.spark.sql.functions.col("window_end").gt(
            new Timestamp(System.currentTimeMillis() - 30L * 24 * 3600 * 1000)
          ), 1
        )
      ).as("active_days"),
      org.apache.spark.sql.functions.first("is_cold_start").as("is_cold_start"),
      org.apache.spark.sql.functions.first("content_type_ratio").as("content_type_ratio"),
      org.apache.spark.sql.functions.first("preference_distribution").as("preference_distribution"),
      org.apache.spark.sql.functions.first("play_count").as("play_count"),
      org.apache.spark.sql.functions.first("completion_rate").as("completion_rate"),
      org.apache.spark.sql.functions.first("like_rate").as("like_rate"),
      org.apache.spark.sql.functions.first("favorite_rate").as("favorite_rate"),
      org.apache.spark.sql.functions.first("skip_rate").as("skip_rate")
    )

    // 读取冷启动聚类结果（表不存在时优雅降级）
    val clusterDF = try {
      spark.read.jdbc(jdbcUrl, "rt_coldstart_cluster", dbProps)
        .select("user_id", "cluster_id")
    } catch { case _: Exception => spark.emptyDataFrame }

    // 左外连接聚类信息
    val joinedDF = if (clusterDF.isEmpty) {
      aggDF.withColumn("cluster_id", org.apache.spark.sql.functions.lit(null))
    } else {
      aggDF.join(clusterDF, Seq("user_id"), "left_outer")
    }

    // 逐行构建画像对象
    val portraitDF = joinedDF.rdd.map { row =>
      val userId = longVal(row, "user_id")
      val totalBehaviors = intVal(row, "total_behaviors")
      val activeDays = intVal(row, "active_days")
      val lastActive = row.getAs[Timestamp]("last_active")
      val prefDist = Option(row.getAs[String]("preference_distribution")).getOrElse("{}")
      val typeRatio = Option(row.getAs[String]("content_type_ratio")).getOrElse("{}")
      val clusterId = try { Some(intVal(row, "cluster_id")) } catch { case _: Exception => None }
      val playCount = intVal(row, "play_count")
      val completionRate = doubleVal(row, "completion_rate")
      val likeRate = doubleVal(row, "like_rate")
      val favoriteRate = doubleVal(row, "favorite_rate")
      val skipRate = doubleVal(row, "skip_rate")

      // 生命周期分类: new(≤50 行为) / active(≥20 天活跃) / silent(5-19 天) / churned(<5 天)
      val lifecycle = classifyLifecycle(totalBehaviors, activeDays)

      // 长期标签: 从偏好分布 JSON 中提取 Top-10 高频标签
      val longTermTags = extractLongTermTags(prefDist)

      // 偏好内容类型: 音乐 vs 视频
      val favType = extractFavoriteType(typeRatio)

      // 128 维偏好向量: [playCount_norm, completionRate, likeRate, favoriteRate, skipRate, totalBehaviors_norm, 零填充]
      val prefVec = buildPreferenceVector(playCount, completionRate, likeRate, favoriteRate, skipRate, totalBehaviors)

      UserPortrait(
        user_id = userId,
        long_term_tags = longTermTags,
        preference_vector = mapper.writeValueAsString(prefVec),
        lifecycle_stage = lifecycle,
        total_behaviors = totalBehaviors,
        avg_session_duration = 0.0,   // 暂未采集，预留字段
        active_days_last_30 = activeDays,
        last_active_time = lastActive,
        favorite_content_type = favType,
        cluster_id = clusterId,
        tag_version = "v1.0",
        compute_time = now
      )
    }.toDF()

    // 写入离线用户画像表
    portraitDF.write
      .mode(SaveMode.Overwrite)
      .jdbc(jdbcUrl, "offline_user_portrait", dbProps)

    println(s"[用户画像] 写入 ${portraitDF.count()} 条用户全量画像")
  }

  /**
   * 生命周期分类
   *
   * new:    总行为数 ≤ 50（冷启动用户）
   * active: 近 30 天活跃 ≥ 20 天
   * silent: 近 30 天活跃 5-19 天
   * churned: 近 30 天活跃 < 5 天
   */
  def classifyLifecycle(total: Int, activeDays: Int): String = {
    if (total <= 50) "new"
    else if (activeDays >= 20) "active"
    else if (activeDays >= 5) "silent"
    else "churned"
  }

  /** 从偏好分布 JSON 中提取 Top-10 长期标签（简化版 TF-IDF） */
  def extractLongTermTags(prefDistJson: String): String = {
    try {
      val dist = mapper.readTree(prefDistJson)
      import scala.collection.JavaConverters._
      val sorted = dist.fields().asScala.toSeq
        .map(e => e.getKey -> e.getValue.asDouble())
        .sortBy(-_._2).take(10)
      mapper.writeValueAsString(sorted.map(_._1))
    } catch { case _: Exception => "[]" }
  }

  /** 从内容类型比例 JSON 中提取偏好类型（音乐 vs 视频） */
  def extractFavoriteType(typeRatioJson: String): String = {
    try {
      val ratio = mapper.readTree(typeRatioJson)
      val music = Option(ratio.get("music")).map(_.asDouble()).getOrElse(0.0)
      val video = Option(ratio.get("video")).map(_.asDouble()).getOrElse(0.0)
      if (music >= video) "music" else "video"
    } catch { case _: Exception => "mixed" }
  }

  /**
   * 构建 128 维偏好向量
   *
   * 前 6 维: [归一化播放量, 完播率, 点赞率, 收藏率, 跳过率, 归一化总行为数]
   * 后 122 维: 零填充（为后续 SVD/PCA 降维预留空间）
   */
  def buildPreferenceVector(playCount: Int, completionRate: Double, likeRate: Double,
                             favoriteRate: Double, skipRate: Double, total: Int): Array[Double] = {
    val base = Array(
      math.min(playCount / 100.0, 1.0), completionRate, likeRate, favoriteRate, skipRate,
      math.min(total / 200.0, 1.0)
    )
    base ++ Array.fill(128 - base.length)(0.0)
  }

  // ── JDBC 类型安全转换 ──

  private def longVal(row: org.apache.spark.sql.Row, col: String): Long =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).longValue()).getOrElse(0L)

  private def intVal(row: org.apache.spark.sql.Row, col: String): Int =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).intValue()).getOrElse(0)

  private def doubleVal(row: org.apache.spark.sql.Row, col: String): Double =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).doubleValue()).getOrElse(0.0)
}
