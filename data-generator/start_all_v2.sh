#!/bin/bash
# ============================================================================
# start_all_v2.sh — 虚拟机端一键启停全部服务
#
# 启动: Kafka → Flume → 持续数据生成
# 停止: 数据生成 → Flume → Kafka
#
# 用法:
#   bash start_all_v2.sh              # 启动全部 (默认每秒 3 条)
#   bash start_all_v2.sh 10           # 启动全部, 每秒 10 条
#   bash start_all_v2.sh stop         # 关闭全部
#   bash start_all_v2.sh status       # 查看状态
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 路径配置 ──
KAFKA_HOME="${KAFKA_HOME:-/usr/local/kafka_2.13-3.3.1}"
KAFKA_CONFIG="${KAFKA_HOME}/config/kraft/server.properties"
KAFKA_BOOTSTRAP="localhost:9092"

FLUME_HOME="${FLUME_HOME:-/usr/local/flume}"
FLUME_CONF_DIR="${SCRIPT_DIR}/flume"
FLUME_AGENT_NAME="agent"

OUTPUT_DIR="/opt/data-generator/output"

TOPICS=("user_behavior" "content_metadata" "user_register")
TOPIC_PARTITIONS=(3 2 2)

# ── 颜色 ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }

# ============================================================================
# Kafka
# ============================================================================
start_kafka() {
    log_step "启动 Kafka..."
    if ${KAFKA_HOME}/bin/kafka-broker-api-versions.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" &>/dev/null; then
        log_info "  Kafka 已在运行中"
    else
        ${KAFKA_HOME}/bin/kafka-server-start.sh -daemon "${KAFKA_CONFIG}"
        sleep 3
        if ${KAFKA_HOME}/bin/kafka-broker-api-versions.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" &>/dev/null; then
            log_info "  Kafka 启动成功"
        else
            log_error "  Kafka 启动失败"
            return 1
        fi
    fi
    init_topics
}

stop_kafka() {
    log_step "停止 Kafka..."
    ${KAFKA_HOME}/bin/kafka-server-stop.sh 2>/dev/null || true
    sleep 2
    log_info "  Kafka 已停止"
}

init_topics() {
    for i in "${!TOPICS[@]}"; do
        local topic="${TOPICS[$i]}"
        local partitions="${TOPIC_PARTITIONS[$i]}"
        if ${KAFKA_HOME}/bin/kafka-topics.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" --describe --topic "${topic}" &>/dev/null; then
            log_info "  Topic '${topic}' 已存在"
        else
            ${KAFKA_HOME}/bin/kafka-topics.sh --create --bootstrap-server "${KAFKA_BOOTSTRAP}" \
                --topic "${topic}" --partitions "${partitions}" --replication-factor 1
            log_info "  Topic '${topic}' 已创建 (${partitions} 分区)"
        fi
    done
}

# ============================================================================
# Flume
# ============================================================================
start_flume() {
    log_step "启动 Flume..."
    mkdir -p "${OUTPUT_DIR}" "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/pids"

    if pgrep -f "flume.node.Application" > /dev/null; then
        log_info "  Flume 已在运行中"
        return 0
    fi

    nohup "${FLUME_HOME}/bin/flume-ng" agent \
        -n "${FLUME_AGENT_NAME}" \
        -c "${FLUME_CONF_DIR}" \
        -f "${FLUME_CONF_DIR}/flume.conf" \
        -Dflume.root.logger=INFO,console \
        > "${SCRIPT_DIR}/logs/flume.log" 2>&1 &

    local pid=$!
    echo "${pid}" > "${SCRIPT_DIR}/pids/flume.pid"
    log_info "  Flume 已启动 (PID: ${pid})"
}

# ============================================================================
# 持续数据生成
# ============================================================================
start_generator() {
    log_step "启动数据生成 (速率: ${RATE}/秒)..."
    if pgrep -f "generate_data.py.*continuous" > /dev/null; then
        log_info "  已在运行中"
        return 0
    fi

    nohup python3 "${SCRIPT_DIR}/generate_data.py" --continuous --rate "${RATE}" \
        > "${SCRIPT_DIR}/logs/generator.log" 2>&1 &

    local pid=$!
    echo "${pid}" > "${SCRIPT_DIR}/pids/generator.pid"
    log_info "  已启动 (PID: ${pid})"
}

# ============================================================================
# 停止
# ============================================================================
stop_all() {
    # 先停数据生成, 再停 Flume, 最后停 Kafka
    log_step "停止数据生成..."
    if [[ -f "${SCRIPT_DIR}/pids/generator.pid" ]]; then
        kill "$(cat "${SCRIPT_DIR}/pids/generator.pid")" 2>/dev/null || true
        rm -f "${SCRIPT_DIR}/pids/generator.pid"
    fi
    pkill -f "generate_data.py.*continuous" 2>/dev/null || true
    log_info "  数据生成已停止"

    log_step "停止 Flume..."
    if [[ -f "${SCRIPT_DIR}/pids/flume.pid" ]]; then
        kill "$(cat "${SCRIPT_DIR}/pids/flume.pid")" 2>/dev/null || true
        rm -f "${SCRIPT_DIR}/pids/flume.pid"
    fi
    pkill -f "flume.node.Application" 2>/dev/null || true
    log_info "  Flume 已停止"

    stop_kafka
}

# ============================================================================
# 状态
# ============================================================================
show_status() {
    echo ""
    echo "=========================================="
    echo "  数据管道 — 运行状态"
    echo "=========================================="

    echo -n "Kafka:  "
    if ${KAFKA_HOME}/bin/kafka-broker-api-versions.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" &>/dev/null; then
        echo -e "${GREEN}运行中${NC} (${KAFKA_BOOTSTRAP})"
    else
        echo -e "${RED}未运行${NC}"
    fi

    echo -n "Flume:  "
    if pgrep -f "flume.node.Application" > /dev/null; then
        echo -e "${GREEN}运行中${NC} (PID: $(pgrep -f 'flume.node.Application' | head -1))"
    else
        echo -e "${RED}未运行${NC}"
    fi

    echo -n "Generator: "
    if pgrep -f "generate_data.py.*continuous" > /dev/null; then
        echo -e "${GREEN}运行中${NC} (PID: $(pgrep -f 'generate_data.*continuous' | head -1))"
    else
        echo -e "${RED}未运行${NC}"
    fi
    echo ""
}

# ============================================================================
# 主入口
# ============================================================================
RATE="${2:-3}"

case "${1:-start}" in
    stop)
        echo ""
        log_info "关闭所有服务..."
        echo ""
        stop_all
        echo ""
        log_info "全部已关闭"
        echo ""
        ;;
    status)
        show_status
        ;;
    *)
        echo ""
        echo "=========================================="
        echo "  推荐系统 — 虚拟机端一键启动"
        echo "=========================================="
        echo ""
        start_kafka
        start_flume
        start_generator
        echo ""
        echo "=========================================="
        echo "  全部启动完成！"
        echo "  Kafka : ${KAFKA_BOOTSTRAP}"
        echo "  数据率: ${RATE} 条/秒"
        echo "  日志  : ${SCRIPT_DIR}/logs/"
        echo "  状态  : bash start_all_v2.sh status"
        echo "  停止  : bash start_all_v2.sh stop"
        echo "=========================================="
        echo ""
        ;;
esac
