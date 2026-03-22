-- Migration: Add auth_methods table for multi-provider authentication
-- This migration adds the auth_methods table, migrates existing GitHub users,
-- adds display_name to users, and removes the old github-specific columns.

-- 1. Create auth_methods table
CREATE TABLE auth_methods (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    provider VARCHAR(20) NOT NULL,
    provider_id VARCHAR(320) NOT NULL,
    credential VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_id)
);

-- 2. Migrate existing GitHub users
INSERT INTO auth_methods (user_id, provider, provider_id)
SELECT id, 'github', CAST(github_id AS VARCHAR) FROM users;

-- 3. Add display_name column
ALTER TABLE users ADD COLUMN display_name VARCHAR(100) NOT NULL DEFAULT '';
UPDATE users SET display_name = github_username WHERE github_username IS NOT NULL;

-- 4. Drop old columns
ALTER TABLE users DROP COLUMN github_id;
ALTER TABLE users DROP COLUMN github_username;
