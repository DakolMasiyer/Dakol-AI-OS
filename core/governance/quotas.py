import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

class QuotaExhaustedError(Exception):
    pass

class SupabaseQuotaClient:
    """
    Mock of Supabase append-only audit tables for Quota Governance.
    Uses SQLite locally to simulate the remote database without flat-files.
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).resolve().parents[2] / "logs" / "supabase_mock.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, isolation_level=None)
        self._init_db()

    def _init_db(self):
        # Append-only ledger for quotas
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quota_audit (
                id TEXT PRIMARY KEY,
                app_id TEXT,
                service TEXT,
                cost INTEGER,
                timestamp TEXT
            )
        """)
        # App quotas configuration
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quota_config (
                app_id TEXT,
                service TEXT,
                max_quota INTEGER,
                PRIMARY KEY (app_id, service)
            )
        """)
        # Initialize default quotas
        self.conn.execute("INSERT OR IGNORE INTO quota_config VALUES ('worldcup_ai', 'gemini', 100)")
        self.conn.execute("INSERT OR IGNORE INTO quota_config VALUES ('listening_farm_ai', 'gemini', 500)")

    def consume_quota(self, app_id: str, service: str, cost: int) -> bool:
        cursor = self.conn.cursor()
        
        # Check current usage
        cursor.execute("SELECT SUM(cost) FROM quota_audit WHERE app_id = ? AND service = ?", (app_id, service))
        row = cursor.fetchone()
        current_usage = row[0] if row[0] else 0
        
        # Check limit
        cursor.execute("SELECT max_quota FROM quota_config WHERE app_id = ? AND service = ?", (app_id, service))
        config_row = cursor.fetchone()
        if not config_row:
            raise ValueError(f"No quota configured for {app_id} -> {service}")
            
        max_quota = config_row[0]
        
        if current_usage + cost > max_quota:
            raise QuotaExhaustedError(f"Quota exhausted for {app_id} -> {service}. Max: {max_quota}, Usage: {current_usage}")
            
        # Append-only audit logging
        audit_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT INTO quota_audit VALUES (?, ?, ?, ?, ?)", (audit_id, app_id, service, cost, timestamp))
        return True

    def get_remaining_quota(self, app_id: str, service: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT max_quota FROM quota_config WHERE app_id = ? AND service = ?", (app_id, service))
        config_row = cursor.fetchone()
        if not config_row:
            return 0
            
        max_quota = config_row[0]
        
        cursor.execute("SELECT SUM(cost) FROM quota_audit WHERE app_id = ? AND service = ?", (app_id, service))
        row = cursor.fetchone()
        current_usage = row[0] if row[0] else 0
        
        return max_quota - current_usage
