# CLAUDE.md — 基于 Spark 大数据的用户行为实时分析与混合推荐系统

> 版本：V1.5 / 日期：2026-06-19

## 项目概述

基于 Spark 大数据的用户行为实时分析与混合推荐系统。数据生成器 → Flume → Kafka 实时接入用户行为 → Spark Streaming 实时分析 → Flask API 实时查询 → Vue 数据大屏。SparkSQL 离线批处理生成推荐结果。

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

**环境**: Kafka、Flume、MySQL 运行在虚拟机 `192.168.88.134` 上（Python 3.11.7）。Flask 和 Vue 在本地 Windows 运行。Spark Streaming 在 Windows 本地运行。`start_app.bat` 使用 CRLF 换行符（Windows 兼容）。VM 远程控制通过 paramiko。

## 目录结构

```
E:\TraeBD\
├── pom.xml                     # Maven 父 POM（聚合 2 个 Scala 模块）
├── docs/                       # 设计文档（需求、架构、详细设计、分工）
├── sql/init.sql                # 数据库初始化（11 张表 + 存储过程 + 定时事件）
├── scripts/                    # 运维脚本（VM Python 升级、部署、数据库检查）
├── checkpoints/                # Spark Streaming checkpoint 目录（运行时生成）
├── start_app.bat               # Windows 端一键启动脚本 (Spark + Flask + Vue)
│
├── data-generator-vm/          # VM 端数据生成器（Python 3.11.7 f-string 版）
│   ├── generate_data.py        # 批量模式 + 持续会话模式（9 种行为序列）
│   ├── start_all_v2.sh         # 虚拟机一键启动 (Kafka + Flume + 持续数据生成)
│   ├── feed_data.sh            # 将 JSONL 文件 feed 到 Flume 源
│   ├── data/                   # 批量模式生成的 JSONL 数据文件
│   ├── output/                 # 持续模式日志输出（Flume tail -F 监控）
│   └── flume/                  # Flume 配置（flume.conf, flume-env.sh）
│
├── spark-streaming/            # Scala Maven 模块 — 实时分析
│   ├── pom.xml
│   └── src/main/
│       ├── resources/
│       │   ├── application.conf     # Kafka/MySQL 配置
│       │   └── log4j2.properties    # 日志配置
│       └── scala/com/recommend/streaming/
│           ├── Models.scala
│           ├── DataValidator.scala
│           ├── UserProfileAgg.scala
│           ├── ContentHotStats.scala
│           ├── ColdStartCluster.scala
│           ├── MySQLBatchWriter.scala
│           └── RealTimeAnalysisApp.scala
│
├── spark-offline/              # Scala Maven 模块 — 离线批处理
│   ├── pom.xml
│   └── src/main/scala/com/recommend/offline/
│       ├── Models.scala
│       ├── OfflineAnalysisApp.scala # 主入口: portrait | als-train | recommend | metrics | all（支持 --limit N）
│       ├── UserPortraitBuilder.scala
│       ├── ALSTrainer.scala
│       ├── ALSRecommender.scala
│       ├── HybridRecommender.scala # FR-08 三路分流混合推荐 + DPP 重排
│       └── MetricsCalculator.scala
│
├── flask-backend/              # Python — REST API + WebSocket
│   ├── app/
│   │   ├── extensions.py       # db, jwt, socketio + JWT blocklist（内存撤销）
│   │   ├── __init__.py         # create_app() 工厂
│   │   ├── auth/               # JWT 认证（HS256）+ bcrypt 密码
│   │   ├── permissions/        # RBAC 装饰器
│   │   ├── api/                # 查询接口（全优先 rt_* 实时计算）
│   │   │   ├── recommendations.py
│   │   │   ├── metrics.py
│   │   │   ├── content.py          # 含推荐理由字段（JOIN offline_recommendations）
│   │   │   ├── users.py
│   │   │   ├── coldstart.py
│   │   │   ├── region.py
│   │   │   └── admin.py
│   │   ├── models/             # SysUser, SysRole, SysUserRole, SysAuditLog
│   │   ├── export/             # CSV/Excel 导出
│   │   ├── websocket/          # DashboardPusher (5s 快照 + 活跃用户 + 地区分布) + EventLogPusher (内容标题缓存)
│   │   ├── email_service/
│   │   └── utils/
│   ├── config.py               # Dev/Test/Prod 配置（含 charset=utf8mb4）
│   ├── run.py                  # 入口 :5000
│   └── requirements.txt
│
└── vue-frontend/               # Vue 3 SPA
    ├── vite.config.js          # 代理 /api, /auth → :5000, /socket.io → :5000 (ws)
    └── src/
        ├── assets/styles/
        │   └── variables.css   # 暖色系 + 暗色模式 CSS 变量
        ├── views/              # login/, dashboard/, query/, admin/, content/
        ├── components/
        │   ├── common/         # ToastContainer, ConfirmDialog, AnimatedNumber, SkeletonCard/Table/Chart
        │   └── dashboard/      # MetricCard, TrendLineChart, HotBarChart, DonutChart, ClusterPieChart,
        │                       # FunnelChart, RegionHeatmap, ScrollLog, StrategyCompareChart, ContentCardGrid
        ├── stores/             # Pinia: auth.js, dashboard.js (applySnapshot), toast.js, confirm.js, theme.js
        ├── api/                # Axios（30s 超时, 401 refresh token 修复）
        ├── composables/        # useWebSocket（polling 模式）, useECharts
        └── router/             # beforeEach 守卫 (JWT + RBAC), /content/:id 路由
```

## 数据库（11 张表）

| 前缀 | 表名 | 用途 | 数据来源 |
|------|------|------|----------|
| `rt_` | user_profile | 用户实时画像（含 region 字段, window_end=系统时间） | Spark Streaming |
| `rt_` | content_hot | 内容实时热度 | Spark Streaming |
| `rt_` | coldstart_cluster | 冷启动聚类结果（8 个簇） | Spark Streaming |
| `offline_` | user_portrait | 用户全量画像（128 维向量） | SparkSQL 批处理 |
| `offline_` | recommendations | 推荐结果（三路分流+DPP 重排, 10,000 条） | SparkSQL 批处理 |
| `offline_` | metrics | 历史 CTR/CVR 指标 | 备选 |
| `sys_` | user, role, user_role | 用户+权限 (RBAC) | Flask |
| `sys_` | audit_log | 操作审计日志 | Flask |
| — | content_metadata | 内容元数据（标题/风格/标签/BPM, 10,180 条） | 数据生成器→Kafka→Spark |

### MySQL 索引

| 表 | 索引 | 用途 |
|----|------|------|
| rt_user_profile | idx_window_end (window_end) | 日期范围查询 |
| rt_user_profile | idx_cold_window (is_cold_start, window_end) | 冷启动筛选 |
| rt_user_profile | idx_user_window (user_id, window_end) | 用户最新窗口 |
| rt_content_hot | idx_hot_type (content_type, hot_score) | 热度排行 |
| rt_coldstart_cluster | idx_cluster_id (cluster_id) | 集群筛选 |

MySQL 连接: `app/app123@192.168.88.134:3306/recommend_db`（charset=utf8mb4）

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `Admin@123456` | 系统管理员 |

新用户可自行注册（默认 `end_user` 角色）。

## 快速启动（完整实时链路）

### 虚拟机端 (192.168.88.134)

```bash
# Python 3.11.7 已安装（python3 / python3.11），OpenSSL 1.1.1w, kafka-python 3.0.2

# 一键启动 Kafka + Flume + 持续数据生成（会话模式）
bash /opt/data-generator-vm/start_all_v2.sh      # 默认速率
bash /opt/data-generator-vm/start_all_v2.sh 5    # 每秒 5 events

# 停止 / 状态
bash /opt/data-generator-vm/start_all_v2.sh stop
bash /opt/data-generator-vm/start_all_v2.sh status

# 或通过 paramiko 远程控制:
python scripts/start_vm_pipeline.py
```

### Windows 端

```bash
# 一键启动 Spark Streaming + Flask + Vue
start_app.bat

# 或单独启动:
# Spark Offline（推荐结果落地，--limit 200）
spark-submit --class com.recommend.offline.OfflineAnalysisApp \
  --master local[2] --driver-memory 2g spark-offline/target/spark-offline-1.0.jar recommend --limit 200
```

**启动顺序**: 虚拟机先启动 (Kafka/MySQL/Flume/Generator), 然后 Windows 启动 (Spark/Flask/Vue)。

**前端**: `http://localhost:5173/dashboard`

## Flask API 路由

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/auth/login` | 公开 | 登录（返回 access + refresh token） |
| POST | `/auth/register` | 公开 | 注册 |
| POST | `/auth/logout` | JWT | 登出（token 撤销） |
| POST | `/auth/refresh` | JWT(refresh) | 刷新 access token（前端修复：正确传入 refresh token） |
| GET | `/api/health` | 公开 | 健康检查 |
| GET | `/api/recommendations` | operator, admin | 推荐列表（offline_ 优先 + rt_ 兜底） |
| GET | `/api/metrics` | operator, admin | 指标（rt_* 实时优先） |
| GET | `/api/content` | operator, admin | 内容列表 |
| GET | `/api/content/hot` | operator, admin | 热度排行（含 artist_or_author） |
| GET | `/api/content/<id>` | operator, admin | 内容详情（含热度+推荐理由+策略） |
| GET | `/api/users/profile` | operator, admin | 用户画像 |
| GET | `/api/coldstart/analysis` | operator, admin | 冷启动列表 |
| GET | `/api/coldstart/stats` | operator, admin | 冷启动统计 |
| GET | `/api/region/heatmap` | operator, admin | 地区热力图 |
| GET | `/api/export/<table>` | operator, admin | CSV/Excel 导出 |
| GET/PUT | `/api/settings` | admin | 系统设置 |
| GET/POST | `/api/users` | admin | 用户管理 |
| PUT | `/api/users/<id>` | admin | 编辑用户 |
| PUT | `/api/users/<id>/status` | admin | 切换状态 |
| DELETE | `/api/users/<id>` | admin | 删除用户 |
| GET | `/api/audit-logs` | admin | 审计日志 |

### WebSocket 推送字段

DashboardPusher 每 5 秒推送全量快照（18+ 字段）：
`online_users`, `daily_recommendations`, `ctr`, `avg_watch_duration`, `coverage`, `metrics_trend`, `ctr_trend`, `play_count_trend`, `coldstart_stats`, `funnel_data`, `compare_data`（含近 30 天回溯）, `hot_content_top5`（含 artist_or_author/tags/duration/bpm）, `cluster_distribution`, `strategy_distribution`, `content_ratio`, `region_distribution`（CN-XX→中文映射）, `active_users`（Top 10）

EventLogPusher 每 2 秒推送用户事件（含 content_title/content_artist）

## Vue 路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 公开 |
| `/dashboard` | 数据大屏（3 Tab + 全局指标栏） | 需登录 |
| `/query` | 查询管理（3 Tab） | operator, admin |
| `/query/user/:id` | 用户画像详情 | operator, admin |
| `/content/:id` | 内容详情（含推荐理由） | operator, admin |
| `/admin` | 系统管理 | admin |

### Dashboard 3 Tab

| Tab | 内容 |
|-----|------|
| **实时概览** | 区域热力图 + 实时行为日志 + 推荐内容 Top 7 + 热度 Top 10 |
| **效果分析** | CTR/曝光趋势 + 音乐视频占比 + 地区分布 + 策略分布 + 冷启vs存量对比 + 活跃用户 Top 10 |
| **冷启动分析** | 4 指标卡 + 聚类分布 + 转化漏斗 |

全局指标栏（5 指标 + 动画数字 + 异常检测 + 时效指示器）在顶栏下方始终可见，支持自动轮播。

### 查询管理 3 Tab

| Tab | 功能 |
|-----|------|
| **推荐列表** | 离线推荐 + 策略/关键词筛选, 排序, 导出 |
| **内容管理** | 热度排行, 关键词搜索, 详情抽屉 |
| **冷启动分析** | 冷启用户列表, 进度条, 集群筛选, 统计卡片 |

## 关键设计决策

- **VM Python 升级**: Python 3.6.8 → 3.11.7（源码编译，OpenSSL 1.1.1w），`python3` 默认 3.11.7
- **数据生成器**: 会话模式（9 种行为序列：探索浏览/深度消费/快速筛选/互动型等），~80% 冷启 + ~20% 存量
- **事件类型**: play/like/favorite/skip/complete/share/comment 7 种（权重均衡化）
- **content_metadata 表**: 10,180 条，含 artist_or_author 字段
- **offline_recommendations**: 10,000 条（coldstart 5125 + established 4875），支持推荐理由展示
- **Dashboard 布局**: 4 Tab → 3 Tab（合并趋势+推荐效果为效果分析），全局指标栏始终可见
- **WebSocket polling 模式**: Flask 开发服务器不支持原生 WebSocket，`transports: ["polling"]`
- **Region 数据贯通**: `UserBehaviorEvent.region` → `rt_user_profile.region` → 热力图 + 地区分布
- **冷启动去重**: `WHERE id IN (SELECT MAX(id) ... GROUP BY user_id)`
- **CTR 趋势统一公式**: `active_rows / (total_rows × 10)`
- **冷启动阈值**: behavior_count ≤ 50 → 冷启动; ≤50 且 is_cold_start=0 → 探索; >50 → 存量
- **存量对比兜底**: 当天无数据时回溯近 30 天，确保冷启/存量对比始终有数据
- **音乐:视频比例**: 6:4
- **DPP 多样性**: theta=0.7, Top-100 → Top-50
- **ε-greedy**: ε=0.15
- **JWT 安全**: 内存 blocklist 实现 token 撤销；access token 过期自动用 refresh token 续期
- **MySQL 连接**: Flask `charset=utf8mb4`，连接池 `pool_pre_ping=True`
- **Spark 恢复**: `StreamingContext.getOrCreate()` + Kafka offset 提交
- **Spark 并行度**: `local[2]`
- **Kafka 消费组**: `spark-streaming-consumer-v5`
- **UI 设计系统**: 暖色系 + 暗色模式（CSS 变量切换），毛玻璃效果，动画数字过渡，骨架屏加载
- **前端全局组件**: Toast 通知、Confirm 确认弹窗、AnimatedNumber、SkeletonCard/Table/Chart
- **VM 部署**: `data-generator-vm/` Python 3.11.7 兼容版（f-string），路径全部指向 `/opt/data-generator-vm/`
- **VM 远程控制**: paramiko 脚本（`scripts/` 目录）, 无需手动 SSH

## 模块间数据流

```
数据生成器 (generate_data.py --continuous, 会话模式)
  │ 每秒 N events, 会话序列（2-6 events/session）
  ▼
/opt/data-generator-vm/output/*.log  ← Flume tail -F
  │
  ▼  Flume → Kafka (3 Topics)
  │
  ▼  Spark Streaming (10s 微批次, local[2])
  │  ├─ DataValidator → 解析 + 去重 + 死信路由
  │  ├─ UserProfileAgg → rt_user_profile (含 region)
  │  ├─ ContentHotStats → rt_content_hot (1min 窗口)
  │  ├─ ColdStartCluster → rt_coldstart_cluster (K-Means)
  │  └─ MySQLBatchWriter → 批量写入 MySQL
  │
  ▼  MySQL（实时 rt_* + 离线 offline_*）
  │
  ├──→ SparkSQL 离线批处理
  │     └─ HybridRecommender → offline_recommendations (10,000 条)
  │
  ├──→ Flask REST API (优先 rt_* 实时计算)
  │      │
  │      ▼  Vue SPA (HTTP + WebSocket 5s 快照, 暖色 UI + 暗色模式)
  │
  └──→ Flask WebSocket
         ├─ DashboardPusher: 5s 全量快照（18+ 字段）
         └─ EventLogPusher: 2s 用户事件（含内容标题）
              │
              ▼  Vue 大屏 (3 Tab + 全局指标栏, 自动轮播)
```

### 实时 vs 离线职责

| 数据 | 实时 (Spark Streaming + Flask) | 离线 (SparkSQL) |
|------|-------------------------------|-----------------|
| CTR/CVR/覆盖率 | ✅ 从 rt_user_profile + rt_content_hot 实时计算 | 历史趋势备选 |
| 内容热度 | ✅ rt_content_hot, 1min 窗口 | — |
| 冷启动统计 | ✅ rt_user_profile + rt_coldstart_cluster | — |
| 推荐策略分布 | ✅ rt_user_profile 三组统计 | offline_recommendations 备选 |
| 地区热力图 | ✅ rt_user_profile.region | — |
| 地区分布 | ✅ rt_user_profile.region（CN-XX→中文） | — |
| 活跃用户排行 | ✅ rt_user_profile 播放量排序 | — |
| 冷启 vs 存量对比 | ✅ rt_user_profile（近 30 天回溯） | offline_metrics 兜底 |
| 用户全量画像 | — | offline_user_portrait (128维) |
| 推荐列表 | — | offline_recommendations (10,000 条) |
| 推荐理由 | — | offline_recommendations (strategy/score/reason) |
| 历史趋势 | — | offline_metrics (保留 90 天) |
