#!/bin/bash
# ============================================================================
# feed_data.sh — 逐行投喂模拟数据到输出文件（供 Flume 监控）
#
# 用法:
#   ./feed_data.sh start          # 启动全部3条投喂流（后台）
#   ./feed_data.sh stop           # 停止全部
#   ./feed_data.sh status         # 查看状态
#   ./feed_data.sh restart        # 重启全部（从文件头开始）
#
# 原理:
#   每秒从 data/{topic}.json 读取一条 → 追加到 output/{topic}.log
#   Flume 监控 output/*.log 并推送到 Kafka
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR"                          # /export/data/mock_data_BD2
OUTPUT_DIR="/export/data/BD2_data"             # 输出文件
PID_DIR="$OUTPUT_DIR/.pids"
LOG_DIR="$OUTPUT_DIR/logs"

# 3个Topic的投喂配置
declare -A TOPIC_FILES=(
    ["user_behavior"]="$DATA_DIR/user_behavior.json"
    ["content_metadata"]="$DATA_DIR/content_metadata.json"
    ["user_register"]="$DATA_DIR/user_register.json"
)
declare -A OUTPUT_FILES=(
    ["user_behavior"]="$OUTPUT_DIR/user_behavior.log"
    ["content_metadata"]="$OUTPUT_DIR/content_metadata.log"
    ["user_register"]="$OUTPUT_DIR/user_register.log"
)

# 每条投喂间隔（秒）
INTERVAL="${INTERVAL:-1}"

# ============================================================
#  初始化目录
# ============================================================
init_dirs() {
    mkdir -p "$OUTPUT_DIR" "$PID_DIR" "$LOG_DIR"
}

# ============================================================
#  投喂单个Topic的数据
# ============================================================
feed_topic() {
    local topic=$1
    local source_file="${TOPIC_FILES[$topic]}"
    local output_file="${OUTPUT_FILES[$topic]}"
    local pid_file="$PID_DIR/${topic}.pid"
    local cursor_file="$PID_DIR/${topic}.cursor"

    if [ ! -f "$source_file" ]; then
        echo "  [ERROR] 数据文件不存在: $source_file"
        return 1
    fi

    # 读取上次游标位置，不存在则从0开始
    local cursor=0
    if [ -f "$cursor_file" ]; then
        cursor=$(cat "$cursor_file")
    fi

    local total_lines=$(wc -l < "$source_file")

    echo "  [$topic] 启动 — 源: $(basename $source_file) ($total_lines 行)"
    echo "  [$topic] 输出: $output_file"
    echo "  [$topic] 从第 $((cursor + 1)) 行开始, 间隔 ${INTERVAL}s"

    # 后台循环: 每秒读一行追加到输出文件
    (
        local line_num=$cursor
        while true; do
            line_num=$((line_num + 1))

            # 读到末尾则退出
            if [ $line_num -gt $total_lines ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$topic] 数据已全部投喂完成 ($total_lines 条)"
                rm -f "$pid_file"
                exit 0
            fi

            # 读取第 N 行并追加
            sed -n "${line_num}p" "$source_file" >> "$output_file"

            # 更新游标
            echo $line_num > "$cursor_file"

            sleep "$INTERVAL"
        done
    ) >> "$LOG_DIR/${topic}.log" 2>&1 &

    # 记录PID
    echo $! > "$pid_file"
    echo "  [$topic] PID: $!"
}

# ============================================================
#  停止单个Topic投喂
# ============================================================
stop_topic() {
    local topic=$1
    local pid_file="$PID_DIR/${topic}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  [$topic] 已停止 (PID: $pid)"
        else
            echo "  [$topic] 进程已不存在 (PID: $pid)"
        fi
        rm -f "$pid_file"
    else
        echo "  [$topic] 未在运行"
    fi
}

# ============================================================
#  查看单个Topic状态
# ============================================================
status_topic() {
    local topic=$1
    local pid_file="$PID_DIR/${topic}.pid"
    local cursor_file="$PID_DIR/${topic}.cursor"
    local source_file="${TOPIC_FILES[$topic]}"
    local output_file="${OUTPUT_FILES[$topic]}"

    if [ -f "$source_file" ]; then
        local total=$(wc -l < "$source_file")
    else
        local total="N/A"
    fi

    if [ -f "$cursor_file" ]; then
        local cursor=$(cat "$cursor_file")
    else
        local cursor=0
    fi

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local status="运行中"
        local pid=$(cat "$pid_file")
    else
        local status="已停止"
        local pid="-"
    fi

    printf "  %-22s | %-6s | %8s / %-8s | %s\n" "$topic" "$status" "$cursor" "$total" "PID: $pid"
}

# ============================================================
#  命令入口
# ============================================================

case "${1:-start}" in

    start)
        init_dirs
        echo "=============================================="
        echo "  逐行投喂脚本 — 启动"
        echo "=============================================="
        for topic in "user_behavior" "content_metadata" "user_register"; do
            feed_topic "$topic"
        done
        echo ""
        echo "  全部启动完成。日志目录: $LOG_DIR"
        echo "  输出目录: $OUTPUT_DIR"
        echo "  使用 '$0 status' 查看进度"
        ;;

    stop)
        echo "=============================================="
        echo "  逐行投喂脚本 — 停止"
        echo "=============================================="
        for topic in "user_behavior" "content_metadata" "user_register"; do
            stop_topic "$topic"
        done
        echo ""
        echo "  全部已停止。"
        ;;

    restart)
        echo "=============================================="
        echo "  逐行投喂脚本 — 重启（重置游标）"
        echo "=============================================="
        # 先停止
        for topic in "user_behavior" "content_metadata" "user_register"; do
            stop_topic "$topic" 2>/dev/null
        done
        # 清空游标和输出文件
        rm -f "$PID_DIR"/*.cursor
        rm -f "$OUTPUT_DIR"/*.log
        echo "  游标和输出文件已清空。"
        echo ""
        # 重新启动
        for topic in "user_behavior" "content_metadata" "user_register"; do
            feed_topic "$topic"
        done
        ;;

    status)
        echo "=============================================="
        echo "  逐行投喂脚本 — 状态"
        echo "=============================================="
        printf "  %-22s | %-6s | %18s | PID\n" "TOPIC" "状态" "进度"
        printf "  %-22s-+-%-6s-+-%-18s-+-%s\n" "----------------------" "------" "------------------" "-----"
        for topic in "user_behavior" "content_metadata" "user_register"; do
            status_topic "$topic"
        done
        echo ""
        echo "  输出目录: $OUTPUT_DIR"
        ls -lh "$OUTPUT_DIR"/*.log 2>/dev/null || echo "  (暂无输出文件)"
        ;;

    *)
        echo "用法: $0 {start|stop|restart|status}"
        echo ""
        echo "  start    — 启动全部3条投喂流（后台运行）"
        echo "  stop     — 停止全部投喂流"
        echo "  restart  — 清空进度并重新开始"
        echo "  status   — 查看投喂进度"
        exit 1
        ;;
esac
