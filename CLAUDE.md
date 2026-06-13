# CLAUDE.md — 冷启动音乐与视频混合推荐系统

## 项目概述

基于 Spark+AI 的冷启动音乐与视频混合推荐系统。数据生成器 → Flume → Kafka 实时接入用户行为 → Spark Streaming 实时分析 → Flask API 实时查询 → Vue 数据大屏。SparkSQL 离线训练作为历史数据补充。

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 构建工具 | Maven (scala-maven-plugin) | 3.9+ / Scala 2.13.10 |
| 消息 | Kafka | 3.3.1 |
| 数据接入 | Flume | — |
| 实时计算 | Spark Streaming (Scala) | 3.3.1 |
| 离线计算 | SparkSQL (Scala) | 3.3.1 |
| 存储 | MySQL | 5.7 |
| 后端 | Flask API | Python 3.11 / Flask 3.1.0 |
| 前端 | Vue 3 + Vite + Pinia + ECharts | 3.4 / 5.1 / 5.5 |

**环境**: Kafka、Flume、MySQL 运行在虚拟机 `192.168.88.134` 上。Flask 和 Vue 在本地 Windows 运行。Spark Streaming 在 Windows 本地运行。不依赖 Docker。`start_app.bat` 使用 CRLF 换行符（Windows 兼容）。

## 目录结构

```
E:\TraeBD\
├── pom.xml                     # Maven 父 POM（聚合 2 个 Scala 模块）
├── docs/                       # 设计文档（需求、架构、详细设计、分工）
├── sql/init.sql                # 数据库初始化（11 张表 + 存储过程 + 定时事件）
├── checkpoints/                # Spark Streaming checkpoint 目录（运行时生成）
├── start_app.bat               # Windows 端一键启动脚本 (Spark + Flask + Vue)
│
├── data-generator/             # Python 模拟数据生成器 + Flume 配置 + 启动脚本
│   ├── generate_data.py        # 批量模式: 3×10,000 条 JSONL；--continuous: 持续生成
│   ├── start_pipeline.sh       # 虚拟机一键启动 (Flume + 持续数据生成)
│   ├── start_all.sh            # 旧版启动脚本 (Flume + 批量数据)
│   ├── feed_data.sh            # 将 JSONL 文件 feed 到 Flume 源
│   ├── data/                   # 批量模式生成的 JSONL 数据文件
│   └── flume/                  # Flume 配置（flume.conf, flume-env.sh）
│
├── spark-streaming/            # Scala Maven 模块 — 实时分析
│   ├── pom.xml
│   └── src/main/scala/com/recommend/streaming/
│       ├── Models.scala         # case class (UserBehaviorEvent, ContentMetaEvent, RegisterEvent)
│       ├── DataValidator.scala # FR-02 JSON 解析 + 去重 + 死信路由
│       ├── UserProfileAgg.scala # FR-03 用户画像 (5min滑动窗口, windowEnd=系统时间)
│       ├── ContentHotStats.scala # FR-04 内容热度 (1min滚动窗口)
│       ├── ColdStartCluster.scala # FR-05 冷启动 K-Means 聚类
│       ├── MySQLBatchWriter.scala # 批量写入 rt_* + content_metadata (INSERT IGNORE)
│       └── RealTimeAnalysisApp.scala # 主入口, 10s 微批次
│
├── spark-offline/              # Scala Maven 模块 — 离线批处理
│   ├── pom.xml
│   └── src/main/scala/com/recommend/offline/
│       ├── Models.scala
│       ├── OfflineAnalysisApp.scala # 主入口: portrait | als-train | recommend | metrics | all
│       ├── UserPortraitBuilder.scala # FR-06 用户全量画像
│       ├── ALSTrainer.scala    # ALS 模型训练 (隐式反馈)
│       ├── ALSRecommender.scala # ALS 批量推荐推理
│       ├── HybridRecommender.scala # FR-08 三路分流混合推荐 + DPP 重排
│       └── MetricsCalculator.scala # FR-09 推荐效果指标
│
├── flask-backend/              # Python — REST API + WebSocket
│   ├── app/
│   │   ├── extensions.py       # db, jwt, socketio 实例
│   │   ├── __init__.py         # create_app() 工厂函数, WebSocket push 启动
│   │   ├── auth/               # 注册/登录/刷新/邮箱验证 (bcrypt + JWT HS256)
│   │   ├── permissions/        # @require_role(*roles) 装饰器 (RBAC)
│   │   ├── api/                # 查询接口 (全优先 rt_* 实时计算)
│   │   │   ├── recommendations.py  # 推荐列表
│   │   │   ├── metrics.py          # 指标 (优先 rt_* 实时)
│   │   │   ├── content.py          # 内容列表 + 热门 (GROUP BY 去重)
│   │   │   ├── users.py            # 用户画像 (JOIN rt_ + offline_)
│   │   │   ├── coldstart.py        # 冷启动分析 + 统计 (转化率/策略分布 实时)
│   │   │   ├── region.py           # 地区热力图
│   │   │   └── admin.py            # 用户管理 + 审计日志
│   │   ├── models/             # SysUser, SysRole, SysUserRole, SysAuditLog
│   │   ├── export/             # CSV/Excel 导出
│   │   ├── websocket/          # DashboardPusher (5s推送全量快照) + EventLogPusher
│   │   ├── email_service/      # SMTP 邮件验证码
│   │   └── utils/              # validators, error_handlers, audit, cluster_utils
│   ├── config.py               # Dev/Test/Prod 配置
│   ├── run.py                  # 入口 :5000
│   ├── requirements.txt
│   └── Dockerfile
│
└── vue-frontend/               # Vue 3 SPA
    └── src/
        ├── views/              # login/, dashboard/, query/, admin/
        ├── components/common/  # Paginator, DatePicker
        ├── components/dashboard/ # 9 图表组件 (不再 dispose 重建, 用 setOption 更新)
        ├── stores/             # Pinia: auth.js, dashboard.js
        ├── api/                # Axios 封装 + 拦截器 (dev 走 Vite proxy)
        ├── composables/        # useWebSocket, useECharts
        └── router/             # beforeEach 守卫 (JWT + RBAC)
```

## 数据库（11 张表）

| 前缀 | 表名 | 用途 | 数据来源 |
|------|------|------|----------|
| `rt_` | user_profile | 用户实时画像 (window_end=系统时间) | Spark Streaming |
| `rt_` | content_hot | 内容实时热度 (去重查询用 MAX+GROUP BY) | Spark Streaming |
| `rt_` | coldstart_cluster | 冷启动聚类结果 (8 个簇) | Spark Streaming |
| `offline_` | user_portrait | 用户全量画像 (128 维向量) | SparkSQL 批处理 |
| `offline_` | recommendations | 推荐结果 (三路分流+DPP 重排) | SparkSQL / 实时计算 |
| `offline_` | metrics | 历史 CTR/CVR 指标 (已改为备选) | 实时 rt_* 优先, offline_ 备选 |
| `sys_` | user, role, user_role | 用户+权限 (RBAC) | Flask |
| `sys_` | audit_log | 操作审计日志 | Flask |
| — | content_metadata | 内容元数据 (标题/风格/标签/BPM) | 数据生成器→Kafka→Spark |

> `offline_content_sim` 表及 SimilarityMatrix 代码已删除。HybridRecommender 内部实现 DPP 多样性重排，不再依赖预计算相似度矩阵。

MySQL 连接: `app/app123@192.168.88.134:3306/recommend_db`

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `Admin@123456` | 系统管理员 |

新用户可自行注册（默认 `end_user` 角色）。

## 快速启动（完整实时链路）

### 虚拟机端 (192.168.88.134)

```bash
# 一键启动 Flume + 持续数据生成
bash /opt/data-generator/start_pipeline.sh

# 可指定速率 (默认每秒 3 条)
bash /opt/data-generator/start_pipeline.sh 10

# 停止
bash /opt/data-generator/start_pipeline.sh stop
```

### Windows 端

```bash
# 双击或执行: 一键启动 Spark Streaming + Flask + Vue
start_app.bat
```

**启动顺序**: 虚拟机先启动 (Kafka/MySQL/Flume/Generator), 然后 Windows 启动 (Spark/Flask/Vue)。

**前端**: `http://localhost:5173/dashboard`

### 常用命令

```bash
# Maven 编译 (仅在修改 Scala 代码后需要)
mvn compile
mvn package -pl spark-streaming -DskipTests

# Spark Streaming 单独启动
spark-submit --class com.recommend.streaming.RealTimeAnalysisApp \
  --master local[2] spark-streaming/target/spark-streaming-1.0-shaded.jar

# Spark Offline 批处理 (可选, 需要 Spark 空闲时运行)
spark-submit --class com.recommend.offline.OfflineAnalysisApp \
  --master local[2] spark-offline-1.0.jar [job]
# job: portrait | als-train | recommend | metrics | all

# Flask 单独启动
cd flask-backend
pip install -r requirements.txt
python run.py

# Vue 单独启动
cd vue-frontend
npm install
npm run dev

# 批量数据生成 (调试用)
cd data-generator
python generate_data.py                        # 生成 3×10,000 条
python generate_data.py --continuous --rate 5  # 持续生成, 每秒 5 条
```

## Flask API 路由

| 方法 | 路径 | 权限 | 数据来源 |
|------|------|------|----------|
| POST | `/auth/register` | 公开 | sys_user |
| POST | `/auth/login` | 公开 | sys_user |
| POST | `/auth/logout` | JWT | — |
| POST | `/auth/refresh` | JWT(refresh) | — |
| GET | `/api/health` | 公开 | — |
| GET | `/api/recommendations` | operator, admin | offline_recommendations + content_metadata |
| GET | `/api/metrics` | operator, admin | **rt_* 实时优先**, offline_ 备选 |
| GET | `/api/content` | operator, admin | rt_content_hot (GROUP BY 去重) |
| GET | `/api/content/hot` | operator, admin | rt_content_hot (MAX+GROUP BY 去重) |
| GET | `/api/content/<id>` | operator, admin | content_metadata |
| GET | `/api/users/profile` | operator, admin | rt_user_profile + offline_user_portrait |
| GET | `/api/users/profile/<id>` | operator, admin | 同上 |
| GET | `/api/coldstart/analysis` | operator, admin | rt_user_profile 冷启列表 |
| GET | `/api/coldstart/stats` | operator, admin | **rt_* 实时计算 (转化率/策略分布)** |
| GET | `/api/region/heatmap` | operator, admin | rt_user_profile + rt_coldstart_cluster |
| GET | `/api/export/<table>` | operator, admin | CSV/Excel 导出 |
| GET/PUT | `/api/admin/settings` | admin | 系统设置 |
| GET/POST | `/api/admin/users` | admin | 用户管理 |
| PUT | `/api/admin/users/<id>` | admin | 编辑用户 |
| PUT | `/api/admin/users/<id>/status` | admin | 切换状态 |
| DELETE | `/api/admin/users/<id>` | admin | 删除用户 |
| GET | `/api/admin/audit-logs` | admin | sys_audit_log |

### API 数据策略

- **实时计算**: `/api/metrics` (CTR/CVR/覆盖率/多样性/转化率), `/api/coldstart/stats` (策略分布), `/api/content/hot` (热度排行) 全部优先从 `rt_*` 表实时计算
- **WebSocket**: `dashboard_pusher.py` 每 5 秒推送全量快照 (在线用户/CTR/热度 Top5/趋势/聚类分布/策略分布/内容占比)
- **离线兜底**: `offline_metrics` 和 `offline_recommendations` 仅当 rt_* 数据缺失时作为备选

## Vue 路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 公开 |
| `/dashboard` | 数据大屏（4 Tab） | 需登录 |
| `/query` | 查询管理（3 Tab） | operator, admin |
| `/query/user/:id` | 用户画像详情 | operator, admin |
| `/admin` | 系统管理 | admin |

### Dashboard 4 Tab 数据源

| Tab | 图表 | 数据链路 |
|-----|------|----------|
| **实时监控** | 4 指标卡 + CTR趋势/热度Top10/热力图/行为日志 | WebSocket + /api/metrics + /api/content/hot + /api/region/heatmap |
| **趋势分析** | CTR趋势/热度Top10/占比环形图/曝光量趋势 | /api/metrics + WebSocket |
| **冷启动分析** | 4 指标卡 + 聚类饼图/转化漏斗 | /api/coldstart/stats + rt_coldstart_cluster |
| **推荐效果** | 4 指标卡 + 占比环形图/CTR趋势/热度Top10/策略分布/对比图 | WebSocket + /api/metrics + offline_recommendations |

## 关键设计决策

- **实时优先**: Metrics/Coldstart/Content API 全部优先从 rt_* 表实时计算, offline_* 仅作备选
- **冷启动阈值**: behavior_count ≤ 50 → 冷启动; ≤50 且 is_cold_start=0 → 探索; >50 → 存量
- **过渡期**: behavior_count ∈ [30, 80] → 冷启动与存量策略线性插值
- **音乐:视频比例**: 6:4 (冷启动默认), 根据 content_type_ratio 动态调整
- **ALS 参数**: rank=50, alpha=40.0, regParam=0.1, 隐式反馈
- **DPP 多样性**: theta=0.7, Top-100 → Top-50
- **ε-greedy**: ε=0.15
- **UserProfileAgg window_end**: 使用系统当前时间 (System.currentTimeMillis), 不再使用 Kafka 数据中的 event_time
- **Content Hot 去重**: API 层用 `MAX(hot_score) GROUP BY content_id, content_type` 去重, 避免多窗口重复
- **Chart 组件**: 使用 `setOption()` 增量更新, 不再每次 `dispose()` + `init()` 重建, 避免闪烁
- **WebSocket CTR 趋势**: 统一使用 row 级 CTR 公式 (active_rows / total_rows×10)，始终补全当天实时数据，不受 offline_metrics 行数限制
- **密码策略**: bcrypt cost=12 (可配), 8-64 位, 至少 3/4 字符类别
- **Spark 并行度**: `local[2]` (平衡性能与 MySQL 死锁风险)
- **Kafka 消费组**: `spark-streaming-consumer-v5` (避免旧 group offset 冲突)

## 模块间数据流

```
持续数据生成 (generate_data.py --continuous)
  │ 每秒 N 条, event_time=当前时间
  ▼
/opt/data-generator/output/*.log  ← Flume tail -F
  │
  ▼  Flume → Kafka (3 Topics)
  │
  ▼  Spark Streaming (10s 微批次, local[2])
  │  ├─ DataValidator → 解析 + 去重 + 死信路由
  │  ├─ UserProfileAgg → rt_user_profile (window_end=系统时间)
  │  ├─ ContentHotStats → rt_content_hot (1min 窗口)
  │  ├─ ColdStartCluster → rt_coldstart_cluster (K-Means)
  │  └─ MySQLBatchWriter → 批量写入 MySQL (INSERT IGNORE)
  │
  ▼  MySQL rt_* 表 (实时, 7天自动清理)
  │
  ├──→ Flask REST API (优先 rt_* 实时计算, offline_* 备选)
  │      │
  │      ▼  Vue SPA (HTTP 初始加载 + WebSocket 5s 增量推送)
  │
  └──→ Flask WebSocket (DashboardPusher: 5s 查询 rt_* 推全量快照)
         │
         ▼  Vue 大屏 (4 Tab, 全部实时更新)
```

### 实时 vs 离线职责

| 数据 | 实时 (Spark Streaming + Flask) | 离线 (SparkSQL) |
|------|-------------------------------|-----------------|
| CTR/CVR/覆盖率 | ✅ 从 rt_user_profile + rt_content_hot 实时计算 | 作为历史趋势备选 |
| 内容热度 | ✅ rt_content_hot, 1min 窗口, API 去重 | — |
| 冷启动统计 | ✅ 从 rt_user_profile + rt_coldstart_cluster 实时计算 | — |
| 推荐策略分布 | ✅ 从 rt_user_profile 三组实时统计 | offline_recommendations 备选 |
| 用户全量画像 | — | offline_user_portrait (128维) |
| 推荐列表 | — | offline_recommendations (需 Spark Offline) |
| 历史趋势 | — | offline_metrics (保留 90 天) |
