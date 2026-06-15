#!/bin/bash
# ============================================================================
# feed_data.sh — 模拟数据逐条喂入脚本
#
# 每秒从每个 Topic 对应的 JSONL 数据文件中读取 1 条记录，
# 追加到对应的输出文件（供 Flume tail -F 消费并推送至 Kafka）。
#
# 用法:
#   ./feed_data.sh start              # 启动所有 Topic 的数据喂入（后台）
#   ./feed_data.sh stop               # 停止所有喂入进程
#   ./feed_data.sh status             # 查看运行状态
#   ./feed_data.sh restart            # 重启
#   ./feed_data.sh start -t user_behavior  # 仅启动指定 Topic
#
# 目录结构:
#   data-generator/
#   ├── data/                         # 输入：静态 JSONL 数据文件
#   │   ├── user_behavior.json
#   │   ├── content_metadata.json
#   │   └── user_register.json
#   ├── output/                       # 输出：Flume 监控的日志文件
#   │   ├── user_behavior.log
#   │   ├── content_metadata.log
#   │   └── user_register.log
#   ├── logs/                         # 脚本运行日志
#   └── pids/                         # 进程 PID 文件
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"
OUTPUT_DIR="${SCRIPT_DIR}/output"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_DIR="${SCRIPT_DIR}/pids"

# 每个 Topic 每秒读取的行数（可配置）
LINES_PER_SECOND=1

# Topic 定义：topic_name:input_file
declare -A TOPICS=(
    ["user_behavior"]="user_behavior.json"
    ["content_metadata"]="content_metadata.json"
    ["user_register"]="user_register.json"
)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*" >&2; }

# ============================================================================
# 初始化目录
# ============================================================================
init_dirs() {
    mkdir -p "${OUTPUT_DIR}" "${LOG_DIR}" "${PID_DIR}"
}

# ============================================================================
# 单 Topic 喂入进程
# 参数: $1=topic_name, $2=input_jsonl_file
# ============================================================================
feed_topic() {
    local topic=$1
    local input_file="${DATA_DIR}/$2"
    local output_file="${OUTPUT_DIR}/${topic}.log"
    local pid_file="${PID_DIR}/${topic}.pid"
    local log_file="${LOG_DIR}/${topic}.log"

    # 检查输入文件
    if [[ ! -f "${input_file}" ]]; then
        log_error "[${topic}] 输入文件不存在: ${input_file}"
        exit 1
    fi

    local total_lines
    total_lines=$(wc -l < "${input_file}")
    log_info "[${topic}] 开始喂入数据 (共 ${total_lines} 行, ${LINES_PER_SECOND} 行/秒)"
    log_info "[${topic}] 输入: ${input_file}"
    log_info "[${topic}] 输出: ${output_file}"

    local line_count=0
    local loop_count=0

    while true; do
        # 逐行读取，到达末尾后循环
        while IFS= read -r line || [[ -n "${line}" ]]; do
            # 跳过空行
            [[ -z "${line}" ]] && continue

            echo "${line}" >> "${output_file}"
            line_count=$((line_count + 1))

            # 每 100 条输出一次进度到日志
            if (( line_count % 100 == 0 )); then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${topic}: 已发送 ${line_count} 条 (循环 #${loop_count})" >> "${log_file}"
            fi

            sleep 1
        done < "${input_file}"

        loop_count=$((loop_count + 1))
        log_info "[${topic}] 完成第 ${loop_count} 轮循环 (${total_lines} 条)，重新开始..."
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${topic}: ===== 完成第 ${loop_count} 轮 (${total_lines} 条), 重新开始 =====" >> "${log_file}"
    done
}

# ============================================================================
# 启动
# ============================================================================
cmd_start() {
    local filter_topic="${1:-}"

    init_dirs

    for topic in "${!TOPICS[@]}"; do
        # 如果指定了 -t 参数，只启动该 Topic
        if [[ -n "${filter_topic}" && "${topic}" != "${filter_topic}" ]]; then
            continue
        fi

        local pid_file="${PID_DIR}/${topic}.pid"

        if [[ -f "${pid_file}" ]]; then
            local pid
            pid=$(cat "${pid_file}")
            if kill -0 "${pid}" 2>/dev/null; then
                log_warn "[${topic}] 已在运行中 (PID: ${pid})"
                continue
            else
                rm -f "${pid_file}"
            fi
        fi

        # 清空旧输出日志（可选：追加模式注释掉下面这行）
        # > "${OUTPUT_DIR}/${topic}.log"

        # 后台启动喂入进程
        feed_topic "${topic}" "${TOPICS[$topic]}" &
        local child_pid=$!
        echo "${child_pid}" > "${pid_file}"
        log_info "[${topic}] 已启动 (PID: ${child_pid})"
    done

    echo ""
    log_info "所有 Topic 喂入进程已启动。使用 '$0 status' 查看状态，'$0 stop' 停止。"
}

# ============================================================================
# 停止
# ============================================================================
cmd_stop() {
    local filter_topic="${1:-}"

    for topic in "${!TOPICS[@]}"; do
        if [[ -n "${filter_topic}" && "${topic}" != "${filter_topic}" ]]; then
            continue
        fi

        local pid_file="${PID_DIR}/${topic}.pid"

        if [[ ! -f "${pid_file}" ]]; then
            log_warn "[${topic}] 未在运行"
            continue
        fi

        local pid
        pid=$(cat "${pid_file}")

        if kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" && log_info "[${topic}] 已停止 (PID: ${pid})"
            # 等待子进程退出
            wait "${pid}" 2>/dev/null || true
        else
            log_warn "[${topic}] 进程不存在 (PID: ${pid})"
        fi

        rm -f "${pid_file}"
    done
}

# ============================================================================
# 状态查看
# ============================================================================
cmd_status() {
    echo "=========================================="
    echo "  模拟数据喂入脚本 — 运行状态"
    echo "=========================================="
    printf "%-22s %-8s %-12s %s\n" "Topic" "PID" "状态" "输出文件行数"
    echo "------------------------------------------"

    for topic in "${!TOPICS[@]}"; do
        local pid_file="${PID_DIR}/${topic}.pid"
        local output_file="${OUTPUT_DIR}/${topic}.log"
        local pid="-"
        local status="${RED}未运行${NC}"

        if [[ -f "${pid_file}" ]]; then
            pid=$(cat "${pid_file}")
            if kill -0 "${pid}" 2>/dev/null; then
                status="${GREEN}运行中${NC}"
            else
                status="${YELLOW}已退出${NC}"
                rm -f "${pid_file}"
            fi
        fi

        # 统计输出文件行数
        local out_lines=0
        if [[ -f "${output_file}" ]]; then
            out_lines=$(wc -l < "${output_file}")
        fi

        printf "%-22s %-8s %-12b %s\n" "${topic}" "${pid}" "${status}" "${out_lines}"
    done

    echo "------------------------------------------"
    echo "输出目录: ${OUTPUT_DIR}"
    echo "日志目录: ${LOG_DIR}"
    echo ""
    echo "查看实时输出: tail -f ${OUTPUT_DIR}/*.log"
}

# ============================================================================
# 主入口
# ============================================================================
main() {
    if [[ $# -eq 0 ]]; then
        echo "用法: $0 {start|stop|status|restart} [-t <topic>]"
        echo ""
        echo "命令:"
        echo "  start    启动所有 Topic 的数据喂入"
        echo "  stop     停止所有喂入进程"
        echo "  status   查看运行状态"
        echo "  restart  重启所有喂入进程"
        echo ""
        echo "选项:"
        echo "  -t <topic>  仅操作指定 Topic (user_behavior | content_metadata | user_register)"
        echo ""
        echo "示例:"
        echo "  $0 start                     # 启动全部"
        echo "  $0 start -t user_behavior    # 仅启动用户行为"
        echo "  $0 stop -t content_metadata  # 仅停止内容元数据"
        exit 1
    fi

    local cmd="$1"
    local filter_topic=""

    # 解析 -t 参数
    if [[ $# -ge 3 && "$2" == "-t" ]]; then
        filter_topic="$3"
        if [[ -z "${TOPICS[$filter_topic]:-}" ]]; then
            log_error "未知 Topic: ${filter_topic}"
            log_error "可用: ${!TOPICS[*]}"
            exit 1
        fi
    fi

    case "${cmd}" in
        start)
            cmd_start "${filter_topic}"
            ;;
        stop)
            cmd_stop "${filter_topic}"
            ;;
        status)
            cmd_status
            ;;
        restart)
            log_info "正在重启..."
            cmd_stop "${filter_topic}"
            sleep 2
            cmd_start "${filter_topic}"
            ;;
        *)
            log_error "未知命令: ${cmd}"
            exit 1
            ;;
    esac
}

main "$@"
