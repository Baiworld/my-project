USE recommend_db;

CREATE TABLE IF NOT EXISTS offline_user_portrait (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    long_term_tags JSON DEFAULT NULL,
    preference_vector JSON NOT NULL,
    lifecycle_stage ENUM('new','active','silent','churned') NOT NULL DEFAULT 'new',
    total_behaviors INT UNSIGNED DEFAULT 0,
    avg_session_duration DECIMAL(10,2) DEFAULT 0.00,
    active_days_last_30 TINYINT UNSIGNED DEFAULT 0,
    last_active_time DATETIME(3) DEFAULT NULL,
    favorite_content_type ENUM('music','video','mixed') DEFAULT 'mixed',
    cluster_id TINYINT UNSIGNED DEFAULT NULL,
    tag_version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    compute_time DATETIME(3) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id),
    INDEX idx_lifecycle (lifecycle_stage),
    INDEX idx_favorite_type (favorite_content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offline_content_sim (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    content_id_a BIGINT UNSIGNED NOT NULL,
    content_id_b BIGINT UNSIGNED NOT NULL,
    content_type ENUM('music','video') NOT NULL,
    similarity DECIMAL(6,5) NOT NULL,
    compute_time DATETIME(3) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    INDEX idx_a_type_sim (content_id_a, content_type, similarity DESC),
    INDEX idx_b_type (content_id_b, content_type),
    UNIQUE KEY uk_pair (content_id_a, content_id_b, content_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offline_recommendations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    content_id BIGINT UNSIGNED NOT NULL,
    content_type ENUM('music','video') NOT NULL,
    `rank` TINYINT UNSIGNED NOT NULL,
    score DECIMAL(10,6) NOT NULL,
    strategy VARCHAR(32) NOT NULL,
    reason VARCHAR(128) DEFAULT NULL,
    batch_id VARCHAR(64) NOT NULL,
    compute_time DATETIME(3) NOT NULL,
    expire_time DATETIME(3) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    INDEX idx_user_rank (user_id, `rank`),
    INDEX idx_batch (batch_id),
    INDEX idx_expire (expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offline_metrics (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    metric_date DATE NOT NULL,
    user_group ENUM('coldstart','existing','all') NOT NULL,
    content_type ENUM('music','video','mixed','all') NOT NULL,
    ctr DECIMAL(6,4) DEFAULT NULL,
    cvr DECIMAL(6,4) DEFAULT NULL,
    avg_watch_duration DECIMAL(10,2) DEFAULT NULL,
    avg_interactions DECIMAL(6,2) DEFAULT NULL,
    coverage DECIMAL(6,4) DEFAULT NULL,
    diversity DECIMAL(6,4) DEFAULT NULL,
    coldstart_conversion DECIMAL(6,4) DEFAULT NULL,
    total_impressions BIGINT UNSIGNED DEFAULT 0,
    total_clicks BIGINT UNSIGNED DEFAULT 0,
    total_users INT UNSIGNED DEFAULT 0,
    compute_time DATETIME(3) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uk_date_group_type (metric_date, user_group, content_type),
    INDEX idx_metric_date (metric_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
