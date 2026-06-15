# CLAUDE.md — 冷启动音乐与视频混合推荐系统

> 版本：V1.4 / 日期：2026-06-15

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
│   ├── start_all_v2.sh         # 虚拟机一键启动 (Kafka + Flume + 持续数据生成)
│   ├── feed_data.sh            # 将 JSONL 文件 feed 到 Flume 源
│   ├── data/                   # 批量模式生成的 JSONL 数据文件
│   └── flume/                  # Flume 配置（flume.conf, flume-env.sh）
│
├── data-generator-vm/          # VM 部署副本（Python 3.6.8 兼容版）
│   ├── generate_data.py        # 纯数字 ID + .format() 字符串
│   ├── start_all_v2.sh         # 使用 /usr/bin/python3 绝对路径
│   └── flume/                  # 同上
│
├── spark-streaming/            # Scala Maven 模块 — 实时分析
│   ├── pom.xml
│   └── src/main/
│       ├── resources/
│       │   ├── application.conf     # Kafka/MySQL 配置（密码可用 MYSQL_PASSWORD 环境变量覆盖）
│       │   └── log4j2.properties    # 日志配置（文件滚动 + 控制台输出）
│       └── scala/com/recommend/streaming/
│           ├── Models.scala         # case class (UserBehaviorEvent, ContentMetaEvent, RegisterEvent, UserProfile, ContentHot, ClusterResult)
│           ├── DataValidator.scala  # FR-02 JSON 解析 + 去重 + 死信路由（DLQ生产者自动关闭）
│           ├── UserProfileAgg.scala # FR-03 用户画像 (5min滑动窗口, windowEnd=系统时间, 含 region 提取)
│           ├── ContentHotStats.scala # FR-04 内容热度 (1min滚动窗口)
│           ├── ColdStartCluster.scala # FR-05 冷启动 K-Means 聚类（单批>5000条自动截断）
│           ├── MySQLBatchWriter.scala # 批量写入 rt_* + content_metadata（事务+3次重试, region 字段）
│           └── RealTimeAnalysisApp.scala # 主入口（getOrCreate恢复+offset提交+优雅关闭）
│
├── spark-offline/              # Scala Maven 模块 — 离线批处理
│   ├── pom.xml
│   └── src/main/scala/com/recommend/offline/
│       ├── Models.scala
│       ├── OfflineAnalysisApp.scala # 主入口: portrait | als-train | recommend | metrics | all（支持 --limit N）
│       ├── UserPortraitBuilder.scala # FR-06 用户全量画像
│       ├── ALSTrainer.scala    # ALS 模型训练 (隐式反馈)
│       ├── ALSRecommender.scala # ALS 批量推荐推理
│       ├── HybridRecommender.scala # FR-08 三路分流混合推荐 + DPP 重排（支持 maxUsers 限制）
│       └── MetricsCalculator.scala # FR-09 推荐效果指标
│
├── flask-backend/              # Python — REST API + WebSocket
│   ├── app/
│   │   ├── extensions.py       # db, jwt, socketio + JWT blocklist（内存撤销）
│   │   ├── __init__.py         # create_app() 工厂 + 文件日志 + token 回收注册
│   │   ├── auth/               # 注册/登录/登出(真撤销)/刷新/邮箱验证 (bcrypt + JWT HS256)
│   │   ├── permissions/        # @require_role(*roles) 装饰器 (RBAC)
│   │   ├── api/                # 查询接口 (全优先 rt_* 实时计算)
│   │   │   ├── recommendations.py  # 推荐列表（离线优先 + 实时兜底 + 关键词/策略筛选 + 排序）
│   │   │   ├── metrics.py          # 指标（一次查询多分组聚合，索引友好日期区间）
│   │   │   ├── content.py          # 内容列表 + 热门（关键词搜索, 扩展字段）
│   │   │   ├── users.py            # 用户画像 (JOIN rt_ + offline_)
│   │   │   ├── coldstart.py        # 冷启动分析 + 统计（转化率/策略分布 实时, 去重, 进度, 集群名称）
│   │   │   ├── region.py           # 地区热力图（基于 rt_user_profile.region 真实数据）
│   │   │   └── admin.py            # 用户管理 + 审计日志 + 系统设置
│   │   ├── models/             # SysUser, SysRole, SysUserRole, SysAuditLog
│   │   ├── export/             # CSV/Excel 导出
│   │   ├── websocket/          # DashboardPusher (5s 推送全量快照) + EventLogPusher
│   │   ├── email_service/      # SMTP 邮件验证码
│   │   └── utils/              # validators, error_handlers(全局DB+Exception), audit(flush非commit), cluster_utils
│   ├── config.py               # Dev/Test/Prod 配置（敏感信息走环境变量）
│   ├── run.py                  # 入口 :5000
│   ├── requirements.txt
│   └── .env.example            # 环境变量模板
│
└── vue-frontend/               # Vue 3 SPA
    ├── vite.config.js          # 代理 /api, /auth → :5000, /socket.io → :5000 (ws)
    └── src/
        ├── assets/styles/
        │   └── variables.css   # 暖色系设计系统（Coral/Amber/Gold/Rose/Teal/Indigo/Plum）
        ├── views/              # login/, dashboard/, query/, admin/
        ├── components/
        │   ├── common/         # Paginator, DatePicker
        │   └── dashboard/      # MetricCard, TrendLineChart, HotBarChart, DonutChart, ClusterPieChart, FunnelChart, RegionHeatmap, ScrollLog, StrategyCompareChart
        ├── stores/             # Pinia: auth.js（JWT exp 检查）, dashboard.js（applySnapshot 统一数据入口）
        ├── api/                # Axios（30s 超时, 401 自动刷新, 登录 username 字段修复）
        ├── composables/        # useWebSocket（polling 模式）, useECharts
        └── router/             # beforeEach 守卫 (JWT + RBAC)
```

## 数据库（11 张表）

| 前缀 | 表名 | 用途 | 数据来源 |
|------|------|------|----------|
| `rt_` | user_profile | 用户实时画像（含 region 字段, window_end=系统时间） | Spark Streaming |
| `rt_` | content_hot | 内容实时热度（去重查询用 MAX+GROUP BY） | Spark Streaming |
| `rt_` | coldstart_cluster | 冷启动聚类结果（8 个簇） | Spark Streaming |
| `offline_` | user_portrait | 用户全量画像（128 维向量） | SparkSQL 批处理 |
| `offline_` | recommendations | 推荐结果（三路分流+DPP 重排） | SparkSQL / 实时计算 |
| `offline_` | metrics | 历史 CTR/CVR 指标（已改为备选） | 实时 rt_* 优先, offline_ 备选 |
| `sys_` | user, role, user_role | 用户+权限 (RBAC) | Flask |
| `sys_` | audit_log | 操作审计日志 | Flask |
| — | content_metadata | 内容元数据（标题/风格/标签/BPM） | 数据生成器→Kafka→Spark |

> `offline_content_sim` 表及 SimilarityMatrix 代码已删除。HybridRecommender 内部实现 DPP 多样性重排，不再依赖预计算相似度矩阵。

### MySQL 索引

| 表 | 索引 | 用途 |
|----|------|------|
| rt_user_profile | idx_window_end (window_end) | 日期范围查询加速 |
| rt_user_profile | idx_cold_window (is_cold_start, window_end) | 冷启动筛选加速 |
| rt_user_profile | idx_user_window (user_id, window_end) | 用户最新窗口子查询加速 |
| rt_content_hot | idx_hot_type (content_type, hot_score) | 热度排行加速 |
| rt_coldstart_cluster | idx_cluster_id (cluster_id) | 集群筛选加速 |

MySQL 连接: `app/app123@192.168.88.134:3306/recommend_db`

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `Admin@123456` | 系统管理员 |

新用户可自行注册（默认 `end_user` 角色）。

## 快速启动（完整实时链路）

### 虚拟机端 (192.168.88.134)

```bash
# 一键启动 Kafka + Flume + 持续数据生成
bash /opt/data-generator-vm/start_all_v2.sh

# 可指定速率 (默认每秒 3 条)
bash /opt/data-generator-vm/start_all_v2.sh 10

# 停止
bash /opt/data-generator-vm/start_all_v2.sh stop

# 查看状态
bash /opt/data-generator-vm/start_all_v2.sh status
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
mvn package -pl spark-streaming -am -DskipTests

# Spark Streaming 单独启动
spark-submit --class com.recommend.streaming.RealTimeAnalysisApp \
  --master local[2] spark-streaming/target/spark-streaming-1.0-shaded.jar

# Spark Offline 批处理 (可选, 需要 Spark 空闲时运行, --limit N 限制用户数)
spark-submit --class com.recommend.offline.OfflineAnalysisApp \
  --master local[2] --driver-memory 2g spark-offline/target/spark-offline-1.0.jar [job] [--limit N]
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
| GET | `/api/recommendations` | operator, admin | offline_ 优先 + rt_content_hot 兜底（支持 keyword/strategy/sort_by） |
| GET | `/api/metrics` | operator, admin | **rt_* 实时优先**（单查询多分组聚合） |
| GET | `/api/content` | operator, admin | rt_content_hot（支持 keyword 搜索） |
| GET | `/api/content/hot` | operator, admin | rt_content_hot (MAX+GROUP BY 去重) |
| GET | `/api/content/<id>` | operator, admin | content_metadata |
| GET | `/api/users/profile` | operator, admin | rt_user_profile + offline_user_portrait |
| GET | `/api/users/profile/<id>` | operator, admin | 同上 |
| GET | `/api/coldstart/analysis` | operator, admin | rt_user_profile 冷启列表（去重, 集群名称, 进度, 支持 time_filter/cluster_id/sort_by） |
| GET | `/api/coldstart/stats` | operator, admin | **rt_* 实时计算**（单查询统计, 集群名称映射） |
| GET | `/api/region/heatmap` | operator, admin | rt_user_profile.region（真实地区数据, 用户数/播放数/冷启比） |
| GET | `/api/export/<table>` | operator, admin | CSV/Excel 导出 |
| GET/PUT | `/api/settings` | admin | 系统设置 |
| GET/POST | `/api/users` | admin | 用户管理（列表+创建） |
| PUT | `/api/users/<id>` | admin | 编辑用户 |
| PUT | `/api/users/<id>/status` | admin | 切换状态 |
| DELETE | `/api/users/<id>` | admin | 删除用户 |
| GET | `/api/audit-logs` | admin | sys_audit_log |

### API 数据策略

- **实时计算**: `/api/metrics` (CTR/CVR/覆盖率/多样性/转化率), `/api/coldstart/stats` (策略分布), `/api/content/hot` (热度排行), `/api/region/heatmap` (地区分布) 全部优先从 `rt_*` 表实时计算
- **WebSocket**: `dashboard_pusher.py` 每 5 秒推全量快照，前端通过 `applySnapshot()` 统一入口接收，`normalizeSnapshot()` 做 snake_case→camelCase 映射
- **数据契约**: 前端 `stores/dashboard.js` 中的 `normalizeSnapshot()` 是所有 WebSocket 数据的唯一映射入口
- **CTR 趋势统一公式**: 全部使用 row-level 公式 `active_rows / (total_rows × 10)`
- **离线兜底**: `offline_metrics` 和 `offline_recommendations` 仅当 rt_* 数据缺失时作为备选
- **前端 axios**: 超时 30s, 401 自动 refresh token, GET 5xx 自动重试 2 次

## Vue 路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 公开 |
| `/dashboard` | 数据大屏（4 Tab） | 需登录 |
| `/query` | 查询管理（3 Tab） | operator, admin |
| `/query/user/:id` | 用户画像详情 | operator, admin |
| `/admin` | 系统管理（用户管理+设置+审计） | admin |

### Dashboard 4 Tab 数据源

所有 4 个 Tab 的数据均由 WebSocket 每 5 秒全量推送（polling 模式），API 仅在页面初始加载时提供首屏数据。

| Tab | 图表 | 数据来源 |
|-----|------|----------|
| **实时监控** | 4 指标卡 + CTR趋势/热度Top10/热力图/行为日志 | WebSocket（热力图除外，仅 API 加载） |
| **趋势分析** | CTR趋势/热度Top10/占比环形图/曝光量趋势 | WebSocket |
| **冷启动分析** | 4 指标卡 + 聚类饼图/转化漏斗 | WebSocket |
| **推荐效果** | 4 指标卡 + 占比环形图/CTR趋势/热度Top10/策略分布/对比图 | WebSocket |

### 查询管理 3 Tab

| Tab | 功能 | 数据来源 |
|-----|------|----------|
| **推荐列表** | 离线推荐 + 实时热度兜底, 策略筛选, 关键词搜索, 排序 | offline_recommendations / rt_content_hot |
| **内容管理** | 热度排行, 关键词搜索, 详情抽屉 | rt_content_hot |
| **冷启动分析** | 冷启用户列表(去重), 进度条, 集群名称下拉, 时间筛选, 排序, 统计卡片 | rt_user_profile + rt_coldstart_cluster |

## 关键设计决策

- **WebSocket polling 模式**: Flask 开发服务器不支持原生 WebSocket，前端 `transports: ["polling"]` 降级为 HTTP 长轮询
- **Region 数据贯通**: `UserBehaviorEvent.region` → `UserProfileAgg.calcRegion()` → `rt_user_profile.region` → 热力图真实地理分布
- **冷启动去重**: `coldstart/analysis` 使用 `WHERE id IN (SELECT MAX(id) ... GROUP BY user_id)` 子查询确保每用户一条
- **API SQL 优化**: metrics 从每日期 12+ 查询合并为 2 查询（一次多分组聚合 + 一次转化率）；日期用 `>= d AND < next_day` 利用索引
- **查询管理关键词搜索**: content 和 recommendations 支持 `keyword` 参数搜索 title/artist/tags
- **WebSocket 全量推送**: DashboardPusher 每 5s 推送覆盖所有卡片，API 仅首屏加载
- **实时优先**: Metrics/Coldstart/Content API 全部优先从 rt_* 表实时计算, offline_* 仅作备选
- **CTR 趋势统一**: rt 数据优先覆盖 offline，全部使用 row-level 公式 `active_rows / (total_rows × 10)`
- **数据契约层**: 前端 `stores/dashboard.js` 中 `applySnapshot()` → `normalizeSnapshot()` 集中处理 snake_case→camelCase 映射
- **冷启动阈值**: behavior_count ≤ 50 → 冷启动; ≤50 且 is_cold_start=0 → 探索; >50 → 存量
- **过渡期**: behavior_count ∈ [30, 80] → 冷启动与存量策略线性插值
- **音乐:视频比例**: 6:4 (冷启动默认), 根据 content_type_ratio 动态调整
- **ALS 参数**: rank=50, alpha=40.0, regParam=0.1, 隐式反馈（模型待训练）
- **DPP 多样性**: theta=0.7, Top-100 → Top-50
- **ε-greedy**: ε=0.15
- **UserProfileAgg window_end**: 使用系统当前时间 (System.currentTimeMillis), 不再使用 Kafka 数据中的 event_time
- **Content Hot 去重**: API 层用 `MAX(hot_score) GROUP BY content_id, content_type` 去重, 避免多窗口重复
- **Chart 组件**: 使用 `setOption()` 增量更新, 不再每次 `dispose()` + `init()` 重建, 避免闪烁
- **JWT 安全**: 内存 blocklist 实现 token 撤销，登出后立即失效；前端 isAuthenticated 检查 exp 过期时间
- **配置安全**: 敏感信息（密钥/密码）走环境变量，开发环境有固定默认值，生产环境强制 env var
- **Spark 恢复**: `StreamingContext.getOrCreate()` + Kafka offset 提交，重启不丢状态不重放
- **Spark Offline limit**: `OfflineAnalysisApp` 支持 `--limit N` 参数限制处理用户数
- **MySQL 写入**: JDBC 事务包装（`autoCommit=false` + `commit/rollback`）+ 3 次重试递增延迟
- **数据库连接**: Flask 连接池 `pool_pre_ping=True`，后台 pusher 每次轮询后 `session.remove()` 防泄漏
- **全局异常**: Flask 注册 `SQLAlchemyError` handler（回滚+error_id）+ 通用 `Exception` handler
- **密码策略**: bcrypt cost=12 (可配), 8-64 位, 至少 3/4 字符类别
- **Spark 并行度**: `local[2]` (平衡性能与 MySQL 死锁风险)
- **Kafka 消费组**: `spark-streaming-consumer-v5` (避免旧 group offset 冲突)
- **UI 设计系统**: 暖色系（Coral/Amber/Gold/Rose/Teal/Indigo/Plum），渐变卡片，磨砂玻璃效果，彩色 accent 顶条
- **VM 部署**: `data-generator-vm/` 包含 Python 3.6.8 兼容版脚本（.format() 替代 f-string），`start_all_v2.sh` 使用 `/usr/bin/python3` 绝对路径

## 模块间数据流

```
持续数据生成 (generate_data.py --continuous)
  │ 每秒 N 条, user_id/content_id 为纯数字字符串, region 为 CN-XX
  ▼
/opt/data-generator/output/*.log  ← Flume tail -F
  │
  ▼  Flume → Kafka (3 Topics)
  │
  ▼  Spark Streaming (10s 微批次, local[2])
  │  ├─ DataValidator → 解析 + 去重 + 死信路由
  │  ├─ UserProfileAgg → rt_user_profile (window_end=系统时间, 含 region)
  │  ├─ ContentHotStats → rt_content_hot (1min 窗口)
  │  ├─ ColdStartCluster → rt_coldstart_cluster (K-Means)
  │  └─ MySQLBatchWriter → 批量写入 MySQL (事务+3次重试)
  │
  ▼  MySQL rt_* 表 (实时, 7天自动清理)
  │
  ├──→ Flask REST API (优先 rt_* 实时计算, 索引优化, polling WebSocket)
  │      │
  │      ▼  Vue SPA (HTTP 初始加载 + WebSocket 5s 增量推送, 暖色 UI)
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
| 地区热力图 | ✅ 从 rt_user_profile.region 真实聚合 | — |
| 用户全量画像 | — | offline_user_portrait (128维) |
| 推荐列表 | — | offline_recommendations（需 Spark Offline，ALS 模型待训练） |
| 历史趋势 | — | offline_metrics (保留 90 天) |
