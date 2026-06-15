package com.recommend.streaming

import com.fasterxml.jackson.databind.{DeserializationFeature, ObjectMapper}
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.typesafe.config.ConfigFactory
import org.apache.kafka.clients.producer.{KafkaProducer, ProducerRecord}
import org.apache.spark.rdd.RDD
import java.util.Properties
import scala.collection.mutable
import scala.util.{Failure, Success, Try}

/**
 * FR-02 数据校验器 — JSON解析、字段校验、去重、死信路由
 *
 * 对 Kafka 消费的原始 JSON 字符串执行:
 * 1. JSON 解析 — 非法 JSON 入死信队列
 * 2. 必填字段校验 — user_id / content_id / event_type 缺失时入死信队列
 * 3. 去重 — (user_id, content_id, event_type) 在 60 秒窗口内去重
 * 4. 死信路由 — 无效消息写入 user_behavior_dlq Topic
 */
object DataValidator extends Serializable {

  private val validEventTypes = Set("play", "like", "favorite", "comment", "skip", "complete", "share")
  private val validContentTypes = Set("music", "video")

  private val mapper = new ObjectMapper()
    .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
    .registerModule(DefaultScalaModule)

  // ── 死信队列 Producer (懒加载，避免序列化问题) ──
  @transient private var dlqProducer: KafkaProducer[String, String] = _

  /** 获取或初始化死信队列生产者 */
  private def getDlqProducer(): KafkaProducer[String, String] = {
    if (dlqProducer == null) {
      val props = new Properties()
      val cfg = ConfigFactory.load()
      props.put("bootstrap.servers", cfg.getString("kafka.bootstrap.servers"))
      props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer")
      props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer")
      dlqProducer = new KafkaProducer[String, String](props)
    }
    dlqProducer
  }

  /** 发送消息到死信队列，附带失败原因和时间戳 */
  private def sendToDlq(originalJson: String, reason: String, sourceTopic: String): Unit = {
    Try {
      val dlqMsg = s"""{"original_message":${originalJson},"error_reason":"${reason}","error_time":"${java.time.Instant.now}","source_topic":"${sourceTopic}"}"""
      val future = getDlqProducer().send(new ProducerRecord[String, String]("user_behavior_dlq", dlqMsg))
      // 异步获取发送结果，失败时输出日志
      future.get()
    } match {
      case Success(_) => // sent OK
      case Failure(e) => println(s"[DLQ] Failed to send dead-letter message: ${e.getMessage}")
    }
  }

  /** 关闭死信队列生产者，释放连接资源 */
  def closeDlqProducer(): Unit = {
    if (dlqProducer != null) {
      Try(dlqProducer.close())
      dlqProducer = null
      println("[DLQ] Producer closed")
    }
  }

  /**
   * 解析并校验用户行为事件
   *
   * 校验规则: JSON 可解析 → user_id > 0 → content_id > 0 → event_type 在白名单 → event_time 合法
   * 去重规则: (user_id, content_id, event_type) 组合每 60 秒窗口内只保留一次
   */
  def validateBehavior(rdd: RDD[String]): RDD[UserBehaviorEvent] = {
    rdd.mapPartitions { iter =>
      val now = System.currentTimeMillis()
      val seen = mutable.Set.empty[String] // 分区内去重集合

      iter.flatMap { json =>
        // 1. JSON 解析
        val node = Try(mapper.readTree(json)).toOption
        if (node.isEmpty) {
          sendToDlq(json, "parse_error", "user_behavior")
          None
        } else {
          val n = node.get

          // 2. 必填字段校验
          val userId = Option(n.get("user_id")).map(_.asLong()).getOrElse(-1L)
          val contentId = Option(n.get("content_id")).map(_.asLong()).getOrElse(-1L)
          val eventType = Option(n.get("event_type")).map(_.asText()).getOrElse("")
          val eventTime = Option(n.get("event_time")).flatMap(t => parseISO8601(t.asText())).getOrElse(-1L)

          if (userId <= 0 || contentId <= 0 || !validEventTypes.contains(eventType) || eventTime < 0) {
            sendToDlq(json, "missing_or_invalid_field", "user_behavior")
            None
          } else {
            // 3. 去重: (user_id, content_id, event_type) 组合
            val dedupKey = s"${userId}_${contentId}_${eventType}"
            if (seen.contains(dedupKey)) {
              None
            } else {
              seen.add(dedupKey)
              Some(UserBehaviorEvent(
                eventId        = Option(n.get("event_id")).map(_.asText()).getOrElse(""),
                userId         = userId,
                contentId      = contentId,
                contentType    = Option(n.get("content_type")).map(_.asText()).filter(validContentTypes).getOrElse("music"),
                eventType      = eventType,
                eventTime      = eventTime,
                duration       = Option(n.get("duration")).map(_.asDouble()).getOrElse(0.0),
                progress       = Option(n.get("progress")).map(_.asDouble()).getOrElse(0.0),
                deviceType     = Option(n.get("device_type")).map(_.asText()).getOrElse("unknown"),
                osVersion      = Option(n.get("os_version")).map(_.asText()).getOrElse(""),
                appVersion     = Option(n.get("app_version")).map(_.asText()).getOrElse(""),
                channel        = Option(n.get("channel")).map(_.asText()).getOrElse(""),
                sessionId      = Option(n.get("session_id")).map(_.asText()).getOrElse(""),
                region         = Option(n.get("region")).map(_.asText()).getOrElse(""),
                source         = Option(n.get("source")).map(_.asText()).getOrElse(""),
                sourceStrategy = Option(n.get("source_strategy")).map(_.asText()).getOrElse(""),
                sourceRank     = Option(n.get("source_rank")).map(_.asInt()).getOrElse(0),
                extra          = parseExtra(n.get("extra"))
              ))
            }
          }
        }
      }
    }
  }

  /** 解析并校验用户注册事件 — user_id 必须大于 0，注册时间默认当前时间 */
  def validateRegister(rdd: RDD[String]): RDD[UserRegisterEvent] = {
    rdd.flatMap { json =>
      val node = Try(mapper.readTree(json)).toOption
      node.flatMap { n =>
        val userId = Option(n.get("user_id")).map(_.asLong()).getOrElse(-1L)
        if (userId <= 0) {
          sendToDlq(json, "missing_user_id", "user_register")
          None
        } else {
          Some(UserRegisterEvent(
            userId          = userId,
            registerTime    = Option(n.get("register_time")).flatMap(t => parseISO8601(t.asText())).getOrElse(System.currentTimeMillis()),
            deviceType      = Option(n.get("device_type")).map(_.asText()).getOrElse("unknown"),
            osVersion       = Option(n.get("os_version")).map(_.asText()).getOrElse(""),
            registerChannel = Option(n.get("register_channel")).map(_.asText()).getOrElse(""),
            interestTags    = Option(n.get("interest_tags")).map(parseArray).getOrElse(Seq.empty),
            region          = Option(n.get("region")).map(_.asText()).getOrElse(""),
            ageGroup        = Option(n.get("age_group")).map(_.asText()).getOrElse("unknown"),
            gender          = Option(n.get("gender")).map(_.asText()).getOrElse("unknown")
          ))
        }
      }
    }
  }

  /** 解析内容元数据 — content_id 必须大于 0，缺少 content_type 默认 "music" */
  def validateMetadata(rdd: RDD[String]): RDD[ContentMetaEvent] = {
    rdd.flatMap { json =>
      val node = Try(mapper.readTree(json)).toOption
      node.flatMap { n =>
        val contentId = Option(n.get("content_id")).map(_.asLong()).getOrElse(-1L)
        if (contentId <= 0) {
          sendToDlq(json, "missing_content_id", "content_metadata")
          None
        } else {
          Some(ContentMetaEvent(
            contentId       = contentId,
            contentType     = Option(n.get("content_type")).map(_.asText()).getOrElse("music"),
            title           = Option(n.get("title")).map(_.asText()).getOrElse(""),
            artistOrAuthor  = Option(n.get("artist_or_author")).map(_.asText()).getOrElse(""),
            styleOrCategory = Option(n.get("style_or_category")).map(_.asText()).getOrElse(""),
            tags            = Option(n.get("tags")).map(parseArray).getOrElse(Seq.empty),
            duration        = Option(n.get("duration")).map(_.asDouble()).getOrElse(0.0),
            language        = Option(n.get("language")).map(_.asText()).getOrElse(""),
            bpm             = Option(n.get("bpm")).map(_.asDouble()).getOrElse(0.0),
            releaseDate     = Option(n.get("release_date")).map(_.asText()).getOrElse(""),
            action          = Option(n.get("action")).map(_.asText()).getOrElse("create")
          ))
        }
      }
    }
  }

  // ── 工具方法 ──

  /** 解析 ISO8601 时间字符串为毫秒时间戳 */
  private def parseISO8601(text: String): Option[Long] = {
    Try(java.time.Instant.parse(text).toEpochMilli).toOption.orElse(
      Try(java.time.LocalDateTime.parse(text.take(19).replace("T", "T"))
        .atZone(java.time.ZoneId.of("UTC")).toInstant.toEpochMilli).toOption
    )
  }

  /** 解析 JSON 数组为字符串序列 */
  private def parseArray(node: com.fasterxml.jackson.databind.JsonNode): Seq[String] = {
    if (node == null || !node.isArray) Seq.empty
    else {
      import scala.collection.JavaConverters._
      node.elements().asScala.map(_.asText()).toSeq
    }
  }

  /** 解析 JSON 对象为键值对 Map */
  private def parseExtra(node: com.fasterxml.jackson.databind.JsonNode): Map[String, String] = {
    if (node == null || !node.isObject) Map.empty
    else {
      import scala.collection.JavaConverters._
      node.fields().asScala.map(e => e.getKey -> e.getValue.asText()).toMap
    }
  }
}
