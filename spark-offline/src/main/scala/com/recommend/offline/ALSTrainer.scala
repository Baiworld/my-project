package com.recommend.offline

import com.typesafe.config.ConfigFactory
import org.apache.spark.ml.recommendation.ALS
import org.apache.spark.sql.{SaveMode, SparkSession}
import org.apache.spark.sql.functions._
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule

/**
 * ALS 协同过滤模型训练器 — 隐式反馈
 *
 * 从 rt_user_profile 和 rt_content_hot 构建用户-物品隐式反馈交互矩阵，
 * 训练 ALS 模型（rank=50, alpha=40.0, regParam=0.1），保存模型和 ID 映射到磁盘。
 *
 * 训练数据构建策略:
 * - 每个用户根据其内容类型偏好（音乐/视频比例）生成约 100 条交互
 * - 交互置信度 = 内容热度分 * 类型偏好匹配度 * 随机因子（0.4~1.0）
 * - 这样产生的稀疏矩阵用于 ALS 隐式反馈训练
 */
object ALSTrainer {

  private val mapper = new ObjectMapper().registerModule(DefaultScalaModule)
  val modelBasePath = "E:/TraeBD/models/als"

  /**
   * 训练 ALS 模型
   *
   * 步骤: 读取数据 → 聚合用户偏好 → 获取内容列表 → Long→Int ID 映射 →
   *       构建交互矩阵 → 训练 ALS → 保存模型 + 双向 ID 映射 + 物品隐向量
   */
  def train(spark: SparkSession): Unit = {
    import spark.implicits._

    val cfg = ConfigFactory.load()

    val alsConf = cfg.getConfig("als")
    val rank    = alsConf.getInt("rank")
    val maxIter = alsConf.getInt("maxIter")
    val regParam = alsConf.getDouble("regParam")
    val alpha   = alsConf.getDouble("alpha")

    val jdbcUrl = cfg.getString("mysql.url") +
      "?useSSL=false&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true&allowPublicKeyRetrieval=true"
    val dbProps = new java.util.Properties()
    dbProps.setProperty("user", cfg.getString("mysql.user"))
    dbProps.setProperty("password", cfg.getString("mysql.password"))
    dbProps.setProperty("driver", "com.mysql.cj.jdbc.Driver")

    println(s"[ALS 训练] 参数: rank=$rank, maxIter=$maxIter, regParam=$regParam, alpha=$alpha")

    // 1. 读取数据
    val profileDF = spark.read.jdbc(jdbcUrl, "rt_user_profile", dbProps)
    val contentDF = spark.read.jdbc(jdbcUrl, "rt_content_hot", dbProps)

    if (profileDF.isEmpty || contentDF.isEmpty) {
      println("[ALS 训练] 数据为空，跳过训练")
      return
    }

    // 2. 按用户聚合：总行为数 + 内容类型偏好 + 实际行为信号
    val userAgg = profileDF.groupBy("user_id").agg(
      sum(coalesce(col("behavior_count"), lit(0))).as("total_behaviors"),
      sum(coalesce(col("play_count"), lit(0))).as("total_plays"),
      avg(coalesce(col("like_rate"), lit(0.0))).as("avg_like_rate"),
      avg(coalesce(col("favorite_rate"), lit(0.0))).as("avg_fav_rate"),
      avg(coalesce(col("completion_rate"), lit(0.0))).as("avg_completion"),
      avg(coalesce(col("skip_rate"), lit(0.0))).as("avg_skip"),
      first(coalesce(col("content_type_ratio"), lit("""{"music":0.6,"video":0.4}"""))).as("type_ratio")
    ).filter(col("total_behaviors") > 0)

    // 3. 获取内容列表（取每类型 Top-N 热门内容）
    val contents = contentDF.select(
      col("content_id"),
      coalesce(col("content_type"), lit("music")).as("content_type"),
      coalesce(col("hot_score"), lit(0.0)).as("hot_score")
    ).distinct().collect().map { row =>
      (row.getAs[Number]("content_id").longValue(),
       row.getAs[String]("content_type"),
       row.getAs[Number]("hot_score").doubleValue())
    }

    // 按热度降序排列，每类型取 Top-200（避免矩阵过大）
    val topN = 200
    val musicItems = contents.filter(_._2 == "music").sortBy(-_._3).take(topN)
    val videoItems = contents.filter(_._2 == "video").sortBy(-_._3).take(topN)
    val topContents = musicItems ++ videoItems

    println(s"[ALS 训练] 内容统计: Top音乐=${musicItems.length}, Top视频=${videoItems.length}")

    // 4. 归一化参数（用于计算置信度权重）
    val maxPlays   = if (userAgg.count() > 0) userAgg.agg(max("total_plays")).as[Long].head() else 1L
    val maxHot     = topContents.map(_._3).max

    // 5. 收集用户偏好
    val userRows = userAgg.collect()
    println(s"[ALS 训练] 用户数: ${userRows.length}")

    // 6. Long → Int ID 映射（ALS 要求 Int 类型）
    val userIds    = userRows.map(r => r.getAs[Number]("user_id").longValue()).distinct.sorted
    val contentIds = topContents.map(_._1).distinct.sorted

    val userToIdx    = userIds.zipWithIndex.toMap
    val contentToIdx = contentIds.zipWithIndex.toMap

    // 7. 基于真实行为数据构建隐式反馈交互矩阵
    // 置信度 = 归一化播放量 × 热度分 × (1 + like_rate - skip_rate) × 类型偏好
    // 不使用任何随机因子 — 全部基于实际数据
    val interactions = userRows.flatMap { row =>
      val uid = row.getAs[Number]("user_id").longValue()
      val totalPlays = row.getAs[Number]("total_plays").longValue()
      val likeRate   = Option(row.getAs[Number]("avg_like_rate")).map(_.doubleValue()).getOrElse(0.0)
      val skipRate   = Option(row.getAs[Number]("avg_skip")).map(_.doubleValue()).getOrElse(0.0)
      val favRate    = Option(row.getAs[Number]("avg_fav_rate")).map(_.doubleValue()).getOrElse(0.0)
      val completion = Option(row.getAs[Number]("avg_completion")).map(_.doubleValue()).getOrElse(0.0)
      val (musicPref, videoPref) = parseTypeRatio(
        row.getAs[String]("type_ratio"))

      val uIdx = userToIdx(uid)

      // 行为权重：基于实际播放数和互动率
      val playWeight   = math.log1p(totalPlays) / math.log1p(maxPlays)  // 对数归一化
      val engageWeight = 1.0 + likeRate + favRate * 0.5 + completion * 0.3 - skipRate * 0.5
      val baseWeight   = math.max(0.2, playWeight * math.max(0.3, engageWeight))

      // 根据类型偏好分配交互数量
      val nMusic = math.max(8,  math.min(topN, (musicPref * 80 * baseWeight).toInt))
      val nVideo = math.max(5,  math.min(topN, (videoPref * 60 * baseWeight).toInt))

      // 音乐交互 — 取热度最高的前 nMusic 首
      val mInts = musicItems.take(nMusic).flatMap {
        case (cid, _, hotScore) =>
          contentToIdx.get(cid).map { cIdx =>
            val confidence = (hotScore / maxHot * musicPref * engageWeight).toFloat
            Interaction(uIdx, cIdx, math.max(0.05f, confidence))
          }
      }

      // 视频交互 — 取热度最高的前 nVideo 个
      val vInts = videoItems.take(nVideo).flatMap {
        case (cid, _, hotScore) =>
          contentToIdx.get(cid).map { cIdx =>
            val confidence = (hotScore / maxHot * videoPref * engageWeight).toFloat
            Interaction(uIdx, cIdx, math.max(0.05f, confidence))
          }
      }
      mInts ++ vInts
    }

    println(s"[ALS 训练] 交互记录: ${interactions.length} (${userToIdx.size} 用户 × ${contentToIdx.size} 内容)")

    if (interactions.length < 100) {
      println("[ALS 训练] 交互记录不足，跳过训练")
      return
    }

    // 7. 转换为 DataFrame
    val trainingDF = spark.sparkContext.parallelize(interactions)
      .toDF("user", "item", "rating")
      .repartition(8)

    // 8. 训练 ALS（隐式反馈模式）
    val als = new ALS()
      .setRank(rank)
      .setMaxIter(maxIter)
      .setRegParam(regParam)
      .setAlpha(alpha)
      .setImplicitPrefs(true)     // 隐式反馈：rating 表示置信度而非显式评分
      .setUserCol("user")
      .setItemCol("item")
      .setRatingCol("rating")
      .setColdStartStrategy("drop")

    println("[ALS 训练] 开始训练 ALS 模型...")
    val t0 = System.currentTimeMillis()
    val model = als.fit(trainingDF)
    val elapsed = (System.currentTimeMillis() - t0) / 1000.0
    println(f"[ALS 训练] 训练完成，耗时 $elapsed%.1f 秒")

    // 9. 保存模型和映射
    model.write.overwrite().save(s"$modelBasePath/model")

    // 正向映射: Long ID → Int Index
    spark.createDataFrame(userToIdx.toSeq).toDF("user_id", "user_idx")
      .write.mode(SaveMode.Overwrite).parquet(s"$modelBasePath/user_mapping")

    spark.createDataFrame(contentToIdx.toSeq).toDF("content_id", "content_idx")
      .write.mode(SaveMode.Overwrite).parquet(s"$modelBasePath/content_mapping")

    // 反向映射: Int Index → Long ID（用于推荐时还原）
    spark.createDataFrame(userToIdx.toSeq.map(_.swap)).toDF("user_idx", "user_id")
      .write.mode(SaveMode.Overwrite).parquet(s"$modelBasePath/idx_to_user")

    spark.createDataFrame(contentToIdx.toSeq.map(_.swap)).toDF("content_idx", "content_id")
      .write.mode(SaveMode.Overwrite).parquet(s"$modelBasePath/idx_to_content")

    // 保存物品隐向量（供相似度矩阵使用）
    model.itemFactors.write.mode(SaveMode.Overwrite).parquet(s"$modelBasePath/item_factors")

    println(s"[ALS 训练] 模型已保存到 $modelBasePath")
  }

  /** 交互记录 — 用户索引、内容索引、置信度评分 */
  private case class Interaction(user: Int, item: Int, rating: Float)

  /** 解析 content_type_ratio JSON，提取音乐和视频偏好比例 */
  private def parseTypeRatio(json: String): (Double, Double) = {
    try {
      val node = mapper.readTree(json)
      val music = Option(node.get("music")).map(_.asDouble()).getOrElse(0.6)
      val video = Option(node.get("video")).map(_.asDouble()).getOrElse(0.4)
      (music, video)
    } catch { case _: Exception => (0.6, 0.4) }
  }
}
