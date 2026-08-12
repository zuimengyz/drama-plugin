-- Drama Plugin long-term memory schema
-- Target: MySQL 8.0+, InnoDB, utf8mb4. Relationships are logical only; no physical referential constraints.

CREATE TABLE drama_work (
    id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    content JSON NOT NULL,
    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    KEY idx_drama_work_title (title)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drama_script (
    id VARCHAR(64) NOT NULL,
    work_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content JSON NOT NULL,
    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    KEY idx_drama_script_work_id (work_id),
    KEY idx_drama_script_work_title (work_id, title)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drama_episode (
    id VARCHAR(64) NOT NULL,
    script_id VARCHAR(64) NOT NULL,
    episode_no INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    content JSON NOT NULL,
    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    UNIQUE KEY uk_drama_episode_script_no (script_id, episode_no),
    KEY idx_drama_episode_script_title (script_id, title)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drama_scene (
    id VARCHAR(64) NOT NULL,
    episode_id VARCHAR(64) NOT NULL,
    scene_order INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    location VARCHAR(255) NULL,
    content JSON NOT NULL,
    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    UNIQUE KEY uk_drama_scene_episode_order (
        episode_id,
        scene_order
    ),
    KEY idx_drama_scene_episode_location (
        episode_id,
        location
    ),
    KEY idx_drama_scene_title (title)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drama_shot (
    id VARCHAR(64) NOT NULL,
    scene_id VARCHAR(64) NOT NULL,
    shot_no VARCHAR(64) NOT NULL,
    title VARCHAR(255) NULL,
    shot_type VARCHAR(64) NULL,
    content JSON NOT NULL,
    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    UNIQUE KEY uk_drama_shot_scene_no (
        scene_id,
        shot_no
    ),
    KEY idx_drama_shot_scene_type (
        scene_id,
        shot_type
    ),
    KEY idx_drama_shot_title (title)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drama_asset (
    id VARCHAR(64) NOT NULL,

    work_id VARCHAR(64) NOT NULL,
    episode_id VARCHAR(64) NULL,
    scene_id VARCHAR(64) NULL,
    shot_id VARCHAR(64) NULL,

    asset_type VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,

    reference_media_ids JSON NOT NULL,
    content JSON NOT NULL,

    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    KEY idx_drama_asset_work_type (
        work_id,
        asset_type
    ),
    KEY idx_drama_asset_episode (episode_id),
    KEY idx_drama_asset_scene (scene_id),
    KEY idx_drama_asset_shot (shot_id),
    KEY idx_drama_asset_name (name)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE drama_media (
    id VARCHAR(64) NOT NULL,

    work_id VARCHAR(64) NOT NULL,
    asset_id VARCHAR(64) NULL,
    shot_id VARCHAR(64) NULL,

    media_type VARCHAR(32) NOT NULL,
    purpose VARCHAR(64) NULL,
    source_ref VARCHAR(255) NOT NULL,

    storage_type VARCHAR(32) NULL,
    bucket_name VARCHAR(255) NULL,
    object_key VARCHAR(1024) NULL,

    mime_type VARCHAR(128) NULL,
    file_size BIGINT UNSIGNED NULL,
    width INT UNSIGNED NULL,
    height INT UNSIGNED NULL,
    duration_ms BIGINT UNSIGNED NULL,
    content_hash VARCHAR(128) NULL,

    content JSON NOT NULL,

    version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    UNIQUE KEY uk_drama_media_source_ref (source_ref),
    KEY idx_drama_media_work (work_id),
    KEY idx_drama_media_asset (asset_id),
    KEY idx_drama_media_shot (shot_id),
    KEY idx_drama_media_type_purpose (
        media_type,
        purpose
    )
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
