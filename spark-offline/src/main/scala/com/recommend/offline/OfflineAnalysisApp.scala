package com.recommend.offline

import org.apache.spark.SparkConf
import org.apache.spark.sql.SparkSession

/**
 * SparkSQL 离线批处理主入口 — 根据 job 参数调度各子任务
 *
 * 支持的作业:
 * - portrait:   用户全量画像构建 (FR-06)
 * - als-train:  ALS 协同过滤模型训练
 * - recommend:  混合推荐结果生成 (FR-08)
 * - metrics:    推荐效果指标计算 (FR-09)
 * - all:        按顺序执行上述全部作业
 */
object OfflineAnalysisApp {

  def main(args: Array[String]): Unit = {

    val job = if (args.nonEmpty) args(0) else "all"

    val conf = new SparkConf()
      .setAppName("HybridRecSys-Offline")
      .setMaster("local[*]")
      .set("spark.sql.shuffle.partitions", "8")
      .set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")

    val spark = SparkSession.builder().config(conf).getOrCreate()

    println("=" * 60)
    println(s"  SparkSQL 离线批处理 — Job: $job")
    println("=" * 60)

    job match {
      case "portrait"     => UserPortraitBuilder.build(spark)
      case "als-train"    => ALSTrainer.train(spark)
      case "recommend"    => HybridRecommender.run(spark)
      case "metrics"      => MetricsCalculator.calculate(spark)
      case "all"          =>
        println("\n[1/4] 构建用户画像...")
        UserPortraitBuilder.build(spark)
        println("\n[2/4] 训练 ALS 模型...")
        ALSTrainer.train(spark)
        println("\n[3/4] 生成混合推荐结果...")
        HybridRecommender.run(spark)
        println("\n[4/4] 计算推荐效果指标...")
        MetricsCalculator.calculate(spark)
      case _ =>
        println(s"未知的 job 参数: $job，可用: portrait | als-train | recommend | metrics | all")
    }

    println("\n" + "=" * 60)
    println(s"  离线批处理作业 '$job' 执行完成")
    println("=" * 60)

    spark.stop()
  }
}
