#!/bin/bash
# ============================================================================
# pipeline.sh — 一键启停整个数据管道
#
# 用法:
#   ./pipeline.sh start        # 启动 Kafka → Flume → 投喂
#   ./pipeline.sh stop         # 停止 投喂 → Flume → Kafka
#   ./pipeline.sh status       # 查看运行状态
# ============================================================================

# ── 路径配置 ──────────────────────────────────────────────────────
KAFKA_HOME="/usr/local/kafka_2.13-3.3.1"
FLUME_HOME="/usr/local/flume"
FLUME_CONF="$FLUME_HOME/job/flume-pipeline.conf"
DATA_DIR="/export/data/mock_data_BD2"
OUTPUT_DIR="/export/data/BD2_data"
BOOTSTRAP_SERVER="node1:9092"

# ── Kafka 启动/停止 ────────────────────────────────────────────────
init_dirs() {
    mkdir -p "$OUTPUT_DIR/logs" "$OUTPUT_DIR/.pids"
}

start_kafka() {
    echo "[1/3] 启动 Kafka..."

    if jps | grep -q Kafka; then
        echo "  Kafka 已在运行"
        return 0
    fi

    cd "$KAFKA_HOME"
    setsid ./bin/kafka-server-start.sh ./config/kraft/server.properties > /tmp/kafka.log 2>&1 &
    sleep 3

    if ./bin/kafka-broker-api-versions.sh --bootstrap-server "$BOOTSTRAP_SERVER" &>/dev/null; then
        echo "  ✓ Kafka 启动成功"
    else
        echo "  ✗ Kafka 启动失败"
        return 1
    fi
}

stop_kafka() {
    echo "[3/3] 停止 Kafka..."
    local pid=$(jps | grep Kafka | awk '{print $1}')
    if [ -n "$pid" ]; then
        kill "$pid"
        sleep 2
        echo "  ✓ Kafka 已停止"
    else
        echo "  Kafka 未在运行"
    fi
}

init_topics() {
    echo "[2/4] 创建 Kafka Topics..."
    $KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" --create \
        --topic user_behavior   --partitions 3 --replication-factor 1 --if-not-exists 2>/dev/null
    $KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" --create \
        --topic content_metadata --partitions 2 --replication-factor 1 --if-not-exists 2>/dev/null
    $KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" --create \
        --topic user_register    --partitions 2 --replication-factor 1 --if-not-exists 2>/dev/null
    echo "  ✓ Topics 就绪"
}

# ── Flume 启动/停止 ────────────────────────────────────────────────
start_flume() {
    echo "[3/4] 启动 Flume Agent..."

    if [ ! -f "$FLUME_CONF" ]; then
        echo "  ✗ 配置文件不存在: $FLUME_CONF"
        return 1
    fi

    # 停掉旧实例
    pkill -f "flume-pipeline.conf" 2>/dev/null || true
    sleep 1

    nohup $FLUME_HOME/bin/flume-ng agent \
        -n a1 \
        -c $FLUME_HOME/conf \
        -f "$FLUME_CONF" \
        -Dflume.root.logger=INFO,console \
        > "$OUTPUT_DIR/logs/flume.log" 2>&1 &

    sleep 2
    echo "  ✓ Flume 已启动 (PID: $!)"
}

stop_flume() {
    echo "[2/3] 停止 Flume..."
    pkill -f "flume-pipeline.conf" 2>/dev/null && echo "  ✓ Flume 已停止" || echo "  Flume 未在运行"
}

# ── 投喂脚本 启动/停止 ────────────────────────────────────────────
start_feed() {
    echo "[4/4] 启动数据投喂..."
    bash "$DATA_DIR/feed_data.sh" start
}

stop_feed() {
    echo "[1/3] 停止数据投喂..."
    bash "$DATA_DIR/feed_data.sh" stop
}

# ── 状态查看 ──────────────────────────────────────────────────────
show_status() {
    echo "=============================================="
    echo "  数据管道 — 运行状态"
    echo "=============================================="

    echo ""
    echo "  Kafka:"
    local kafka_pid=$(jps 2>/dev/null | grep Kafka | awk '{print $1}')
    if [ -n "$kafka_pid" ]; then
        echo "    状态: 运行中 (PID: $kafka_pid)"
        echo "    Broker: $BOOTSTRAP_SERVER"
    else
        echo "    状态: 未运行"
    fi

    echo ""
    echo "  Flume:"
    local flume_pid=$(pgrep -f "flume-pipeline.conf" 2>/dev/null)
    if [ -n "$flume_pid" ]; then
        echo "    状态: 运行中 (PID: $flume_pid)"
        echo "    配置: $FLUME_CONF"
    else
        echo "    状态: 未运行"
    fi

    echo ""
    echo "  投喂进度:"
    bash "$DATA_DIR/feed_data.sh" status 2>/dev/null || echo "    投喂脚本未启动"

    echo ""
    echo "  输出文件:"
    ls -lh "$OUTPUT_DIR"/*.log 2>/dev/null || echo "    (暂无)"
}

# ============================================================
case "${1:-}" in
    start)
        echo "=============================================="
        echo "  数据管道 — 启动"
        echo "=============================================="
        echo ""
        init_dirs
        start_kafka || exit 1
        echo ""
        init_topics
        echo ""
        start_flume  || exit 1
        echo ""
        start_feed
        echo ""
        echo "=============================================="
        echo "  管道启动完成"
        echo "=============================================="
        echo "  管理命令:"
        echo "    $0 status     查看状态"
        echo "    $0 stop       停止管道"
        echo "    tail -f $OUTPUT_DIR/logs/flume.log  查看Flume日志"
        ;;

    stop)
        echo "=============================================="
        echo "  数据管道 — 停止"
        echo "=============================================="
        echo ""
        stop_feed
        echo ""
        stop_flume
        echo ""
        stop_kafka
        echo ""
        echo "=============================================="
        echo "  管道已完全停止"
        echo "=============================================="
        ;;

    status)
        show_status
        ;;

    *)
        echo "用法: $0 {start|stop|status}"
        echo ""
        echo "  start   — 依次启动 Kafka → Flume → 数据投喂"
        echo "  stop    — 依次停止 数据投喂 → Flume → Kafka"
        echo "  status  — 查看各组件运行状态"
        exit 1
        ;;
esac
