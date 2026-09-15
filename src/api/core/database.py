# src/api/core/database.py

# This governs the SQLite database used to track ingestion batches and their statuses.

import sqlite3
from datetime import datetime

DB_NAME = "jobs.db"

def init_db():
    """Create the table if it doesn't exist"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                batch_id TEXT PRIMARY KEY,
                status TEXT,
                created_at TIMESTAMP,
                output_file_id TEXT
            )
        """)
        # We also need to map individual files to the batch to update Qdrant later
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                qdrant_point_id TEXT,
                custom_id TEXT
            )
        """)

def save_batch(batch_id, image_data_list):
    """Log a new batch and the images inside it"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO batches (batch_id, status, created_at) VALUES (?, ?, ?)",
            (batch_id, "pending", datetime.now())
        )
        for img in image_data_list:
            conn.execute(
                "INSERT INTO pending_images (batch_id, qdrant_point_id, custom_id) VALUES (?, ?, ?)",
                (batch_id, img['qdrant_id'], img['custom_id'])
            )