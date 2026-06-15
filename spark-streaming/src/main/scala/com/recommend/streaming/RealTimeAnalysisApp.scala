package com.recommend.streaming

import com.typesafe.config.ConfigFactory
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.spark.SparkConf
import org.apache.spark.streaming.{Seconds, StreamingContext}
import org.apache.spark.streaming.dstream.DStream
import org.apache.spark.streaming.kafka010.{CanCommitOffsets, ConsumerStrategies, HasOffsetRanges, KafkaUtils, LocationStrategies}

/**
 * Spark Streaming 主入口 — 组装实时分析管线
 *
 * 管线流程:
 * 1. 配置 SparkConf（local 模式 + 背压 + Kryo 序列化）
 * 2. 使用 getOrCreate 从 checkpoint 恢复，避免重启丢失状态
 * 3. 从 Kafka 消费 3 个 Topic（user_behavior / content_metadata / user_register）
 * 4. 按 Topic 分流
 * 5. 数据校验（DataValidator — JSON 解析 + 去重 + 死信路由）
 * 6. 实时聚合（用户画像 / 内容热度 / 冷启动聚类）
 * 7. 批量写入 MySQL（rt_user_profile / rt_content_hot / rt_coldstart_cluster）
 * 8. 提交 Kafka offset，避免重启全量重放
 * 9. 启动 StreamingContext 等待终止
 */
object RealTimeAnalysisApp {

  def main(args: Array[String]): Unit = {

    val cfg = ConfigFactory.load()
    val bootstrapServers = cfg.getString("kafka.bootstrap.servers")
    val groupId = if (cfg.hasPath("kafka.group.id")) cfg.getString("kafka.group.id") else "hybrid_rec_streaming"
    val ckptPath = if (cfg.hasPath("spark.checkpoint.path")) cfg.getString("spark.checkpoint.path") else "checkpoints/streaming-v2"

    // ── StreamingContext 工厂函数（首次运行或 checkpoint 不存在时调用） ──
    def createContext(): StreamingContext = {
      val conf = new SparkConf()
        .setAppName("HybridRecSys-Streaming")
        .setMaster("local[*]")
        .set("spark.sql.shuffle.partitions", "8")
        .set("spark.streaming.backpressure.enabled", "true")
        .set("spark.streaming.kafka.maxRatePerPartition", "500")
        .set("spark.streaming.stopGracefullyOnShutdown", "true")
        .set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")

      val ssc = new StreamingContext(conf, Seconds(10))
      ssc.checkpoint(ckptPath)

      // ── Kafka 消费配置 ──
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

      // ── 创建 Kafka DStream ──
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

      // ── 数据校验 ──
      val validatedBehavior = behaviorStream.transform(rdd => DataValidator.validateBehavior(rdd))
      val validatedRegister = registerStream.transform(rdd => DataValidator.validateRegister(rdd))

      metadataStream.foreachRDD { rdd =>
        val valid = DataValidator.validateMetadata(rdd)
        if (!valid.isEmpty()) {
          MySQLBatchWriter.writeContentMetadata(valid)
          println(s"[元数据] 校验通过并写入: ${valid.count()} 条")
        }
      }

      // ── 实时聚合（三个并行管线） ──
      val userProfileRDD   = UserProfileAgg.aggregate(validatedBehavior)
      val contentHotRDD    = ContentHotStats.compute(validatedBehavior)
      val clusterResultRDD = ColdStartCluster.cluster(validatedRegister)

      // ── 写入 MySQL ──
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

      // ── 提交 Kafka offset（所有处理完成后，避免重启全量重放） ──
      kafkaStream.foreachRDD { rdd =>
        val offsetRanges = rdd.asInstanceOf[HasOffsetRanges].offsetRanges
        kafkaStream.asInstanceOf[CanCommitOffsets].commitAsync(offsetRanges)
      }

      // ── 优雅关闭：释放 DLQ Producer 等资源 ──
      sys.addShutdownHook {
        DataValidator.closeDlqProducer()
      }

      println("=" * 60)
      println("  Spark Streaming 实时分析已启动")
      println(s"  Kafka 地址: $bootstrapServers")
      println(s"  消费组: $groupId")
      println("  消费主题: user_behavior, content_metadata, user_register")
      val mysqlUrl = cfg.getString("mysql.url")
      println(s"  MySQL 地址: $mysqlUrl")
      println(s"  Checkpoint: $ckptPath")
      println("=" * 60)

      ssc
    }

    // ── 使用 getOrCreate 恢复或创建 StreamingContext ──
    val ssc = StreamingContext.getOrCreate(ckptPath, () => createContext())

    ssc.start()
    ssc.awaitTermination()
  }
}
