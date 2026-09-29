CREATE TABLE IF NOT EXISTS task_runs (
    id SERIAL PRIMARY KEY,
    run_name VARCHAR(255) NOT NULL,
    game_name VARCHAR(255) NOT NULL,
    start_index INTEGER NOT NULL,
    end_index INTEGER NOT NULL,
    total_success INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'RUNNING',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES task_runs(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    game_name VARCHAR(255) NOT NULL,
    proxy_address VARCHAR(255),
    status VARCHAR(50) DEFAULT 'PENDING',
    error_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_acc_game_seq ON accounts (game_name, sequence_number);
