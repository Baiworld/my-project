package com.recommend.producer

import com.typesafe.config.ConfigFactory
import org.apache.kafka.clients.producer.{KafkaProducer, ProducerRecord}

import java.util.Properties

/**
 * 用户注册生产者 — 批量生成用户注册数据并发送到 Kafka
 *
 * 一次性运行，生成约 10000 条用户注册记录（姓名、年龄组、性别、地区、渠道等），
 * 写入 Kafka Topic: user_register
 */
object UserRegisterProducer {

  def main(args: Array[String]): Unit = {
    val config    = ConfigFactory.load()
    val topic     = config.getString("kafka.topic.user-register")
    val userCount = config.getInt("producer.users.count")

    val props    = baseProps(config)
    val producer = new KafkaProducer[String, String](props)

    println(s"[开始] 正在生成 $userCount 条用户注册数据 → $topic")

    try {
      var sent = 0

      for (id <- MockDataGenerator.userIds) {
        val json = MockDataGenerator.generateUserRegister(id)
        producer.send(new ProducerRecord[String, String](topic, json))
        sent += 1
        if (sent % 1000 == 0) println(f"[进度] $sent/$userCount 条注册记录")
      }

      producer.flush()
    } catch {
      case e: Exception =>
        System.err.println(s"[错误] 发送消息失败: ${e.getMessage}")
        System.err.println("请确认 Kafka 已启动 (node1:9092)")
    } finally {
      producer.close()
      println(s"[完成] 已发送 $userCount 条用户注册数据到 $topic")
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
