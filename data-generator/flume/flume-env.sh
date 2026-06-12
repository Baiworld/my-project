#!/bin/bash
# ============================================================================
# Flume 环境变量配置
# 复制到 $FLUME_HOME/conf/ 或通过 --conf 参数指定
# ============================================================================

# Java 环境（按实际路径修改）
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-11-openjdk}"
export JAVA_OPTS="-Xms512m -Xmx1024m -Dflume.root.logger=INFO,console"

# Flume 类路径扩展（Kafka Sink 依赖）
# 确保以下 jar 已放入 $FLUME_HOME/lib/ 或 plugins.d/ 目录：
#   - flume-kafka-sink-*.jar
#   - kafka-clients-3.3.1.jar
#   - snappy-java-*.jar
