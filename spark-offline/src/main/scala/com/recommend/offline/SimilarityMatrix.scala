package com.recommend.offline

import com.typesafe.config.ConfigFactory
import org.apache.spark.ml.linalg.Vector
import org.apache.spark.sql.{SaveMode, SparkSession}
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import java.sql.Timestamp

/**
 * FR-07 内容相似度矩阵 — 基于 ALS 物品隐向量或内容特征的余弦相似度
 *
 * 优先从 ALS 模型的 item_factors 加载物品隐向量（rank=50 维），计算余弦相似度。
 * ALS 模型不可用时，从 content_metadata 表提取内容特征（标签、风格、BPM、语言等），
 * 计算基于内容的 Jaccard+特征加权相似度，确保相似度始终有实际语义。
 *
 * 音乐与视频分别在各自类型内计算，相似度 > 0.3 的配对写入 offline_content_sim。
 */
object SimilarityMatrix {

  private val modelBasePath = "E:/TraeBD/models/als"
  private val mapper = new ObjectMapper().registerModule(DefaultScalaModule)

  /** 内容元数据特征 — 用于基于内容的相似度计算 */
  private case class ContentFeatures(
    contentId:   Long,
    contentType: String,
    tags:        Set[String],
    style:       String,
    language:    String,
    bpm:         Double,
    duration:    Double
  )

  /**
   * 计算内容相似度矩阵
   *
   * 步骤: 加载内容列表 → 尝试加载 ALS 隐向量 → 组内两两计算相似度 → 写入 MySQL
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

    // 尝试加载 ALS 物品隐向量，不可用时加载内容特征用于基于内容的相似度
    val featureMap: Map[Long, Array[Double]] = loadFeatureMap(spark, contents.map(_._1))
    val useALS = featureMap.nonEmpty

    // 内容特征回退（ALS 不可用时使用）
    val contentFeatures: Map[Long, ContentFeatures] = if (!useALS) {
      loadContentFeatures(spark, jdbcUrl, dbProps)
    } else Map.empty

    if (useALS) {
      println(s"[相似度矩阵] 使用 ALS 隐向量计算余弦相似度 (${featureMap.size} 个内容)")
    } else {
      println(s"[相似度矩阵] ALS 模型不可用，使用内容特征计算相似度 (${contentFeatures.size} 个内容)")
    }

    // 按风格/类别分桶，仅在桶内计算相似度，避免 O(n^2) 全量配对
    val musicByStyle = musicItems.groupBy { case (id, _) =>
      contentFeatures.get(id).map(_.style).getOrElse("unknown")
    }
    val videoByStyle = videoItems.groupBy { case (id, _) =>
      contentFeatures.get(id).map(_.style).getOrElse("unknown")
    }

    // 音乐内容相似度（按风格分桶计算）
    val musicSimRDD = spark.sparkContext.parallelize(musicByStyle.toSeq).flatMap { case (style, items) =>
      val arr = items.toArray
      for {
        i <- arr.indices
        j <- (i + 1) until arr.length
        (idA, _) = arr(i)
        (idB, _) = arr(j)
        sim = computeSim(featureMap, contentFeatures, idA, idB, useALS)
        if sim > 0.3
      } yield ContentSim(idA, idB, "music", sim, now)
    }

    // 视频内容相似度（按风格分桶计算）
    val videoSimRDD = spark.sparkContext.parallelize(videoByStyle.toSeq).flatMap { case (style, items) =>
      val arr = items.toArray
      for {
        i <- arr.indices
        j <- (i + 1) until arr.length
        (idA, _) = arr(i)
        (idB, _) = arr(j)
        sim = computeSim(featureMap, contentFeatures, idA, idB, useALS)
        if sim > 0.3
      } yield ContentSim(idA, idB, "video", sim, now)
    }

    val allSimDF = musicSimRDD.union(videoSimRDD).toDF()

    val connSim = java.sql.DriverManager.getConnection(jdbcUrl, dbProps)
    connSim.createStatement().execute("TRUNCATE TABLE offline_content_sim")
    connSim.close()
    allSimDF.write
      .mode(SaveMode.Append)
      .jdbc(jdbcUrl, "offline_content_sim", dbProps)

    println(s"[相似度矩阵] 写入 ${allSimDF.count()} 条内容相似度记录")
  }

  /**
   * 从 content_metadata 表加载内容特征
   *
   * 提取: 标签集合、风格/类别、语言、BPM、时长
   */
  private def loadContentFeatures(spark: SparkSession, jdbcUrl: String, dbProps: java.util.Properties): Map[Long, ContentFeatures] = {
    try {
      val metaDF = spark.read.jdbc(jdbcUrl, "content_metadata", dbProps)
      metaDF.collect().flatMap { row =>
        val cid  = safeLong(row, "content_id")
        val ctype = Option(row.getAs[String]("content_type")).getOrElse("music")
        val tags: Set[String] = try {
          val tagsJson = Option(row.getAs[String]("tags")).getOrElse("[]")
          val node = mapper.readTree(tagsJson)
          if (node.isArray) {
            import scala.collection.JavaConverters._
            node.elements().asScala.map(_.asText().trim.toLowerCase).toSet
          } else Set.empty[String]
        } catch { case _: Exception => Set.empty[String] }

        Some(cid -> ContentFeatures(
          contentId   = cid,
          contentType = ctype,
          tags        = tags,
          style       = Option(row.getAs[String]("style_or_category")).getOrElse(""),
          language    = Option(row.getAs[String]("language")).getOrElse(""),
          bpm         = safeDouble(row, "bpm"),
          duration    = safeDouble(row, "duration")
        ))
      }.toMap
    } catch {
      case _: Exception =>
        println("[相似度矩阵] content_metadata 表不可用")
        Map.empty
    }
  }

  /**
   * 加载 ALS 模型产出的物品隐向量和 ID 映射
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
   * - 有 ALS 隐向量时：余弦相似度
   * - 无 ALS 时：基于内容特征的多维度加权相似度
   *   - 标签 Jaccard 相似度（权重 0.40）
   *   - 风格匹配（权重 0.25）
   *   - BPM 归一化距离（权重 0.10，仅音乐）
   *   - 语言匹配（权重 0.15）
   *   - 时长归一化距离（权重 0.10）
   */
  private def computeSim(
    featureMap:  Map[Long, Array[Double]],
    contentFeat: Map[Long, ContentFeatures],
    idA: Long, idB: Long, useALS: Boolean
  ): Double = {
    if (useALS) {
      (featureMap.get(idA), featureMap.get(idB)) match {
        case (Some(a), Some(b)) => cosineSimilarity(a, b)
        case _                  => contentBasedSim(contentFeat, idA, idB)
      }
    } else {
      contentBasedSim(contentFeat, idA, idB)
    }
  }

  /**
   * 基于内容特征的多维度加权相似度
   *
   * 得分 = 0.40 * Jaccard(标签) + 0.25 * 风格匹配 + 0.15 * 语言匹配
   *       + 0.10 * (1 - |BPM差|/200) + 0.10 * (1 - |时长差|/600)
   */
  private def contentBasedSim(feat: Map[Long, ContentFeatures], idA: Long, idB: Long): Double = {
    val fa = feat.get(idA)
    val fb = feat.get(idB)
    if (fa.isEmpty || fb.isEmpty) return 0.0
    val a = fa.get; val b = fb.get

    // 标签 Jaccard 相似度
    val jaccard = if (a.tags.nonEmpty && b.tags.nonEmpty) {
      val intersection = a.tags.intersect(b.tags).size.toDouble
      val union = a.tags.union(b.tags).size.toDouble
      if (union > 0) intersection / union else 0.0
    } else 0.0

    // 风格匹配
    val styleMatch = if (a.style.nonEmpty && b.style.nonEmpty && a.style == b.style) 1.0 else 0.0

    // 语言匹配
    val langMatch = if (a.language.nonEmpty && b.language.nonEmpty && a.language == b.language) 1.0 else 0.0

    // BPM 距离（归一化到 0-1，差 200 以上为 0）
    val bpmDist = math.max(0.0, 1.0 - math.abs(a.bpm - b.bpm) / 200.0)

    // 时长距离（归一化到 0-1，差 600 秒以上为 0）
    val durDist = math.max(0.0, 1.0 - math.abs(a.duration - b.duration) / 600.0)

    // 加权求和
    0.40 * jaccard + 0.25 * styleMatch + 0.15 * langMatch + 0.10 * bpmDist + 0.10 * durDist
  }

  /** 余弦相似度 */
  def cosineSimilarity(a: Array[Double], b: Array[Double]): Double = {
    val dotProduct = a.zip(b).map { case (x, y) => x * y }.sum
    val normA = math.sqrt(a.map(x => x * x).sum)
    val normB = math.sqrt(b.map(x => x * x).sum)
    if (normA == 0 || normB == 0) 0.0 else dotProduct / (normA * normB)
  }

  private def safeLong(row: org.apache.spark.sql.Row, col: String): Long =
    Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).longValue()).getOrElse(0L)

  private def safeDouble(row: org.apache.spark.sql.Row, col: String): Double =
    try { Option(row.get(row.fieldIndex(col))).map(v => new java.math.BigDecimal(v.toString).doubleValue()).getOrElse(0.0) } catch { case _: Exception => 0.0 }
}
