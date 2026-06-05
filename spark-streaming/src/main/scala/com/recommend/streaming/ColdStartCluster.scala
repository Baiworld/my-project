package com.recommend.streaming

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import org.apache.spark.mllib.clustering.{KMeans, KMeansModel}
import org.apache.spark.mllib.linalg.Vectors
import org.apache.spark.rdd.RDD
import org.apache.spark.streaming.dstream.DStream
import scala.collection.mutable.ArrayBuffer

/**
 * FR-05 冷启动用户实时 K-Means 聚类
 *
 * 基于用户注册信息（设备类型、操作系统、渠道、地区、年龄段、兴趣标签）构建
 * 79 维特征向量，使用 K-Means（K=8）对冷启动用户进行聚类。
 *
 * 采用增量训练策略：特征缓冲区累积满 200 条或距上次训练超过 1 小时后重新训练模型。
 * 新用户直接预测其所属聚类，输出簇归属和簇中心向量。
 */
object ColdStartCluster extends Serializable {

  private val k           = 8     // 聚类数
  private val maxIter     = 20    // 最大迭代次数
  private val bufferSize  = 200   // 缓冲区大小（达到此数量触发重新训练）
  private val retrainHour = 1     // 重训练间隔（小时）

  // ── 特征词表 ──
  private val deviceTypes       = Seq("android", "ios", "web", "ipad")
  private val channels          = Seq("organic", "app_store_search", "ad_google", "ad_facebook", "wechat_mini", "douyin_campaign", "referral", "seo")
  private val regions           = Seq("CN-BJ", "CN-SH", "CN-GD", "CN-ZJ", "CN-SC", "CN-HB", "CN-HN", "CN-FJ", "CN-SD", "CN-JS")
  private val ageGroups         = Seq("<18", "18-24", "25-34", "35-44", "45-54", "55+")
  private val allInterestTags   = Seq(
    "华语", "欧美", "日韩", "流行", "经典", "治愈", "励志", "伤感", "甜蜜", "燃向",
    "古风", "电子", "摇滚", "民谣", "说唱", "二次元", "影视", "游戏", "运动", "美食",
    "旅行", "时尚", "科技", "学习", "生活", "搞笑", "萌宠", "舞蹈", "翻唱", "原创",
    "2024", "2025", "怀旧", "新歌", "热歌", "冷门", "小众", "网红", "校园", "职场",
    "轻音乐", "纯音乐", "DJ", "串烧", "混音", "教程", "开箱", "测评", "挑战", "日常"
  )

  // 特征维度: device(4) + os(1) + channel(8) + region(10) + age(6) + interest(50) = 79
  private val featureDim = 4 + 1 + 8 + 10 + 6 + 50

  private val mapper = new ObjectMapper().registerModule(DefaultScalaModule)

  // ── 缓冲区与模型状态 ──
  @transient private var featureBuffer: ArrayBuffer[org.apache.spark.mllib.linalg.Vector] = ArrayBuffer.empty
  @transient private var userIdBuffer: ArrayBuffer[UserRegisterEvent] = ArrayBuffer.empty
  @transient private var kmeansModel: Option[KMeansModel] = None
  @transient private var lastTrainTime: Long = 0L
  private var clusterSizes: Map[Int, Int] = Map.empty

  /**
   * 对用户注册流进行实时聚类
   *
   * 每个微批次: 累积特征 → 判断是否重新训练 → 为当前批次的用户预测聚类归属
   * 模型未训练时返回默认 clusterId = 0
   */
  def cluster(stream: DStream[UserRegisterEvent]): DStream[ClusterResult] = {
    stream.transform { rdd =>
      val events = rdd.collect()  // 收集到 Driver（适用于中小规模数据）
      if (events.isEmpty) {
        rdd.sparkContext.emptyRDD[ClusterResult]
      } else {

        // 累积特征向量和用户事件到缓冲区
        val encoded = events.map(e => (e, encodeFeatures(e)))
        featureBuffer ++= encoded.map(_._2)
        userIdBuffer ++= encoded.map(_._1)

        val now = System.currentTimeMillis()
        // 判断是否需要重新训练: 缓冲区满 或 距上次训练超过 1 小时
        val shouldRetrain = featureBuffer.size >= bufferSize ||
          (featureBuffer.nonEmpty && (now - lastTrainTime) > retrainHour * 3600 * 1000L)

        if (shouldRetrain) {
          retrainModel(rdd.sparkContext.parallelize(featureBuffer.toSeq))
          featureBuffer.clear()
          userIdBuffer.clear()
        }

        // 预测当前批次用户的聚类归属
        if (kmeansModel.isDefined) {
          val model = kmeansModel.get
          val results = encoded.map { case (event, vec) =>
            val clusterId = model.predict(org.apache.spark.mllib.linalg.Vectors.dense(vec.toArray))
            ClusterResult(
              userId          = event.userId,
              clusterId       = clusterId,
              clusterCenter   = mapper.writeValueAsString(model.clusterCenters(clusterId).toArray),
              clusterSize     = clusterSizes.getOrElse(clusterId, 0),
              deviceType      = event.deviceType,
              registerChannel = event.registerChannel,
              interestTags    = mapper.writeValueAsString(event.interestTags),
              computeTime     = now
            )
          }
          rdd.sparkContext.parallelize(results)
        } else {
          // 模型未训练，返回默认聚类
          val results = encoded.map { case (event, _) =>
            ClusterResult(
              userId          = event.userId,
              clusterId       = 0,
              clusterCenter   = "[]",
              clusterSize     = featureBuffer.size,
              deviceType      = event.deviceType,
              registerChannel = event.registerChannel,
              interestTags    = mapper.writeValueAsString(event.interestTags),
              computeTime     = now
            )
          }
          rdd.sparkContext.parallelize(results)
        }
      }
    }
  }

  /**
   * 将用户注册事件编码为 79 维特征向量
   *
   * 编码方案:
   *   idx  0-3:   device_type One-Hot (4 维)
   *   idx  4:     os_version 数值 (1 维)
   *   idx  5-12:  register_channel One-Hot (8 维)
   *   idx 13-22:  region One-Hot (10 维)
   *   idx 23-28:  age_group One-Hot (6 维)
   *   idx 29-78:  interest_tags Multi-Hot (50 维)
   */
  def encodeFeatures(event: UserRegisterEvent): org.apache.spark.mllib.linalg.Vector = {
    val feats = Array.fill[Double](featureDim)(0.0)
    var idx = 0

    // device_type One-Hot (4)
    deviceTypes.zipWithIndex.foreach { case (dt, i) =>
      if (event.deviceType == dt) feats(idx + i) = 1.0
    }
    idx += 4

    // os_version 数值
    feats(idx) = TryNum(event.osVersion.replaceAll("[^0-9.]", "").split("\\.").headOption.map(_.toDouble).getOrElse(0.0))
    idx += 1

    // register_channel One-Hot (8)
    channels.zipWithIndex.foreach { case (ch, i) =>
      if (event.registerChannel == ch) feats(idx + i) = 1.0
    }
    idx += 8

    // region One-Hot (10)
    regions.zipWithIndex.foreach { case (r, i) =>
      if (event.region == r) feats(idx + i) = 1.0
    }
    idx += 10

    // age_group One-Hot (6)
    ageGroups.zipWithIndex.foreach { case (ag, i) =>
      if (event.ageGroup == ag) feats(idx + i) = 1.0
    }
    idx += 6

    // interest_tags Multi-Hot (50)
    val userTags = event.interestTags.toSet
    allInterestTags.zipWithIndex.foreach { case (tag, i) =>
      if (userTags.contains(tag)) feats(idx + i) = 1.0
    }

    Vectors.dense(feats)
  }

  /** 使用缓冲区中的特征数据重新训练 K-Means 模型，统计各聚类大小 */
  private def retrainModel(featuresRDD: RDD[org.apache.spark.mllib.linalg.Vector]): Unit = {
    val cachedRDD = featuresRDD.cache()
    val model = new KMeans()
      .setK(k)
      .setMaxIterations(maxIter)
      .setSeed(System.currentTimeMillis())
      .run(cachedRDD)

    val predictions = cachedRDD.map(p => model.predict(p))
    clusterSizes = predictions.countByValue().map { case (c, count) => c.toInt -> count.toInt }.toMap
    kmeansModel = Some(model)
    lastTrainTime = System.currentTimeMillis()
    cachedRDD.unpersist()
  }

  /** 安全数值转换，解析失败时返回 0.0 */
  private def TryNum(s: => Double): Double = try { s } catch { case _: Throwable => 0.0 }
}
