package com.recommend.offline

import org.apache.spark.ml.recommendation.ALSModel
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

/**
 * ALS 推荐推理器 — 加载训练好的 ALS 模型，批量生成推荐
 *
 * 支持批量推理: 一次性为所有存量用户生成 Top-N 推荐，
 * 通过 Long→Int→Long 的 ID 映射还原原始 ID。
 * 模型不存在时返回空 Map，调用方回退到 hot-score 推荐。
 */
object ALSRecommender {

  private val modelBasePath = "E:/TraeBD/models/als"

  /** 检查训练好的 ALS 模型是否存在 */
  def modelExists: Boolean = {
    try { new java.io.File(s"$modelBasePath/model/_SUCCESS").exists }
    catch { case _: Exception => false }
  }

  /**
   * 批量推荐：为给定用户生成 Top-N 推荐
   *
   * @param spark   SparkSession
   * @param userIds 目标用户 ID 列表
   * @param topN    每个用户推荐的物品数量（默认 50）
   * @return 按 user_id 分组的推荐结果 Map，未命中用户为空列表
   */
  def recommend(
    spark: SparkSession,
    userIds: Seq[Long],
    topN: Int = 50
  ): Map[Long, Seq[Recommendation]] = {
    import spark.implicits._

    if (!modelExists || userIds.isEmpty) {
      return Map.empty.withDefaultValue(Seq.empty)
    }

    // 1. 加载模型（失败则回退）
    val model: ALSModel = try {
      ALSModel.load(s"$modelBasePath/model")
    } catch {
      case _: Exception =>
        println("[ALS 推荐] 模型加载失败")
        return Map.empty.withDefaultValue(Seq.empty)
    }

    // 2. 加载 ID 映射表
    val userMapping = loadOrFail(spark, "user_mapping")
    val idxToContent = loadOrFail(spark, "idx_to_content")
    val idxToUser = loadOrFail(spark, "idx_to_user")

    if (userMapping.isEmpty) {
      return Map.empty.withDefaultValue(Seq.empty)
    }

    // 3. 筛选在训练集中的用户（与映射表做内连接）
    val targetDF = userIds.distinct.toDF("user_id")

    val knownUsers = targetDF
      .join(userMapping.get, Seq("user_id"), "inner")
      .select(col("user_idx").as("user"), col("user_id"))

    if (knownUsers.isEmpty) {
      return Map.empty.withDefaultValue(Seq.empty)
    }

    val knownCount = knownUsers.count()
    println(s"[ALS 推荐] $knownCount / ${userIds.distinct.length} 个用户在训练集中")

    // 4. 调用 Spark ML 批量推荐
    val recsDF = model.recommendForUserSubset(knownUsers, topN)

    // recommendForUserSubset 返回: user(Int), recommendations(Array(Struct(item:Int, rating:Float)))
    val exploded = recsDF
      .select(col("user"), explode(col("recommendations")).as("rec"))
      .select(
        col("user"),
        col("rec.item").as("content_idx"),   // ALS 内部的 Int 索引
        col("rec.rating").as("score")         // ALS 预测评分
      )

    // 5. 还原为原始 Long ID（Int Index → content_id, user_id）
    val result = exploded
      .join(idxToContent.get, Seq("content_idx"), "inner")
      .join(idxToUser.get, exploded("user") === idxToUser.get("user_idx"), "inner")
      .select(
        idxToUser.get("user_id"),
        idxToContent.get("content_id"),
        col("score")
      )
      .collect()

    // 6. 按用户分组，按评分降序排列
    val grouped: Map[Long, Seq[Recommendation]] = result.groupBy { row =>
      row.getAs[Long]("user_id")
    }.map { case (uid, rows) =>
      val recs = rows.sortBy(r => -r.getAs[Float]("score")).zipWithIndex.map {
        case (row, idx) =>
          Recommendation(
            user_id      = uid,
            content_id   = row.getAs[Long]("content_id"),
            content_type = "",    // 调用方会补全
            rank         = idx + 1,
            score        = row.getAs[Float]("score").toDouble,
            strategy     = "established",
            reason       = "als_cf",
            batch_id     = "",
            compute_time = null,
            expire_time  = null
          )
      }.toSeq
      (uid, recs)
    }

    println(s"[ALS 推荐] 为 ${grouped.size} 个用户生成了推荐")
    grouped.withDefaultValue(Seq.empty)
  }

  /** 加载 Parquet 映射表，失败返回 None */
  private def loadOrFail(spark: SparkSession, name: String): Option[org.apache.spark.sql.DataFrame] = {
    try {
      Some(spark.read.parquet(s"$modelBasePath/$name"))
    } catch {
      case _: Exception =>
        println(s"[ALS 推荐] 加载映射表 $name 失败")
        None
    }
  }
}
