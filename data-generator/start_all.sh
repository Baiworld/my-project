#!/bin/bash
# ============================================================================
# start_all.sh — 一键启停完整数据管道
#
# 启动: Kafka → Topic初始化 → 数据喂入 → Flume
# 停止: Flume → 数据喂入 → Kafka
#
# 用法:
#   ./start_all.sh start     # 一键启动
#   ./start_all.sh stop      # 一键停止
#   ./start_all.sh status    # 查看状态
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 路径配置（按你的实际路径修改） ──
KAFKA_HOME="${KAFKA_HOME:-/usr/local/kafka_2.13-3.3.1}"
KAFKA_CONFIG="${KAFKA_HOME}/config/kraft/server.properties"
KAFKA_BOOTSTRAP="localhost:9092"
FLUME_HOME="${FLUME_HOME:-/usr/local/flume}"
FLUME_CONF_DIR="${SCRIPT_DIR}/flume"
FLUME_AGENT_NAME="agent"

TOPICS=("user_behavior" "content_metadata" "user_register")
TOPIC_PARTITIONS=(3 2 2)
TOPIC_REPLICATION=1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }

# ============================================================================
# Kafka 启停
# ============================================================================
start_kafka() {
    log_step "启动 Kafka..."

    if ${KAFKA_HOME}/bin/kafka-broker-api-versions.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" &>/dev/null; then
        log_warn "  Kafka 已在运行中"
        return 0
    fi

    nohup "${KAFKA_HOME}/bin/kafka-server-start.sh" "${KAFKA_CONFIG}" > /tmp/kafka.log 2>&1 &
    sleep 3

    if ${KAFKA_HOME}/bin/kafka-broker-api-versions.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" &>/dev/null; then
        log_info "  Kafka 启动成功"
    else
        log_error "  Kafka 启动失败，查看 /tmp/kafka.log"
        return 1
    fi
}

stop_kafka() {
    log_step "停止 Kafka..."
    "${KAFKA_HOME}/bin/kafka-server-stop.sh" "${KAFKA_CONFIG}" 2>/dev/null
    sleep 2
    log_info "  Kafka 已停止"
}

# ============================================================================
# Topic 初始化
# ============================================================================
init_topics() {
    log_step "检查 Kafka Topics..."

    for i in "${!TOPICS[@]}"; do
        local topic="${TOPICS[$i]}"
        local partitions="${TOPIC_PARTITIONS[$i]}"

        if ${KAFKA_HOME}/bin/kafka-topics.sh --bootstrap-server "${KAFKA_BOOTSTRAP}" --describe --topic "${topic}" &>/dev/null; then
            log_info "  Topic '${topic}' 已存在"
        else
            log_warn "  创建 Topic '${topic}' ..."
            ${KAFKA_HOME}/bin/kafka-topics.sh --create \
                --bootstrap-server "${KAFKA_BOOTSTRAP}" \
                --topic "${topic}" \
                --partitions "${partitions}" \
                --replication-factor "${TOPIC_REPLICATION}"
            log_info "  Topic '${topic}' 创建完成"
        fi
    done
}

# ============================================================================
# 数据文件
# ============================================================================
check_data() {
    log_step "检查数据文件..."
    for topic in "${TOPICS[@]}"; do
        if [[ -f "${SCRIPT_DIR}/data/${topic}.json" ]]; then
            local lines=$(wc -l < "${SCRIPT_DIR}/data/${topic}.json")
            log_info "  ${topic}.json — ${lines} 条"
        else
            log_warn "  ${topic}.json 不存在，正在生成..."
            python3 "${SCRIPT_DIR}/generate_data.py"
            return
        fi
    done
}

# ============================================================================
# Flume 启停
# ============================================================================
start_flume() {
    log_step "启动 Flume..."

    if pgrep -f "flume.node.Application" > /dev/null; then
        log_warn "  Flume 已在运行中"
        return 0
    fi

    mkdir -p "${SCRIPT_DIR}/logs"

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

stop_flume() {
    log_step "停止 Flume..."
    local pid_file="${SCRIPT_DIR}/pids/flume.pid"

    if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
        kill "$(cat "${pid_file}")"
        rm -f "${pid_file}"
        log_info "  Flume 已停止"
    elif pkill -f "flume.node.Application" 2>/dev/null; then
        log_info "  Flume 已停止"
    else
        log_warn "  Flume 未在运行"
    fi
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

    echo ""
    bash "${SCRIPT_DIR}/feed_data.sh" status
}

# ============================================================================
# 主入口
# ============================================================================
main() {
    local cmd="${1:-start}"

    case "${cmd}" in
        start)
            echo ""
            echo "=========================================="
            echo "  冷启动混合推荐系统 — 一键启动"
            echo "=========================================="
            echo ""

            check_data
            start_kafka
            init_topics
            bash "${SCRIPT_DIR}/feed_data.sh" start
            sleep 2
            start_flume

            echo ""
            log_info "全部启动完成！"
            log_info "  Kafka : ${KAFKA_BOOTSTRAP}"
            log_info "  数据流: feed_data → output/*.log → Flume → Kafka"
            log_info "  状态  : ./start_all.sh status"
            log_info "  停止  : ./start_all.sh stop"
            ;;
        stop)
            echo ""
            log_info "正在停止管道..."
            stop_flume
            bash "${SCRIPT_DIR}/feed_data.sh" stop
            stop_kafka
            echo ""
            log_info "管道已完全停止。"
            ;;
        status)
            show_status
            ;;
        *)
            echo "用法: $0 {start|stop|status}"
            exit 1
            ;;
    esac
}

main "$@"
