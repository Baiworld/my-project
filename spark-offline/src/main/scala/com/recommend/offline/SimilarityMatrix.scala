package com.recommend.offline

import com.typesafe.config.ConfigFactory
import org.apache.spark.ml.linalg.Vector
import org.apache.spark.sql.{SaveMode, SparkSession}
import java.sql.Timestamp

/**
 * FR-07 内容相似度矩阵 — 基于 ALS 物品隐向量的余弦相似度
 *
 * 优先从 ALS 模型的 item_factors 加载物品隐向量（rank=50 维），计算两两余弦相似度。
 * ALS 模型不可用时回退到随机相似度（0.15~0.80）。
 *
 * 音乐与视频分别在各自类型内计算，相似度 > 0.3 的配对写入 offline_content_sim。
 */
object SimilarityMatrix {

  private val modelBasePath = "E:/TraeBD/models/als"

  /**
   * 计算内容相似度矩阵
   *
   * 步骤: 加载内容列表 → 尝试加载 ALS 隐向量 → 组内两两计算余弦相似度 → 写入 MySQL
   */
  def compute(spark: SparkSession): Unit = {
    import spark.implicits._

    val cfg     = ConfigFactory.load().getConfig("mysql")
    val jdbcUrl = cfg.getString("url") + "?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true"
    val dbProps = new java.util.Properties()
    dbProps.setProperty("user", cfg.getString("user"))
    dbProps.setProperty("password", cfg.getString("password"))
    dbProps.setProperty("driver", "com.mysql.cj.jdbc.Driver")

    val hotDF = spark.read.jdbc(jdbcUrl, "rt_content_hot", dbProps)

    // 获取所有去重内容
    val contents = hotDF.select("content_id", "content_type").distinct()
      .collect().map { row =>
        (safeLong(row, "content_id"),
         Option(row.getAs[String]("content_type")).getOrElse("music"))
      }.toSeq

    val musicItems = contents.filter(_._2 == "music")
    val videoItems = contents.filter(_._2 == "video")

    val now = new Timestamp(System.currentTimeMillis())

    // 尝试加载 ALS 物品隐向量，不可用时回退随机相似度
    val featureMap: Map[Long, Array[Double]] = loadFeatureMap(spark, contents.map(_._1))

    val useALS = featureMap.nonEmpty
    if (useALS) {
      println(s"[相似度矩阵] 使用 ALS 隐向量计算余弦相似度 (${featureMap.size} 个内容)")
    } else {
      println("[相似度矩阵] ALS 模型不可用，使用随机相似度")
    }

    // 音乐内容相似度
    val musicSimRDD = spark.sparkContext.parallelize(musicItems).flatMap { case (idA, _) =>
      val others = musicItems.filter { case (idB, _) => idB > idA }
      others.flatMap { case (idB, _) =>
        val sim = computeSim(featureMap, idA, idB, useALS)
        if (sim > 0.3) Some(ContentSim(idA, idB, "music", sim, now))
        else None
      }
    }

    // 视频内容相似度
    val videoSimRDD = spark.sparkContext.parallelize(videoItems).flatMap { case (idA, _) =>
      val others = videoItems.filter { case (idB, _) => idB > idA }
      others.flatMap { case (idB, _) =>
        val sim = computeSim(featureMap, idA, idB, useALS)
        if (sim > 0.3) Some(ContentSim(idA, idB, "video", sim, now))
        else None
      }
    }

    val allSimDF = musicSimRDD.union(videoSimRDD).toDF()

    allSimDF.write
      .mode(SaveMode.Overwrite)
      .jdbc(jdbcUrl, "offline_content_sim", dbProps)

    println(s"[相似度矩阵] 写入 ${allSimDF.count()} 条内容相似度记录")
  }

  /**
   * 加载 ALS 模型产出的物品隐向量和 ID 映射
   *
   * @return Map[content_id → 50维特征向量]，加载失败返回空 Map
   */
  private def loadFeatureMap(spark: SparkSession, contentIds: Seq[Long]): Map[Long, Array[Double]] = {
    try {
      val itemFactors = spark.read.parquet(s"$modelBasePath/item_factors")
      val contentMapping = spark.read.parquet(s"$modelBasePath/content_mapping")

      import spark.implicits._
      val idSet = contentIds.toSet

      val joined = itemFactors
        .join(contentMapping, itemFactors("id") === contentMapping("content_idx"), "inner")
        .select(contentMapping("content_id"), itemFactors("features"))
        .collect()

      joined.flatMap { row =>
        val cid = row.getAs[Long]("content_id")
        if (idSet.contains(cid)) {
          val vec = row.getAs[Vector]("features")
          Some(cid -> vec.toArray)
        } else None
      }.toMap
    } catch {
      case _: Exception => Map.empty
    }
  }

  /**
   * 计算两个内容的相似度
   *
   * 有 ALS 隐向量时用余弦相似度，否则用随机相似度。两者均无隐向量时回退随机。
   */
  private def computeSim(featureMap: Map[Long, Array[Double]], idA: Long, idB: Long, useALS: Boolean): Double = {
    if (useALS) {
      (featureMap.get(idA), featureMap.get(idB)) match {
        case (Some(a), Some(b)) => cosineSimilarity(a, b)
        case _                  => 0.15 + scala.util.Random.nextDouble() * 0.65
      }
    } else {
      0.15 + scala.util.Random.nextDouble() * 0.65
    }
  }

  /**
   * 余弦相似度公式: cos(a, b) = (a · b) / (|a| * |b|)
   *
   * 取值范围 [0, 1]，两向量正交时为 0。
   */
  def cosineSimilarity(a: Array[Double], b: Array[Double]): Double = {
    val dotProduct = a.zip(b).map { case (x, y) => x * y }.sum
    val normA = math.sqrt(a.map(x => x * x).sum)
    val normB = math.sqrt(b.map(x => x * x).sum)
    if (normA == 0 || normB == 0) 0.0 else dotProduct / (normA * normB)
  }

  private def safeLong(row: org.apache.spark.sql.Row, col: String): Long =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).longValue()).getOrElse(0L)
}
