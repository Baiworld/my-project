#!/bin/bash
# ============================================================================
# start_pipeline.sh — 一键启动整个数据管道
#
# 用法:
#   ./start_pipeline.sh
#
# 启动顺序:
#   1. 检查 Kafka 是否运行
#   2. 创建 Topics（如不存在）
#   3. 启动 Flume
#   4. 启动逐行投喂脚本
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FLUME_HOME="/usr/local/flume"
FLUME_CONF="$FLUME_HOME/job/flume-pipeline.conf"
FLUME_LOG="/export/data/BD2_data/logs/flume.log"
KAFKA_HOME="${KAFKA_HOME:-/opt/kafka}"

echo "=============================================="
echo "  冷启动推荐系统 — 数据管道启动"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# ── Step 1: 检查 Kafka ──
echo ""
echo "[1/4] 检查 Kafka 连通性..."
if $KAFKA_HOME/bin/kafka-broker-api-versions.sh --bootstrap-server node1:9092 &>/dev/null; then
    echo "  ✓ Kafka Broker 可用 (node1:9092)"
else
    echo "  ✗ 无法连接 Kafka。请先启动 Kafka。"
    exit 1
fi

# ── Step 2: 初始化 Topics ──
echo ""
echo "[2/4] 初始化 Kafka Topics..."
bash "$SCRIPT_DIR/init_kafka.sh" create

# ── Step 3: 启动 Flume ──
echo ""
echo "[3/4] 启动 Flume Agent..."

if [ ! -f "$FLUME_CONF" ]; then
    echo "  ✗ Flume 配置文件不存在: $FLUME_CONF"
    exit 1
fi

# 先停掉旧的 Flume
pkill -f "flume-pipeline.conf" 2>/dev/null || true
sleep 1

nohup $FLUME_HOME/bin/flume-ng agent \
    -n a1 \
    -c $FLUME_HOME/conf \
    -f "$FLUME_CONF" \
    -Dflume.root.logger=INFO,console \
    > "$FLUME_LOG" 2>&1 &

FLUME_PID=$!
echo "  ✓ Flume 已启动 (PID: $FLUME_PID)"
echo "  日志: $FLUME_LOG"

# ── Step 4: 启动投喂脚本 ──
echo ""
echo "[4/4] 启动逐行投喂..."
bash "$SCRIPT_DIR/feed_data.sh" start

# ── 完成 ──
echo ""
echo "=============================================="
echo "  数据管道启动完成!"
echo "=============================================="
echo ""
echo "  组件状态:"
echo "    Kafka    — localhost:9092"
echo "    Flume    — PID: $FLUME_PID"
echo "    投喂脚本  — 3个后台进程"
echo ""
echo "  管理命令:"
echo "    $SCRIPT_DIR/feed_data.sh status  查看投喂进度"
echo "    $SCRIPT_DIR/stop_pipeline.sh     停止整个管道"
echo "    tail -f $FLUME_LOG              查看 Flume 日志"
