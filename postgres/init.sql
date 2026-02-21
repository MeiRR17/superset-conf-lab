-- יצירת מסד הנתונים עבור Superset
CREATE DATABASE superset_db;

-- יצירת מסד הנתונים עבור הטלפוניה
CREATE DATABASE telephony_db;

-- התחברות למסד הנתונים של הטלפוניה
\c telephony_db;

-- יצירת טבלת המדדים (הורדנו מגבלות NOT NULL ו-CHECK כדי להתאים ל-Mock)
CREATE TABLE IF NOT EXISTS telephony_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    server_type VARCHAR(20) NOT NULL,
    server_name VARCHAR(100),
    metric_category VARCHAR(50),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    raw_data TEXT
);

CREATE INDEX idx_telephony_metrics_timestamp ON telephony_metrics (timestamp DESC);
CREATE INDEX idx_telephony_metrics_server_time ON telephony_metrics (server_type, timestamp DESC);