# AGENTS.md — 基于 Spark 大数据的用户行为实时分析与混合推荐系统

## 项目概述

基于 Spark 大数据的用户行为实时分析与混合推荐系统。数据生成器 → Flume → Kafka 实时接入用户行为 → Spark Streaming 实时分析 → SparkSQL 离线训练 → Flask API → Vue 数据大屏。

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 构建工具 | Maven (scala-maven-plugin) | 3.9+ / Scala 2.13.10 |
| IDE | IntelliJ IDEA (Scala 插件) | 2024+ |
| 消息 | Kafka | 3.3.1 |
| 数据接入 | Flume | — |
| 实时计算 | Spark Streaming (Scala) | 3.3.1 |
| 离线计算 | SparkSQL (Scala) | 3.3.1 |
| 存储 | MySQL | 5.7 |
| 后端 | Flask (Python) | 3.1.0 |
| 前端 | Vue 3 + Vite + Pinia + ECharts | 3.4 / 5.1 / 5.5 |

**环境**: Kafka、Flume、MySQL 运行在虚拟机 `192.168.88.134` 上。Flask 和 Vue 在本地 Windows 运行。不依赖 Docker。

## 目录结构

```
E:\TraeBD\
├── pom.xml                     # Maven 父 POM（聚合 2 个 Scala 模块）
├── docs/                       # 设计文档（需求、架构、详细设计、分工）
├── sql/init.sql                # 数据库初始化（11 张表 + 存储过程 + 定时事件）
├── checkpoints/                # Spark Streaming checkpoint 目录（运行时生成）
│
├── data-generator/             # Python 模拟数据生成器 + Flume 配置
│   ├── generate_data.py        # 生成 user_behavior / content_metadata / user_register JSONL
│   ├── start_all.sh            # 一键启动：生成数据 → Flume → Kafka
│   ├── feed_data.sh            # 将 JSONL 文件 feed 到 Flume 源
│   ├── data/                   # 生成的 JSONL 数据文件（各 10,000 条）
│   └── flume/                  # Flume 配置（flume.conf, flume-env.sh）
│
├── spark-streaming/            # Scala Maven 模块 — 实时分析
│   ├── pom.xml
│   └── src/main/scala/com/recommend/streaming/
│       ├── Models.scala         # case class 定义（UserBehaviorEvent, ContentMetaEvent 等）
│       ├── DataValidator.scala # FR-02 数据校验 + 去重 + 死信路由
│       ├── UserProfileAgg.scala # FR-03 用户画像聚合（5min 滑动窗口）
│       ├── ContentHotStats.scala # FR-04 内容热度统计（1min 窗口）
│       ├── ColdStartCluster.scala # FR-05 冷启动 K-Means 聚类
│       ├── MySQLBatchWriter.scala # 批量写入 rt_* 表 + content_metadata 表
│       └── RealTimeAnalysisApp.scala # 主入口，组装全部管线
│
├── spark-offline/              # Scala Maven 模块 — 离线批处理
│   ├── pom.xml
│   └── src/main/scala/com/recommend/offline/
│       ├── Models.scala
│       ├── OfflineAnalysisApp.scala # 主入口，按 job 参数调度子任务
│       ├── UserPortraitBuilder.scala # FR-06 用户全量画像（128 维向量 + 生命周期）
│       ├── SimilarityMatrix.scala # FR-07 内容相似度（ALS 隐向量 / 内容特征回退）
│       ├── ALSTrainer.scala    # ALS 模型训练（真实行为数据驱动的隐式反馈）
│       ├── ALSRecommender.scala # ALS 批量推荐推理
│       ├── HybridRecommender.scala # FR-08 三路分流混合推荐 + DPP 重排
│       └── MetricsCalculator.scala # FR-09 推荐效果指标（CTR/CVR/覆盖率/多样性）
│
├── flask-backend/              # Python — REST API + WebSocket
│   ├── app/
│   │   ├── extensions.py       # db, jwt, socketio 实例
│   │   ├── __init__.py         # create_app() 工厂函数
│   │   ├── auth/               # 注册/登录/刷新/邮箱验证（bcrypt + JWT HS256）
│   │   ├── permissions/        # @require_role(*roles) 装饰器
│   │   ├── api/                # 6 个查询接口 + 管理（recommendations, metrics, content, users, coldstart, admin）
│   │   ├── models/             # SysUser, SysRole, SysUserRole, SysAuditLog
│   │   ├── export/             # CSV/Excel 导出
│   │   ├── websocket/          # DashboardPusher + EventLogPusher
│   │   ├── email_service/      # SMTP 邮件验证码
│   │   └── utils/              # validators, error_handlers, audit
│   ├── config.py               # Dev/Test/Prod 配置
│   ├── run.py                  # 入口 :5000
│   ├── requirements.txt
│   └── Dockerfile
│
└── vue-frontend/               # Vue 3 SPA
    └── src/
        ├── views/              # login/, dashboard/, query/, admin/
        ├── components/common/  # Paginator, DatePicker
        ├── components/dashboard/ # 7 图表 + MetricCard + ScrollLog
        ├── stores/             # Pinia: auth.js, dashboard.js
        ├── api/                # Axios 封装 + 拦截器（dev 走 Vite proxy）
        ├── composables/        # useWebSocket, useECharts
        └── router/             # beforeEach 守卫 (JWT + RBAC)
```

## 数据库（12 张表）

| 前缀 | 表名 | 用途 |
|------|------|------|
| `rt_` | user_profile, content_hot, coldstart_cluster | Spark Streaming 写入，保留 7 天 |
| `offline_` | user_portrait, content_sim, recommendations, metrics | SparkSQL 写入，保留 90 天 |
| `sys_` | user, role, user_role, audit_log | Flask 读写，永久保留 |
| — | content_metadata | Spark Streaming + 数据导入，内容标题/标签/风格等 |

MySQL 连接: `app/app123@192.168.88.134:3306/recommend_db`

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `Admin@123456` | 系统管理员 |

新用户可自行注册（默认 `end_user` 角色）。

## 常用命令

### 环境准备
- **MySQL**: 虚拟机 `192.168.88.134:3306`，首次执行 `sql/init.sql`
- **Kafka**: 虚拟机 `192.168.88.134:9092`
- **Flume**: 虚拟机，配置在 `data-generator/flume/`

### 模拟数据生成（虚拟机上执行）
```bash
cd data-generator
python generate_data.py          # 生成 3×10,000 条 JSONL
bash start_all.sh                # 生成 + Flume → Kafka
```

### Maven 编译
```bash
mvn compile                      # 编译全部 2 个模块
mvn package -pl spark-streaming  # 打包 Streaming fat jar
mvn package -pl spark-offline    # 打包 Offline fat jar
```

### Spark 运行
```bash
spark-submit --class com.recommend.streaming.RealTimeAnalysisApp --master local[4] spark-streaming-1.0.jar
spark-submit --class com.recommend.offline.OfflineAnalysisApp --master local[4] spark-offline-1.0.jar [job]
# job: portrait | similarity | als-train | recommend | metrics | all
```

### Flask
```bash
cd flask-backend; pip install -r requirements.txt; python run.py
```

### Vue
```bash
cd vue-frontend; npm install; npm run dev  # :5173，proxy → :5000
```

## Flask API 路由

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/auth/register` | 公开 | 注册 |
| POST | `/auth/login` | 公开 | 登录 |
| POST | `/auth/logout` | JWT | 登出 |
| POST | `/auth/refresh` | JWT(refresh) | 刷新 Token |
| POST | `/auth/send-verification` | JWT | 发送邮箱验证码 |
| GET | `/api/health` | 公开 | 健康检查 |
| GET | `/api/recommendations` | operator, admin | 推荐列表（JOIN 真实标题） |
| GET | `/api/metrics` | operator, admin | 指标查询 |
| GET | `/api/content` | operator, admin | 内容列表 |
| GET | `/api/content/hot` | operator, admin | 热门内容（JOIN 真实标题） |
| GET | `/api/users/profile` | operator, admin | 用户画像（实时+离线） |
| GET | `/api/coldstart/analysis` | operator, admin | 冷启动用户列表 |
| GET | `/api/coldstart/stats` | operator, admin | 冷启动聚合统计 |
| GET | `/api/export/<table>` | operator, admin | CSV/Excel 导出 |
| GET/PUT | `/api/admin/settings` | admin | 系统设置 |
| GET/POST | `/api/admin/users` | admin | 用户管理 |
| PUT | `/api/admin/users/<id>` | admin | 编辑用户 |
| PUT | `/api/admin/users/<id>/status` | admin | 切换状态 |
| DELETE | `/api/admin/users/<id>` | admin | 删除用户 |
| GET | `/api/admin/audit-logs` | admin | 审计日志查询 |

## Vue 路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 公开 |
| `/dashboard` | 数据大屏（4 Tab + 7 图表） | 需登录 |
| `/query` | 查询管理（3 Tab） | operator, admin |
| `/query/user/:id` | 用户画像详情 | operator, admin |
| `/admin` | 系统管理 | admin |

## 关键设计决策

- **冷启动阈值**: behavior_count ≤ 50 → 聚类热门 + ε-greedy 探索
- **过渡期**: behavior_count ∈ [30, 80] → 冷启动与存量策略线性插值
- **音乐:视频比例**: 6:4（冷启动默认），根据 content_type_ratio 动态调整
- **ALS 参数**: rank=50, alpha=40.0, regParam=0.1, 隐式反馈
- **相似度矩阵**: 优先 ALS 隐向量余弦相似度 → 回退内容特征多维度加权（标签 Jaccard + 风格/语言/BPM/时长）
- **DPP 多样性**: theta=0.7, 从 Top-100 重排到 Top-50
- **ε-greedy**: ε=0.15
- **密码策略**: bcrypt cost=12（可配）, 8-64 位, 至少 3/4 字符类别

## 模块间数据流

```
[数据生成器] → Flume → Kafka → Spark Streaming → MySQL rt_* 表 + content_metadata
                                         ↓
[定时 Cron] → SparkSQL 读 rt_* → 批量计算 → MySQL offline_* 表
                                                 ↓
[运营/管理员] → Vue → Flask API 查询 → MySQL → JSON 响应
[数据大屏]   → Vue WebSocket ← Flask SocketIO push ← MySQL 轮询
```
