package com.recommend.streaming

import com.typesafe.config.ConfigFactory
import org.apache.spark.rdd.RDD
import java.sql.{Connection, DriverManager, PreparedStatement, Timestamp}

/**
 * MySQL 批量写入器 — 将实时聚合结果写入 rt_* 表
 *
 * 支持三张实时表:
 * - rt_user_profile: 用户画像（15 列）
 * - rt_content_hot: 内容热度（11 列）
 * - rt_coldstart_cluster: 冷启动聚类（8 列，主键冲突时更新）
 *
 * 使用 JDBC 批量提交（每 500 条一批），每个分区独立获取连接。
 */
object MySQLBatchWriter extends Serializable {

  // 从配置文件读取 MySQL 连接参数
  private val cfg   = ConfigFactory.load().getConfig("mysql")
  private val jdbcUrl = cfg.getString("url") +
    "?useSSL=false&rewriteBatchedStatements=true&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true"
  private val dbUser  = cfg.getString("user")
  private val dbPass  = cfg.getString("password")
  private val batchSize = 500  // 批量提交阈值

  /**
   * 将用户画像 RDD 批量写入 rt_user_profile 表
   *
   * 窗口级别的用户行为聚合，包含播放次数、各项比率、偏好分布、冷启动标记等。
   */
  def writeUserProfile(rdd: RDD[UserProfile]): Unit = {
    rdd.foreachPartition { iter =>
      if (iter.nonEmpty) {
        val conn = getConnection()
        try {
          val sql =
            """INSERT INTO rt_user_profile
              |  (user_id, window_start, window_end, play_count, completion_rate,
              |   like_rate, favorite_rate, skip_rate, share_count, comment_count,
              |   preference_distribution, active_hours, is_cold_start, behavior_count, content_type_ratio)
              |VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """.stripMargin
          val ps = conn.prepareStatement(sql)
          var count = 0
          iter.foreach { p =>
            ps.setLong(1, p.userId)
            ps.setTimestamp(2, new Timestamp(p.windowStart))
            ps.setTimestamp(3, new Timestamp(p.windowEnd))
            ps.setInt(4, p.playCount)
            ps.setDouble(5, p.completionRate)
            ps.setDouble(6, p.likeRate)
            ps.setDouble(7, p.favoriteRate)
            ps.setDouble(8, p.skipRate)
            ps.setInt(9, p.shareCount)
            ps.setInt(10, p.commentCount)
            ps.setString(11, p.preferenceDistribution)
            ps.setString(12, p.activeHours)
            ps.setInt(13, if (p.isColdStart) 1 else 0)
            ps.setInt(14, p.behaviorCount)
            ps.setString(15, p.contentTypeRatio)
            ps.addBatch()
            count += 1
            if (count >= batchSize) {
              ps.executeBatch()
              count = 0
            }
          }
          if (count > 0) ps.executeBatch()  // 提交剩余批次
          ps.close()
        } finally {
          conn.close()
        }
      }
    }
  }

  /**
   * 将内容热度 RDD 批量写入 rt_content_hot 表
   *
   * 1 分钟滚动窗口统计的内容热度数据。
   */
  def writeContentHot(rdd: RDD[ContentHot]): Unit = {
    rdd.foreachPartition { iter =>
      if (iter.nonEmpty) {
        val conn = getConnection()
        try {
          val sql =
            """INSERT INTO rt_content_hot
              |  (content_id, content_type, play_count, like_count, favorite_count,
              |   share_count, completion_rate, interaction_rate, hot_score, window_start, window_end)
              |VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """.stripMargin
          val ps = conn.prepareStatement(sql)
          var count = 0
          iter.foreach { h =>
            ps.setLong(1, h.contentId)
            ps.setString(2, h.contentType)
            ps.setLong(3, h.playCount)
            ps.setLong(4, h.likeCount)
            ps.setLong(5, h.favoriteCount)
            ps.setLong(6, h.shareCount)
            ps.setDouble(7, h.completionRate)
            ps.setDouble(8, h.interactionRate)
            ps.setDouble(9, h.hotScore)
            ps.setTimestamp(10, new Timestamp(h.windowStart))
            ps.setTimestamp(11, new Timestamp(h.windowEnd))
            ps.addBatch()
            count += 1
            if (count >= batchSize) {
              ps.executeBatch()
              count = 0
            }
          }
          if (count > 0) ps.executeBatch()
          ps.close()
        } finally {
          conn.close()
        }
      }
    }
  }

  /**
   * 将冷启动聚类结果 RDD 写入 rt_coldstart_cluster 表
   *
   * 使用 INSERT ... ON DUPLICATE KEY UPDATE 实现幂等写入，
   * 同一用户再次聚类时自动更新簇归属和簇中心。
   */
  def writeColdStartCluster(rdd: RDD[ClusterResult]): Unit = {
    rdd.foreachPartition { iter =>
      if (iter.nonEmpty) {
        val conn = getConnection()
        try {
          val sql =
            """INSERT INTO rt_coldstart_cluster
              |  (user_id, cluster_id, cluster_center, cluster_size,
              |   device_type, register_channel, interest_tags, compute_time)
              |VALUES (?, ?, ?, ?, ?, ?, ?, ?)
              |ON DUPLICATE KEY UPDATE
              |  cluster_id = VALUES(cluster_id), cluster_center = VALUES(cluster_center),
              |  cluster_size = VALUES(cluster_size), compute_time = VALUES(compute_time)
            """.stripMargin
          val ps = conn.prepareStatement(sql)
          var count = 0
          iter.foreach { c =>
            ps.setLong(1, c.userId)
            ps.setInt(2, c.clusterId)
            ps.setString(3, c.clusterCenter)
            ps.setInt(4, c.clusterSize)
            ps.setString(5, c.deviceType)
            ps.setString(6, c.registerChannel)
            ps.setString(7, c.interestTags)
            ps.setTimestamp(8, new Timestamp(c.computeTime))
            ps.addBatch()
            count += 1
            if (count >= batchSize) {
              ps.executeBatch()
              count = 0
            }
          }
          if (count > 0) ps.executeBatch()
          ps.close()
        } finally {
          conn.close()
        }
      }
    }
  }

  /** 获取 MySQL 数据库连接 */
  private def getConnection(): Connection = {
    Class.forName("com.mysql.cj.jdbc.Driver")
    DriverManager.getConnection(jdbcUrl, dbUser, dbPass)
  }
}
