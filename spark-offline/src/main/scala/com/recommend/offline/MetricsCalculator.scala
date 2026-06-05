package com.recommend.offline

import com.typesafe.config.ConfigFactory
import org.apache.spark.sql.{SaveMode, SparkSession}
import org.apache.spark.sql.functions._
import java.sql.Timestamp
import java.time.LocalDate

/**
 * FR-09 推荐效果指标计算 — 基于真实数据交叉计算
 *
 * 从 offline_recommendations / rt_user_profile / rt_content_hot 三张表交叉计算:
 * - CTR（点击率）: 用户实际播放量 / 推荐曝光量
 * - CVR（完播率）: 已推荐用户的平均完播率
 * - 人均播放时长: （总播放量 / 用户数）* 完播率 * 180s
 * - 人均互动次数: 点赞率 + 收藏率 + 分享数均值
 * - 覆盖率: 推荐覆盖内容数 / 总内容数
 * - 多样性: 1 - 各用户推荐列表内容类型集中度均值
 * - 冷启动转化率: 推荐后有行为记录的冷用户占比
 *
 * 按 user_group 分组输出: all（全体）/ coldstart（冷启动）/ existing（存量）
 */
object MetricsCalculator {

  /**
   * 计算每日指标
   *
   * 先删除当日已有数据（支持重复运行），再从推荐、用户行为、内容三张表
   * 交叉计算各项真实指标，分别统计全体/冷启动/存量三组。
   */
  def calculate(spark: SparkSession): Unit = {
    import spark.implicits._

    val cfg     = ConfigFactory.load().getConfig("mysql")
    val jdbcUrl = cfg.getString("url") + "?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true"
    val dbProps = new java.util.Properties()
    dbProps.setProperty("user", cfg.getString("user"))
    dbProps.setProperty("password", cfg.getString("password"))
    dbProps.setProperty("driver", "com.mysql.cj.jdbc.Driver")

    val today = new java.sql.Date(System.currentTimeMillis())
    val now   = new Timestamp(System.currentTimeMillis())

    // 删除当日已存在的指标（避免唯一键冲突）
    try {
      val conn = java.sql.DriverManager.getConnection(jdbcUrl, dbProps)
      conn.createStatement().executeUpdate(
        s"DELETE FROM offline_metrics WHERE metric_date = '${today.toString}'")
      conn.close()
    } catch { case _: Exception => }

    // 1. 读取推荐数据
    val recDF = try {
      spark.read.jdbc(jdbcUrl, "offline_recommendations", dbProps)
    } catch { case _: Exception => spark.emptyDataFrame }

    if (recDF.isEmpty) {
      println("[指标计算] 无推荐数据，写入占位指标")
      val placeholder = Seq(
        DailyMetric(today, "all", "all", Some(0.0), Some(0.0), Some(0.0),
          Some(0.0), Some(0.0), Some(0.0), Some(0.0), 0L, 0L, 0, now)
      ).toDF()
      placeholder.write.mode(SaveMode.Append).jdbc(jdbcUrl, "offline_metrics", dbProps)
      return
    }

    // 2. 读取用户行为数据
    val profileDF = try {
      spark.read.jdbc(jdbcUrl, "rt_user_profile", dbProps)
    } catch { case _: Exception => spark.emptyDataFrame }

    // 3. 读取内容数据
    val contentDF = try {
      spark.read.jdbc(jdbcUrl, "rt_content_hot", dbProps)
    } catch { case _: Exception => spark.emptyDataFrame }

    // ── 公共指标计算 ──
    val totalRecs       = recDF.count()
    val totalUsers      = recDF.select("user_id").distinct().count().toInt
    val distinctContent = recDF.select("content_id").distinct().count()
    val totalContent    = if (contentDF.isEmpty) 1L else contentDF.select("content_id").distinct().count()
    val coverageVal     = if (totalContent > 0) distinctContent.toDouble / totalContent else 0.0

    // 推荐用户与实际行为用户取交集
    val recUsers = recDF.select("user_id").distinct()
    val matchedProfiles = if (profileDF.isEmpty) spark.emptyDataFrame
      else profileDF.join(recUsers, Seq("user_id"), "inner")

    val totalPlays    = if (matchedProfiles.isEmpty) 0L
      else safeLongVal(matchedProfiles.agg(sum(coalesce(col("play_count"), lit(0)))).head(), 0)
    val avgCompletion = if (matchedProfiles.isEmpty) 0.0
      else safeDoubleVal(matchedProfiles.agg(avg(coalesce(col("completion_rate"), lit(0.0)))).head(), 0)
    val avgLikeRate   = if (matchedProfiles.isEmpty) 0.0
      else safeDoubleVal(matchedProfiles.agg(avg(coalesce(col("like_rate"), lit(0.0)))).head(), 0)
    val avgFavRate    = if (matchedProfiles.isEmpty) 0.0
      else safeDoubleVal(matchedProfiles.agg(avg(coalesce(col("favorite_rate"), lit(0.0)))).head(), 0)
    val avgShare      = if (matchedProfiles.isEmpty) 0.0
      else safeDoubleVal(matchedProfiles.agg(avg(coalesce(col("share_count"), lit(0)))).head(), 0)

    val ctr  = calcCTR(totalRecs, totalPlays)
    val cvr  = avgCompletion
    val avgWatch = if (totalUsers > 0) (totalPlays.toDouble / totalUsers) * avgCompletion * 180.0 else 0.0
    val avgInteract = avgLikeRate + avgFavRate + avgShare

    // 多样性: 按用户计算推荐列表中内容类型的集中度
    val diversityVal = computeDiversity(recDF, spark)

    // ── 按用户分组计算 ──
    val strategyGroups = Seq(
      ("all",        recDF),
      ("coldstart",  recDF.filter(col("strategy") === "coldstart")),
      ("existing",   recDF.filter(col("strategy") === "established"))
    )

    val metricsRows = strategyGroups.flatMap { case (group, df) =>
      if (df.isEmpty) {
        None
      } else {
        val gRecs   = df.count()
        val gUsers  = df.select("user_id").distinct().count().toInt
        val gPlays  = computeGroupPlays(df, profileDF, spark)
        val gCompl  = computeGroupCompletion(df, profileDF, spark)
        val gLike   = computeGroupAvg(df, profileDF, spark, "like_rate")
        val gFav    = computeGroupAvg(df, profileDF, spark, "favorite_rate")
        val gShare  = computeGroupAvg(df, profileDF, spark, "share_count")
        val gDistinct = df.select("content_id").distinct().count()

        val gCtr = calcCTR(gRecs, gPlays)
        val gCvr = gCompl
        val gWatch = if (gUsers > 0) (gPlays.toDouble / gUsers) * gCompl * 180.0 else 0.0
        val gInteract = gLike + gFav + gShare
        val gCoverage = if (totalContent > 0) gDistinct.toDouble / totalContent else 0.0
        val gDiversity = if (gUsers > 1) computeDiversity(df, spark) else diversityVal

        val coldConv = if (group == "coldstart" && gUsers > 0) {
          computeColdStartConversion(df, profileDF, spark)
        } else None

        Some(DailyMetric(today, group, "all",
          Some(round4(gCtr)), Some(round4(gCvr)), Some(round4(gWatch)),
          Some(round4(gInteract)), Some(round4(gCoverage)), Some(round4(gDiversity)),
          coldConv.map(round4), gRecs, gPlays, gUsers, now))
      }
    }

    metricsRows.toDF().write.mode(SaveMode.Append).jdbc(jdbcUrl, "offline_metrics", dbProps)

    println(s"[指标计算] 写入 ${metricsRows.size} 组推荐效果指标")
  }

  // ── 分组辅助计算 ──

  /** 计算该推荐分组用户的实际播放总量 */
  private def computeGroupPlays(recDF: org.apache.spark.sql.DataFrame,
    profileDF: org.apache.spark.sql.DataFrame, spark: SparkSession): Long = {
    import spark.implicits._
    if (profileDF.isEmpty) return 0L
    val users = recDF.select("user_id").distinct()
    val joined = profileDF.join(users, Seq("user_id"), "inner")
    if (joined.isEmpty) 0L
    else safeLongVal(joined.agg(sum(coalesce(col("play_count"), lit(0)))).head(), 0)
  }

  /** 计算该推荐分组用户的平均完播率 */
  private def computeGroupCompletion(recDF: org.apache.spark.sql.DataFrame,
    profileDF: org.apache.spark.sql.DataFrame, spark: SparkSession): Double = {
    computeGroupAvg(recDF, profileDF, spark, "completion_rate")
  }

  /** 计算该推荐分组用户指定列的均值 */
  private def computeGroupAvg(recDF: org.apache.spark.sql.DataFrame,
    profileDF: org.apache.spark.sql.DataFrame, spark: SparkSession, colName: String): Double = {
    import spark.implicits._
    if (profileDF.isEmpty) return 0.0
    val users = recDF.select("user_id").distinct()
    val joined = profileDF.join(users, Seq("user_id"), "inner")
    if (joined.isEmpty) 0.0
    else safeDoubleVal(joined.agg(avg(coalesce(col(colName), lit(0.0)))).head(), 0)
  }

  /**
   * 冷启动转化率 — 推荐后有行为记录的冷用户占比
   *
   * 冷启动推荐用户中，behavior_count > 0 的比例即为"被激活"的冷用户。
   */
  private def computeColdStartConversion(recDF: org.apache.spark.sql.DataFrame,
    profileDF: org.apache.spark.sql.DataFrame, spark: SparkSession): Option[Double] = {
    import spark.implicits._
    if (profileDF.isEmpty) return None
    val coldUsers = recDF.select("user_id").distinct()
    val totalCold = coldUsers.count()
    if (totalCold == 0) return None

    val active = profileDF.join(coldUsers, Seq("user_id"), "inner")
      .filter(coalesce(col("behavior_count"), lit(0)) > 0)
      .count()

    Some(active.toDouble / totalCold)
  }

  /**
   * 推荐列表多样性 — 1 - 各用户推荐内容类型最大占比的均值
   *
   * 先计算每个用户推荐列表中内容类型的集中度（max_type_count / total_count），
   * 再取所有用户的均值，最后用 1 减去得到多样性指标。
   * 所有内容为同一类型时多样性为 0，类型均匀分布时多样性趋近 0.5。
   */
  private def computeDiversity(recDF: org.apache.spark.sql.DataFrame,
    spark: SparkSession): Double = {
    import spark.implicits._

    val diversityRow = recDF
      .groupBy("user_id", "content_type")
      .agg(count(lit(1)).as("cnt"))
      .groupBy("user_id")
      .agg(
        sum("cnt").as("total"),
        max("cnt").as("max_cnt")
      )
      .select(
        when(col("total") > 0, lit(1.0) - (col("max_cnt").cast("double") / col("total")))
          .otherwise(lit(0.0)).as("div_score")
      )
      .agg(avg("div_score")).head()
    val div = safeDoubleVal(diversityRow, 0)
    if (div.isNaN || div.isInfinite) 0.0 else div
  }

  // ── 指标公式 ──

  /** CTR 点击率 = 点击数 / 曝光数 */
  def calcCTR(impressions: Long, clicks: Long): Double =
    if (impressions > 0) clicks.toDouble / impressions else 0.0

  /** CVR 转化率 = 完成数 / 曝光数 */
  def calcCVR(impressions: Long, completions: Long): Double =
    if (impressions > 0) completions.toDouble / impressions else 0.0

  /** 冷启动转化率 = 被激活冷用户数 / 总冷用户数 */
  def calcColdStartConversion(newUsers: Long, converted: Long): Double =
    if (newUsers > 0) converted.toDouble / newUsers else 0.0

  /** 保留 4 位小数 */
  private def round4(d: Double): Double = Math.round(d * 10000.0) / 10000.0

  /** 安全 Long 值提取（处理 JDBC BigDecimal 类型） */
  private def safeLongVal(row: org.apache.spark.sql.Row, idx: Int): Long =
    Option(row.get(idx)).map(v => new java.math.BigDecimal(v.toString).longValue()).getOrElse(0L)

  /** 安全 Double 值提取（处理 JDBC BigDecimal 类型） */
  private def safeDoubleVal(row: org.apache.spark.sql.Row, idx: Int): Double =
    Option(row.get(idx)).map(v => new java.math.BigDecimal(v.toString).doubleValue()).getOrElse(0.0)
}
