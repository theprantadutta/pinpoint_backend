-- Delete all data from PinPoint database (PRESERVES STRUCTURE)
-- WARNING: This will delete ALL user data, notes, subscriptions, etc.
-- Database schema (tables, columns, constraints) will remain intact

-- Disable triggers temporarily for faster deletion
SET session_replication_role = 'replica';

-- Delete data from all tables (in correct order to respect foreign keys)
-- Using TRUNCATE CASCADE for efficiency

TRUNCATE TABLE admin_audit_logs CASCADE;
TRUNCATE TABLE fcm_tokens CASCADE;
TRUNCATE TABLE subscription_events CASCADE;
TRUNCATE TABLE sync_events CASCADE;
TRUNCATE TABLE encrypted_notes CASCADE;
TRUNCATE TABLE encryption_keys CASCADE;
TRUNCATE TABLE devices CASCADE;
TRUNCATE TABLE users CASCADE;

-- NOTE: We do NOT delete from alembic_version (migration tracking)

-- Re-enable triggers
SET session_replication_role = 'origin';

-- Verify deletion
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'encrypted_notes', COUNT(*) FROM encrypted_notes
UNION ALL
SELECT 'encryption_keys', COUNT(*) FROM encryption_keys
UNION ALL
SELECT 'devices', COUNT(*) FROM devices
UNION ALL
SELECT 'sync_events', COUNT(*) FROM sync_events
UNION ALL
SELECT 'subscription_events', COUNT(*) FROM subscription_events
UNION ALL
SELECT 'fcm_tokens', COUNT(*) FROM fcm_tokens
UNION ALL
SELECT 'admin_audit_logs', COUNT(*) FROM admin_audit_logs;

-- All counts should be 0
