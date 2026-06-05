package com.recommend.producer

import com.typesafe.config.ConfigFactory
import org.apache.kafka.clients.producer.{KafkaProducer, ProducerRecord}

import java.util.Properties

/**
 * 用户行为生产者 — 持续生成用户行为事件流并发送到 Kafka
 *
 * 以可配置的速率（默认 100 条/秒）持续发送用户行为事件（播放、点赞、收藏、分享、跳过等），
 * 可配置运行时长（默认 60 分钟），写入 Kafka Topic: user_behavior
 */
object UserBehaviorProducer {

  def main(args: Array[String]): Unit = {
    val config          = ConfigFactory.load()
    val topic           = config.getString("kafka.topic.user-behavior")
    val eventsPerSecond = config.getInt("producer.events.per-second")
    val durationMinutes = config.getInt("producer.duration.minutes")
    val totalEvents     = eventsPerSecond * durationMinutes * 60

    val props    = baseProps(config)
    val producer = new KafkaProducer[String, String](props)

    println(s"[开始] 正在生成 $totalEvents 条行为事件 (${eventsPerSecond}条/秒, 持续${durationMinutes}分钟) → $topic")

    var sent      = 0
    val startTime = System.currentTimeMillis()

    try {
      while (sent < totalEvents) {
        val tickStart = System.currentTimeMillis()
        var tickCount = 0

        // 每秒发送固定数量的事件
        while (tickCount < eventsPerSecond && sent < totalEvents) {
          val json = MockDataGenerator.generateUserBehavior()
          producer.send(new ProducerRecord[String, String](topic, json))
          tickCount += 1
          sent += 1
        }

        // 每 10 秒输出一次进度（速率 = 已发送 / 已用时间）
        if (sent % (eventsPerSecond * 10) == 0 || sent == totalEvents) {
          val elapsed = (System.currentTimeMillis() - startTime) / 1000.0
          val rate    = if (elapsed > 0) sent / elapsed else 0
          println(f"[进度] $sent/$totalEvents (${sent * 100.0 / totalEvents}%.1f%%), 速率=${rate}%.1f 条/秒")
        }

        // 补偿睡眠时间，保持恒定每秒速率
        val tickDuration = System.currentTimeMillis() - tickStart
        val sleepTime    = 1000L - tickDuration
        if (sleepTime > 0) Thread.sleep(sleepTime)
      }
    } catch {
      case e: Exception =>
        System.err.println(s"[错误] 发送消息失败: ${e.getMessage}")
        System.err.println("请确认 Kafka 已启动 (node1:9092)")
    } finally {
      producer.close()
      println(s"[完成] 已发送 $sent 条行为事件到 $topic")
    }
  }

  /**
   * 构建 Kafka 生产者配置
   *
   * @param config Typesafe Config 对象
   * @return Kafka 生产者配置属性
   */
  private def baseProps(config: com.typesafe.config.Config): Properties = {
    val props = new Properties()
    props.put("bootstrap.servers", config.getString("kafka.bootstrap.servers"))
    props.put("acks", config.getString("kafka.acks"))
    props.put("retries", config.getInt("kafka.retries").toString)
    props.put("batch.size", config.getInt("kafka.batch.size").toString)
    props.put("linger.ms", config.getInt("kafka.linger.ms").toString)
    props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer")
    props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer")
    props.put("compression.type", "snappy")
    props
  }
}
