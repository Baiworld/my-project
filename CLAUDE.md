# CLAUDE.md — 冷启动音乐与视频混合推荐系统

## 项目概述

基于 Spark+AI 的冷启动音乐与视频混合推荐系统。Kafka 实时接入用户行为 → Spark Streaming 实时分析 → SparkSQL 离线训练 → Flask API → Vue 数据大屏。

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 构建工具 | Maven (scala-maven-plugin) | 3.8+ / Scala 2.13.10 |
| IDE | IntelliJ IDEA (Scala 插件) | 2024+ |
| 消息 | Kafka | 3.3.1 |
| 实时计算 | Spark Streaming (Scala) | 3.3.1 |
| 离线计算 | SparkSQL (Scala) | 3.3.1 |
| 存储 | MySQL | 8.0 |
| 后端 | Flask (Python) | 3.1.0 |
| 前端 | Vue 3 + Vite + Pinia + ECharts | 3.4 / 5.1 / 5.5 |

**重要**: 本项目不依赖 Docker。MySQL 和 Kafka 需在本地安装并运行。

## 目录结构

```
E:\TraeBD\
├── pom.xml                     # Maven 父 POM（聚合 3 个 Scala 模块）
├── docs/                       # 设计文档（需求、架构、详细设计、分工）
├── sql/init.sql                # 数据库初始化（11 张表 + 存储过程 + 定时事件）
├── docker-compose.yml          # 可选：Docker 开发环境（Zookeeper + Kafka + MySQL + Flask + Vue）
│
├── kafka-producer/             # Scala Maven 模块 — Mock 数据生成 & 写入 Kafka
│   ├── pom.xml
│   └── src/main/scala/com/recommend/producer/
│
├── spark-streaming/            # Scala Maven 模块 — 实时分析
│   ├── pom.xml
│   └── src/main/scala/com/recommend/streaming/
│
├── spark-offline/              # Scala Maven 模块 — 离线批处理
│   ├── pom.xml
│   └── src/main/scala/com/recommend/offline/
│
├── flask-backend/              # Python — REST API + WebSocket
│   ├── app/
│   │   ├── extensions.py       # db, jwt, socketio 实例
│   │   ├── __init__.py         # create_app() 工厂函数
│   │   ├── auth/               # 注册/登录/刷新（bcrypt + JWT HS256）
│   │   ├── permissions/        # @require_role(*roles) 装饰器
│   │   ├── api/                # 5 个查询接口（recommendations, metrics, content, users, coldstart）
│   │   ├── models/             # SysUser, SysRole, SysUserRole, SysAuditLog
│   │   ├── export/             # CSV/Excel 导出
│   │   ├── websocket/          # DashboardPusher + EventLogPusher
│   │   ├── email_service/      # SMTP 邮件验证码
│   │   └── utils/              # validators, error_handlers
│   ├── config.py               # Dev/Test/Prod 配置
│   ├── run.py                  # 入口
│   └── Dockerfile
│
└── vue-frontend/               # Vue 3 SPA
    └── src/
        ├── views/              # login/, dashboard/, query/, admin/
        ├── components/common/  # Paginator, DatePicker
        ├── stores/             # Pinia: auth.js, dashboard.js
        ├── api/                # Axios 封装 + 拦截器
        ├── composables/        # useWebSocket, useECharts
        └── router/             # beforeEach 守卫 (JWT + RBAC)
```

## 数据库（11 张表）

| 前缀 | 表名 | 用途 |
|------|------|------|
| `rt_` | user_profile, content_hot, coldstart_cluster | Spark Streaming 写入，保留 7 天 |
| `offline_` | user_portrait, content_sim, recommendations, metrics | SparkSQL 写入，保留 90 天 |
| `sys_` | user, role, user_role, audit_log | Flask 读写，永久保留 |

默认 MySQL 管理员: `root/123456@localhost:3306`
应用连接账号: `app/app123@localhost:3306/recommend_db`

## IntelliJ IDEA 导入

1. File → Open → 选择 `E:\TraeBD\pom.xml`（父 POM）
2. IntelliJ 自动识别 3 个 Maven 模块（kafka-producer, spark-streaming, spark-offline）
3. 确保已安装 **Scala 插件**（Settings → Plugins → 搜索 "Scala"）
4. 右键各模块的 `pom.xml` → Maven → Reload Project

## 常用命令

### 环境准备（本地安装，不使用 Docker）

- **MySQL 8.0**: 本地运行在 `localhost:3306`，首次执行 `sql/init.sql` 建库建表
- **Kafka 3.3.1**: 本地运行在 `localhost:9092`，需先启动 Zookeeper 再启动 Kafka
- **Java 11**: 确保 `JAVA_HOME` 指向 JDK 11

### Maven 编译与运行

```bash
# 编译全部模块
mvn compile

# 编译单个模块
mvn compile -pl kafka-producer

# 打包（spark-streaming/offline 会生成 fat jar）
mvn package -pl spark-streaming
mvn package -pl spark-offline
```

### Kafka Producer（Mock 数据生成）

```bash
# 1. 生成内容元数据（~8000 条，一次性）
mvn scala:run -pl kafka-producer -DmainClass=com.recommend.producer.ContentMetadataProducer

# 2. 生成用户注册（~10000 条，一次性）
mvn scala:run -pl kafka-producer -DmainClass=com.recommend.producer.UserRegisterProducer

# 3. 模拟行为流（100 条/秒 × 60 分钟）
mvn scala:run -pl kafka-producer -DmainClass=com.recommend.producer.UserBehaviorProducer
```

或直接在 IntelliJ 中右键 main 方法 → Run。

### Flask 后端

```bash
cd flask-backend
pip install -r requirements.txt
python run.py                       # 开发模式启动 :5000
```

### Vue 前端

```bash
cd vue-frontend
npm install
npm run dev                         # 开发服务器 :5173
```

## JWT 认证链路

1. Vue Axios 拦截器从 Pinia store 读 `access_token` → 注入 `Authorization: Bearer <token>`
2. Flask `@jwt_required()` 验证签名 → 解析 `sub`, `roles` claims
3. `@require_role("operator", "admin")` 做角色交集校验
4. Token 过期 → 响应 401 → Axios 拦截器自动 refresh → 重试原请求

## 关键设计决策

- **冷启动阈值**: behavior_count ≤ 50 → 冷启动策略（K-Means 聚类 + ε-greedy 探索）
- **过渡期**: behavior_count ∈ [30, 80] → 冷启动与存量策略按比例混合
- **音乐:视频比例**: 6:4（冷启动默认），后续根据 content_type_ratio 动态调整
- **ALS 参数**: rank=50, alpha=40.0, regParam=0.1
- **DPP 多样性**: theta=0.7, 从 Top-100 重排到 Top-50
- **ε-greedy**: ε=0.15, 15% 概率随机探索其他簇的内容
- **密码策略**: bcrypt cost=12, 8-64 位, 至少 3/4 字符类别

## 模块间数据流

```
[用户行为] → Kafka → Spark Streaming → MySQL rt_* 表
                                         ↓
[定时 Cron] → SparkSQL 读 rt_* → 批量计算 → MySQL offline_* 表
                                                 ↓
[运营/管理员] → Vue → Flask API 查询 → MySQL → JSON 响应
[数据大屏]   → Vue WebSocket ← Flask SocketIO push ← MySQL 轮询
```
