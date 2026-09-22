CREATE TABLE IF NOT EXISTS webhook_receipts (
    event_key TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
