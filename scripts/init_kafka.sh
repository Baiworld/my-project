#!/bin/bash
# ============================================================================
# init_kafka.sh — 创建 Kafka Topics
#
# 用法:
#   ./init_kafka.sh                   # 创建全部3个Topic
#   ./init_kafka.sh delete            # 删除全部Topic（谨慎）
#   ./init_kafka.sh list              # 列出所有Topic
# ============================================================================

KAFKA_HOME="${KAFKA_HOME:-/opt/kafka}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-node1:9092}"

# Topic 定义
declare -A TOPIC_PARTITIONS=(
    ["user_behavior"]=3
    ["content_metadata"]=2
    ["user_register"]=2
)
TOPIC_RETENTION_HOURS=24
TOPIC_RETENTION_MS=$((TOPIC_RETENTION_HOURS * 3600 * 1000))

create_topics() {
    echo "=============================================="
    echo "  Kafka Topic 初始化"
    echo "  Broker: $BOOTSTRAP_SERVER"
    echo "=============================================="

    for topic in "${!TOPIC_PARTITIONS[@]}"; do
        partitions=${TOPIC_PARTITIONS[$topic]}
        echo ""
        echo "  创建 Topic: $topic (${partitions} 分区) ..."

        $KAFKA_HOME/bin/kafka-topics.sh \
            --bootstrap-server "$BOOTSTRAP_SERVER" \
            --create \
            --topic "$topic" \
            --partitions "$partitions" \
            --replication-factor 1 \
            --config "retention.ms=${TOPIC_RETENTION_MS}" \
            --config "compression.type=snappy" \
            --if-not-exists

        echo "  ✓ $topic 创建完成"
    done

    echo ""
    echo "=============================================="
    echo "  当前所有 Topics:"
    echo "=============================================="
    list_topics
}

delete_topics() {
    echo "=============================================="
    echo "  !!! 警告: 即将删除以下 Topics !!!"
    echo "=============================================="
    for topic in "${!TOPIC_PARTITIONS[@]}"; do
        echo "    - $topic"
    done
    echo ""
    read -p "  确认删除? (输入 yes 继续): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "  已取消。"
        exit 0
    fi

    for topic in "${!TOPIC_PARTITIONS[@]}"; do
        echo "  删除: $topic ..."
        $KAFKA_HOME/bin/kafka-topics.sh \
            --bootstrap-server "$BOOTSTRAP_SERVER" \
            --delete \
            --topic "$topic"
        echo "  ✓ $topic 已删除"
    done
}

list_topics() {
    $KAFKA_HOME/bin/kafka-topics.sh \
        --bootstrap-server "$BOOTSTRAP_SERVER" \
        --list
}

case "${1:-create}" in
    create) create_topics ;;
    delete) delete_topics ;;
    list)   list_topics ;;
    *)
        echo "用法: $0 {create|delete|list}"
        echo ""
        echo "  create  — 创建3个Topic (默认)"
        echo "  delete  — 删除全部Topic"
        echo "  list    — 列出已有Topics"
        exit 1
        ;;
esac
