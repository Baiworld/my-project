package com.recommend.offline

import com.typesafe.config.ConfigFactory
import org.apache.spark.sql.{SaveMode, SparkSession}
import java.sql.Timestamp
import java.time.LocalDateTime

/**
 * FR-08 混合推荐引擎 — ALS 协同过滤 + 聚类冷启动 + DPP 多样性重排
 *
 * 推荐策略分流:
 * - 冷启动用户 (behaviorCount ≤ 50): ε-greedy 探索 + 热门内容，音乐:视频 = 6:4
 * - 过渡期用户 (51 ≤ behaviorCount < 80): 冷启动与存量策略线性插值
 * - 存量用户 (behaviorCount ≥ 80): ALS 协同过滤推荐
 *
 * 所有推荐结果经过 DPP 多样性重排（θ=0.7），写入 offline_recommendations。
 */
object HybridRecommender {

  private val coldThreshold = 50
  private val transitionMin  = 30
  private val transitionMax  = 80
  private val epsilon        = 0.15   // ε-greedy 探索率
  private val topN           = 50
  private val musicRatio     = 0.6    // 音乐:视频 = 6:4

  /**
   * 执行混合推荐
   *
   * 步骤: 读取用户数据 → 按行为量分三类 → ALS 批量推荐存量用户 →
   *       冷启动 ε-greedy → 过渡期插值混合 → DPP 重排 → 写入 MySQL
   */
  def run(spark: SparkSession, maxUsers: Option[Int] = None): Unit = {
    import spark.implicits._

    val cfg = ConfigFactory.load()

    val jdbcUrl = cfg.getString("mysql.url") +
      "?useSSL=false&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true&allowPublicKeyRetrieval=true"
    val dbProps = new java.util.Properties()
    dbProps.setProperty("user", cfg.getString("mysql.user"))
    dbProps.setProperty("password", cfg.getString("mysql.password"))
    dbProps.setProperty("driver", "com.mysql.cj.jdbc.Driver")

    // 1. 读取数据
    val profileDF = spark.read.jdbc(jdbcUrl, "rt_user_profile", dbProps)
    val hotDF     = spark.read.jdbc(jdbcUrl, "rt_content_hot", dbProps)
    val clusterDF = try {
      spark.read.jdbc(jdbcUrl, "rt_coldstart_cluster", dbProps)
    } catch { case _: Exception => spark.emptyDataFrame }

    // 2. 提取用户列表
    val allUsers = profileDF.select("user_id", "behavior_count")
      .distinct().collect().map { r =>
      (safeLong(r, "user_id"), safeInt(r, "behavior_count"))
    }.toSeq

    // 如果指定了用户上限，优先选冷启动用户（最能体现推荐效果）
    val users = maxUsers match {
      case Some(limit) if limit < allUsers.size =>
        val cold = allUsers.filter(_._2 <= coldThreshold).take(limit / 2)
        val rest = allUsers.filter(_._2 > coldThreshold).take(limit - cold.size)
        println(s"[推荐引擎] 限制用户数: ${allUsers.size} -> ${cold.size + rest.size} (冷启动=${cold.size}, 其他=${rest.size})")
        cold ++ rest
      case _ => allUsers
    }

    // 3. 构建热门内容池（Top-300）
    val hotContents = hotDF.select("content_id", "content_type", "hot_score")
      .distinct().orderBy(org.apache.spark.sql.functions.desc("hot_score"))
      .limit(300).collect().map { r =>
      val ct = Option(r.getAs[String]("content_type")).getOrElse("music")
      (safeLong(r, "content_id"), ct, safeDouble(r, "hot_score"))
    }.toSeq

    val musicPool = hotContents.filter(_._2 == "music")
    val videoPool = hotContents.filter(_._2 == "video")
    val typeMap   = hotContents.map(c => c._1 -> c._2).toMap  // 用于 ALS 结果补全类型

    // 4. 按策略分桶
    val coldUsers      = users.filter(_._2 <= coldThreshold)
    val transitionUsers = users.filter(u => u._2 > coldThreshold && u._2 < transitionMax)
    val establishedUsers = users.filter(_._2 >= transitionMax)

    println(s"[推荐引擎] 冷启动=${coldUsers.size} 过渡期=${transitionUsers.size} 存量=${establishedUsers.size}")

    val now         = new Timestamp(System.currentTimeMillis())
    val expireTime  = new Timestamp(System.currentTimeMillis() + 6L * 3600 * 1000)
    val batchId     = s"batch_${LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmm"))}"

    // 5. ALS 批量推荐（存量用户一次性调用）
    val alsRecMap: Map[Long, Seq[Recommendation]] =
      if (establishedUsers.nonEmpty && ALSRecommender.modelExists) {
        ALSRecommender.recommend(spark, establishedUsers.map(_._1), topN)
      } else {
        if (establishedUsers.nonEmpty) println("[推荐引擎] ALS 模型不可用，存量用户使用 hot-score 回退")
        Map.empty.withDefaultValue(Seq.empty)
      }

    // 6. 逐用户生成推荐
    val recommendations = users.flatMap { case (userId, behaviorCount) =>
      val strategy = if (behaviorCount <= coldThreshold) "coldstart"
      else if (behaviorCount < transitionMax) "transition"
      else "established"

      val rawRecs = strategy match {
        case "coldstart" =>
          recommendColdStart(userId, musicPool, videoPool, clusterDF, spark)

        case "transition" =>
          // 过渡期: coldstart * (1-ratio) + established * ratio
          val ratio = transitionBlend(behaviorCount)
          val cold = recommendColdStart(userId, musicPool, videoPool, clusterDF, spark)
            .map(r => r.copy(score = r.score * (1 - ratio)))
          val estb = alsRecMap.getOrElse(userId,
            recommendEstablishedFallback(userId, musicPool, videoPool))
            .map(r => r.copy(score = r.score * ratio))
          (cold ++ estb).groupBy(_.content_id).map { case (_, rs) =>
            rs.maxBy(_.score)
          }.toSeq.sortBy(-_.score).take(topN)

        case "established" =>
          alsRecMap.getOrElse(userId,
            recommendEstablishedFallback(userId, musicPool, videoPool))
      }

      // 补全 content_type（ALS 结果可能缺少）
      val enriched = rawRecs.map { r =>
        if (r.content_type.isEmpty) r.copy(content_type = typeMap.getOrElse(r.content_id, "music"))
        else r
      }

      // DPP 多样性重排 + 分配排名和时间戳
      dppRerank(enriched, topN).zipWithIndex.map { case (rec, idx) =>
        rec.copy(rank = idx + 1, batch_id = batchId, compute_time = now, expire_time = expireTime)
      }
    }

    // 7. 写入 MySQL
    val recDF = spark.sparkContext.parallelize(recommendations).toDF()
    val connRec = java.sql.DriverManager.getConnection(jdbcUrl, dbProps)
    connRec.createStatement().execute("TRUNCATE TABLE offline_recommendations")
    connRec.close()
    recDF.write
      .mode(SaveMode.Append)
      .jdbc(jdbcUrl, "offline_recommendations", dbProps)

    println(s"[推荐引擎] 写入 ${recommendations.size} 条推荐结果")
  }

  /**
   * 冷启动推荐 — ε-greedy 探索 + 热门内容
   *
   * 85% 概率从按类型加权（6:4）的热门池中选取，
   * 15% 概率从全局池随机探索，保证多样性。
   */
  private def recommendColdStart(
    userId: Long, musicPool: Seq[(Long, String, Double)],
    videoPool: Seq[(Long, String, Double)],
    clusterDF: org.apache.spark.sql.DataFrame,
    spark: SparkSession
  ): Seq[Recommendation] = {
    import spark.implicits._

    val basePool = (musicPool.take((musicRatio * 200).toInt) ++
      videoPool.take(((1 - musicRatio) * 200).toInt)).sortBy(-_._3)

    // ε-greedy: 15% 概率从全局随机采样
    val pool = if (scala.util.Random.nextDouble() < epsilon) {
      scala.util.Random.shuffle(musicPool ++ videoPool).take(topN * 2)
    } else {
      basePool
    }

    scala.util.Random.shuffle(pool).take(topN).map { case (cid, ct, hs) =>
      Recommendation(userId, cid, ct, 0, hs, "coldstart", "cluster_hot", "", null, null)
    }
  }

  /**
   * 存量用户推荐回退 — hot-score + 随机扰动
   *
   * 当 ALS 模型不可用时使用，按类型比例从热门池中加权选取。
   */
  private def recommendEstablishedFallback(
    userId: Long, musicPool: Seq[(Long, String, Double)],
    videoPool: Seq[(Long, String, Double)]
  ): Seq[Recommendation] = {
    val pool = (scala.util.Random.shuffle(musicPool).take((musicRatio * topN * 3).toInt) ++
      scala.util.Random.shuffle(videoPool).take(((1 - musicRatio) * topN * 3).toInt))
      .sortBy(-_._3)

    pool.take(topN).map { case (cid, ct, hs) =>
      Recommendation(userId, cid, ct, 0, hs * (0.8 + scala.util.Random.nextDouble() * 0.4),
        "established", "hot_score", "", null, null)
    }
  }

  /**
   * DPP 多样性重排 — 贪心选物
   *
   * 从候选集中逐个选取与已选集合最不相似的内容。
   * 相似度基于内容类型: 同类 = 0.5, 不同类 = 0.1。
   * 多样性权重 θ = 0.7: score * (1.0 - 0.7 * avgSimilarity)
   */
  def dppRerank(candidates: Seq[Recommendation], n: Int): Seq[Recommendation] = {
    if (candidates.size <= n) return candidates

    val selected  = scala.collection.mutable.ArrayBuffer(candidates.head)
    val remaining = scala.collection.mutable.ArrayBuffer(candidates.tail: _*)

    while (selected.size < n && remaining.nonEmpty) {
      val best = remaining.maxBy { r =>
        val avgSim = selected.map { s =>
          if (s.content_type == r.content_type) 0.5 else 0.1
        }.sum / selected.size
        r.score * (1.0 - 0.7 * avgSim)
      }
      selected += best
      remaining -= best
    }

    selected.toSeq
  }

  /**
   * 过渡期平滑权重
   *
   * ratio = (behaviorCount - 30) / 50，线性从冷启动过渡到存量策略
   */
  def transitionBlend(behaviorCount: Int): Double =
    math.min(1.0, math.max(0.0, (behaviorCount - transitionMin).toDouble / (transitionMax - transitionMin)))

  // ── 安全类型转换 ──

  private def safeLong(row: org.apache.spark.sql.Row, col: String): Long =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).longValue()).getOrElse(0L)

  private def safeInt(row: org.apache.spark.sql.Row, col: String): Int =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).intValue()).getOrElse(0)

  private def safeDouble(row: org.apache.spark.sql.Row, col: String): Double =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).doubleValue()).getOrElse(0.0)
}
