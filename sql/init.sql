-- ============================================================================
-- 冷启动音乐与视频混合推荐系统 — 数据库初始化脚本
-- 版本: V1.0  日期: 2026-05-29
-- 兼容: MySQL 8.0+
-- ============================================================================

CREATE DATABASE IF NOT EXISTS recommend_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE recommend_db;

-- ============================================================================
-- 第一部分: 实时表 (rt_) — Spark Streaming 写入, 保留 7 天
-- ============================================================================

-- --------------------------------------------------------------------------
-- rt_user_profile — 用户实时行为画像
-- FR-03: UserProfileAgg 聚合输出
-- --------------------------------------------------------------------------
CREATE TABLE rt_user_profile (
    id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id               BIGINT UNSIGNED NOT NULL,
    window_start          DATETIME(3) NOT NULL,
    window_end            DATETIME(3) NOT NULL,
    play_count            INT UNSIGNED DEFAULT 0,
    completion_rate       DECIMAL(5,4) DEFAULT 0.0000,
    like_rate             DECIMAL(5,4) DEFAULT 0.0000,
    favorite_rate         DECIMAL(5,4) DEFAULT 0.0000,
    skip_rate             DECIMAL(5,4) DEFAULT 0.0000,
    share_count           INT UNSIGNED DEFAULT 0,
    comment_count         INT UNSIGNED DEFAULT 0,
    preference_distribution JSON DEFAULT NULL,
    active_hours          JSON DEFAULT NULL,
    is_cold_start         TINYINT(1) DEFAULT 1,
    behavior_count        INT UNSIGNED DEFAULT 0,
    content_type_ratio    JSON DEFAULT NULL,
    extended_attrs        JSON DEFAULT NULL,
    created_at            DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id),
    INDEX idx_window_start (window_start),
    INDEX idx_is_cold_start (is_cold_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- rt_content_hot — 内容实时热度
-- FR-04: ContentHotStats 聚合输出
-- --------------------------------------------------------------------------
CREATE TABLE rt_content_hot (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    content_id       BIGINT UNSIGNED NOT NULL,
    content_type     ENUM('music','video') NOT NULL,
    play_count       BIGINT UNSIGNED DEFAULT 0,
    like_count       BIGINT UNSIGNED DEFAULT 0,
    favorite_count   BIGINT UNSIGNED DEFAULT 0,
    share_count      BIGINT UNSIGNED DEFAULT 0,
    completion_rate  DECIMAL(5,4) DEFAULT 0.0000,
    interaction_rate DECIMAL(5,4) DEFAULT 0.0000,
    hot_score        DECIMAL(10,4) DEFAULT 0.0000,
    window_start     DATETIME(3) NOT NULL,
    window_end       DATETIME(3) NOT NULL,
    extended_attrs   JSON DEFAULT NULL,
    created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    INDEX idx_content (content_id, content_type),
    INDEX idx_hot_score (hot_score DESC),
    INDEX idx_window (window_start, window_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- rt_coldstart_cluster — 冷启动用户聚类结果
-- FR-05: ColdStartCluster K-Means 聚类输出
-- --------------------------------------------------------------------------
CREATE TABLE rt_coldstart_cluster (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id          BIGINT UNSIGNED NOT NULL,
    cluster_id       TINYINT UNSIGNED NOT NULL,
    cluster_center   JSON NOT NULL,
    cluster_size     INT UNSIGNED DEFAULT 0,
    device_type      VARCHAR(32) DEFAULT NULL,
    register_channel VARCHAR(64) DEFAULT NULL,
    interest_tags    JSON DEFAULT NULL,
    compute_time     DATETIME(3) NOT NULL,
    extended_attrs   JSON DEFAULT NULL,
    created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id),
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_compute_time (compute_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 第二部分: 离线表 (offline_) — SparkSQL 批量写入, 保留 90 天
-- ============================================================================

-- --------------------------------------------------------------------------
-- offline_user_portrait — 用户全量画像
-- FR-06: UserPortraitBuilder 输出
-- --------------------------------------------------------------------------
CREATE TABLE offline_user_portrait (
    id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id              BIGINT UNSIGNED NOT NULL,
    long_term_tags       JSON DEFAULT NULL,
    preference_vector    JSON NOT NULL,
    lifecycle_stage      ENUM('new','active','silent','churned') NOT NULL DEFAULT 'new',
    total_behaviors      INT UNSIGNED DEFAULT 0,
    avg_session_duration DECIMAL(10,2) DEFAULT 0.00,
    active_days_last_30  TINYINT UNSIGNED DEFAULT 0,
    last_active_time     DATETIME(3) DEFAULT NULL,
    favorite_content_type ENUM('music','video','mixed') DEFAULT 'mixed',
    cluster_id           TINYINT UNSIGNED DEFAULT NULL,
    tag_version          VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    compute_time         DATETIME(3) NOT NULL,
    extended_attrs       JSON DEFAULT NULL,
    created_at           DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at           DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id),
    INDEX idx_lifecycle (lifecycle_stage),
    INDEX idx_favorite_type (favorite_content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- offline_recommendations — 离线推荐结果
-- FR-08: HybridRecommender 混合推荐输出
-- --------------------------------------------------------------------------
CREATE TABLE offline_recommendations (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id        BIGINT UNSIGNED NOT NULL,
    content_id     BIGINT UNSIGNED NOT NULL,
    content_type   ENUM('music','video') NOT NULL,
    `rank`         TINYINT UNSIGNED NOT NULL,
    score          DECIMAL(10,6) NOT NULL,
    strategy       VARCHAR(32) NOT NULL,
    reason         VARCHAR(128) DEFAULT NULL,
    batch_id       VARCHAR(64) NOT NULL,
    compute_time   DATETIME(3) NOT NULL,
    expire_time    DATETIME(3) NOT NULL,
    extended_attrs JSON DEFAULT NULL,
    created_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    INDEX idx_user_rank (user_id, `rank`),
    INDEX idx_batch (batch_id),
    INDEX idx_expire (expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- offline_metrics — 推荐效果指标
-- FR-09: MetricsCalculator 每日指标计算输出
-- --------------------------------------------------------------------------
CREATE TABLE offline_metrics (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    metric_date         DATE NOT NULL,
    user_group          ENUM('coldstart','existing','all') NOT NULL,
    content_type        ENUM('music','video','mixed','all') NOT NULL,
    ctr                 DECIMAL(6,4) DEFAULT NULL,
    cvr                 DECIMAL(6,4) DEFAULT NULL,
    avg_watch_duration  DECIMAL(10,2) DEFAULT NULL,
    avg_interactions    DECIMAL(6,2) DEFAULT NULL,
    coverage            DECIMAL(6,4) DEFAULT NULL,
    diversity           DECIMAL(6,4) DEFAULT NULL,
    coldstart_conversion DECIMAL(6,4) DEFAULT NULL,
    total_impressions   BIGINT UNSIGNED DEFAULT 0,
    total_clicks        BIGINT UNSIGNED DEFAULT 0,
    total_users         INT UNSIGNED DEFAULT 0,
    compute_time        DATETIME(3) NOT NULL,
    created_at          DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_date_group_type (metric_date, user_group, content_type),
    INDEX idx_metric_date (metric_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 第三部分: 系统表 (sys_) — Flask 应用读写, 永久保留
-- ============================================================================

-- --------------------------------------------------------------------------
-- sys_user — 系统用户
-- --------------------------------------------------------------------------
CREATE TABLE sys_user (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
    username       VARCHAR(64) NOT NULL,
    email          VARCHAR(128) NOT NULL,
    password_hash  VARCHAR(256) NOT NULL COMMENT 'bcrypt hash, cost=12',
    is_active      TINYINT(1) NOT NULL DEFAULT 1,
    is_verified    TINYINT(1) NOT NULL DEFAULT 0,
    last_login_at  DATETIME(3) DEFAULT NULL,
    created_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- sys_role — 角色定义 (RBAC)
-- --------------------------------------------------------------------------
CREATE TABLE sys_role (
    id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(32) NOT NULL,
    description VARCHAR(128) DEFAULT NULL,
    created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- sys_user_role — 用户-角色关联
-- --------------------------------------------------------------------------
CREATE TABLE sys_user_role (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     INT UNSIGNED NOT NULL,
    role_id     TINYINT UNSIGNED NOT NULL,
    assigned_by INT UNSIGNED DEFAULT NULL COMMENT '分配者 user_id',
    assigned_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_role (user_id, role_id),
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES sys_role(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------------
-- sys_audit_log — 操作审计日志
-- --------------------------------------------------------------------------
CREATE TABLE sys_audit_log (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    operator_id INT UNSIGNED NOT NULL,
    action      VARCHAR(64) NOT NULL COMMENT '操作类型: user.create, user.disable, role.assign, config.update',
    target      VARCHAR(128) NOT NULL COMMENT '操作对象: user:123, role:2',
    detail      JSON DEFAULT NULL COMMENT '操作详情 JSON',
    ip_address  VARCHAR(45) DEFAULT NULL,
    created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    INDEX idx_operator_time (operator_id, created_at DESC),
    INDEX idx_action (action),
    FOREIGN KEY (operator_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 第四部分: 初始数据
-- ============================================================================

INSERT INTO sys_role (name, description) VALUES
('end_user', '终端用户 — 消费推荐内容'),
('operator', '运营人员 — 查看数据大屏，查询分析结果，导出报表'),
('admin',    '系统管理员 — 用户管理，权限分配，系统配置');

-- 创建默认管理员 (密码: Admin@123456, bcrypt cost=12)
-- 生产环境请务必修改密码
INSERT INTO sys_user (username, email, password_hash, is_active, is_verified) VALUES
('admin', 'admin@recommend.local', '$2b$12$LJ3m4ys3Lk0TSwHBqExrJOvHGcJ0FmzCDhJbY3V0zPxMr1CH0yQPC', 1, 1);

-- 赋予 admin 用户 admin 角色
INSERT INTO sys_user_role (user_id, role_id, assigned_by) VALUES
(1, 3, 1);

-- ============================================================================
-- 第五部分: 数据清理存储过程
-- ============================================================================

DELIMITER //

-- 清理 7 天前的实时表数据
CREATE PROCEDURE clean_realtime_tables()
BEGIN
    DELETE FROM rt_user_profile    WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
    DELETE FROM rt_content_hot     WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
    DELETE FROM rt_coldstart_cluster WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
END //

-- 清理离线推荐表, 仅保留最近 3 个批次
CREATE PROCEDURE clean_offline_recommendations()
BEGIN
    DELETE FROM offline_recommendations
    WHERE batch_id NOT IN (
        SELECT batch_id FROM (
            SELECT batch_id FROM offline_recommendations
            GROUP BY batch_id ORDER BY MAX(compute_time) DESC LIMIT 3
        ) AS recent
    );
END //

-- 清理 90 天前的离线表数据
CREATE PROCEDURE clean_offline_tables()
BEGIN
    DELETE FROM offline_user_portrait WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
    DELETE FROM offline_metrics       WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
END //

-- 清理 180 天前的审计日志
CREATE PROCEDURE clean_audit_logs()
BEGIN
    DELETE FROM sys_audit_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 180 DAY);
END //

-- 一键清理所有过期数据
CREATE PROCEDURE clean_all_expired()
BEGIN
    CALL clean_realtime_tables();
    CALL clean_offline_recommendations();
    CALL clean_offline_tables();
    CALL clean_audit_logs();
END //

DELIMITER ;

-- ============================================================================
-- 第六部分: 定时清理事件 (MySQL Event Scheduler)
-- ============================================================================

SET GLOBAL event_scheduler = ON;

-- 每日 03:00 清理实时表
CREATE EVENT IF NOT EXISTS evt_clean_realtime
ON SCHEDULE EVERY 1 DAY STARTS CONCAT(CURRENT_DATE, ' 03:00:00')
DO CALL clean_realtime_tables();

-- 每日 04:00 清理离线表
CREATE EVENT IF NOT EXISTS evt_clean_offline
ON SCHEDULE EVERY 1 DAY STARTS CONCAT(CURRENT_DATE, ' 04:00:00')
DO CALL clean_offline_tables();

-- 每日 04:30 清理过期推荐批次
CREATE EVENT IF NOT EXISTS evt_clean_recommendations
ON SCHEDULE EVERY 1 DAY STARTS CONCAT(CURRENT_DATE, ' 04:30:00')
DO CALL clean_offline_recommendations();

-- 每周日 05:00 清理审计日志
CREATE EVENT IF NOT EXISTS evt_clean_audit
ON SCHEDULE EVERY 1 WEEK STARTS CONCAT(DATE_ADD(CURRENT_DATE, INTERVAL (7 - WEEKDAY(CURRENT_DATE)) DAY), ' 05:00:00')
DO CALL clean_audit_logs();
