package com.recommend.streaming

import com.typesafe.config.ConfigFactory
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.spark.SparkConf
import org.apache.spark.streaming.{Seconds, StreamingContext}
import org.apache.spark.streaming.dstream.DStream
import org.apache.spark.streaming.kafka010.{ConsumerStrategies, KafkaUtils, LocationStrategies}

/**
 * Spark Streaming 主入口 — 组装实时分析管线
 *
 * 管线流程:
 * 1. 配置 SparkConf（local 模式 + 背压 + Kryo 序列化）
 * 2. 从 Kafka 消费 3 个 Topic（user_behavior / content_metadata / user_register）
 * 3. 按 Topic 分流
 * 4. 数据校验（DataValidator — JSON 解析 + 去重 + 死信路由）
 * 5. 实时聚合（用户画像 / 内容热度 / 冷启动聚类）
 * 6. 批量写入 MySQL（rt_user_profile / rt_content_hot / rt_coldstart_cluster）
 * 7. 启动 StreamingContext 等待终止
 */
object RealTimeAnalysisApp {

  def main(args: Array[String]): Unit = {

    val cfg = ConfigFactory.load()
    val bootstrapServers = cfg.getString("kafka.bootstrap.servers")

    // ── 1. SparkConf 配置 ──
    val conf = new SparkConf()
      .setAppName("HybridRecSys-Streaming")
      .setMaster("local[*]")
      .set("spark.sql.shuffle.partitions", "8")
      .set("spark.streaming.backpressure.enabled", "true")       // 开启背压，防止消费过快
      .set("spark.streaming.kafka.maxRatePerPartition", "500")   // 每分区每秒最多 500 条
      .set("spark.streaming.stopGracefullyOnShutdown", "true")   // 优雅关闭
      .set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")

    val ssc = new StreamingContext(conf, Seconds(10))  // 10 秒微批次间隔
    ssc.checkpoint("E:/TraeBD/checkpoints/streaming-v2")

    // ── 2. Kafka 消费配置 ──
    val groupId = if (cfg.hasPath("kafka.group.id")) cfg.getString("kafka.group.id") else "hybrid_rec_streaming"

    val kafkaParams = Map[String, Object](
      "bootstrap.servers"  -> bootstrapServers,
      "key.deserializer"   -> classOf[StringDeserializer],
      "value.deserializer" -> classOf[StringDeserializer],
      "group.id"           -> groupId,
      "auto.offset.reset"  -> "earliest",
      "enable.auto.commit" -> (false: java.lang.Boolean)
    )

    import scala.collection.JavaConverters._
    val topics = cfg.getStringList("kafka.topics").asScala.toArray

    // ── 3. 创建 Kafka DStream ──
    val kafkaStream = KafkaUtils.createDirectStream[String, String](
      ssc,
      LocationStrategies.PreferConsistent,
      ConsumerStrategies.Subscribe[String, String](topics, kafkaParams)
    )

    // 按 Topic 分流为三个独立 DStream
    val topicStreams = kafkaStream.map(r => (r.topic(), r.value()))

    val behaviorStream = topicStreams.filter(_._1 == "user_behavior").map(_._2)
    val metadataStream = topicStreams.filter(_._1 == "content_metadata").map(_._2)
    val registerStream = topicStreams.filter(_._1 == "user_register").map(_._2)

    // ── 4. 数据校验 ──
    val validatedBehavior = behaviorStream.transform(rdd => DataValidator.validateBehavior(rdd))
    val validatedRegister = registerStream.transform(rdd => DataValidator.validateRegister(rdd))
    // 内容元数据校验后写入 MySQL content_metadata 表
    metadataStream.foreachRDD { rdd =>
      val valid = DataValidator.validateMetadata(rdd)
      if (!valid.isEmpty()) {
        MySQLBatchWriter.writeContentMetadata(valid)
        println(s"[元数据] 校验通过并写入: ${valid.count()} 条")
      }
    }

    // ── 5. 实时聚合（三个并行管线） ──
    val userProfileRDD   = UserProfileAgg.aggregate(validatedBehavior)   // 用户画像
    val contentHotRDD    = ContentHotStats.compute(validatedBehavior)     // 内容热度
    val clusterResultRDD = ColdStartCluster.cluster(validatedRegister)    // 冷启动聚类

    // ── 6. 写入 MySQL ──
    userProfileRDD.foreachRDD { rdd =>
      if (!rdd.isEmpty()) {
        MySQLBatchWriter.writeUserProfile(rdd)
        println(s"[用户画像] 写入 ${rdd.count()} 条")
      }
    }

    contentHotRDD.foreachRDD { rdd =>
      if (!rdd.isEmpty()) {
        MySQLBatchWriter.writeContentHot(rdd)
        println(s"[内容热度] 写入 ${rdd.count()} 条")
      }
    }

    clusterResultRDD.foreachRDD { rdd =>
      if (!rdd.isEmpty()) {
        MySQLBatchWriter.writeColdStartCluster(rdd)
        println(s"[冷启动聚类] 写入 ${rdd.count()} 条")
      }
    }

    // ── 7. 启动 StreamingContext ──
    ssc.start()
    println("=" * 60)
    println("  Spark Streaming 实时分析已启动")
    println(s"  Kafka 地址: $bootstrapServers")
    println("  消费主题: user_behavior, content_metadata, user_register")
    val mysqlUrl = cfg.getString("mysql.url")
    println(s"  MySQL 地址: $mysqlUrl")
    println("=" * 60)
    ssc.awaitTermination()
  }
}
