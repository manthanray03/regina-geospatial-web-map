"""Database connection for the API."""
import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

from etl import config


def get_conn():
    """FastAPI dependency: opens a connection for one request and closes it after."""
    try:
        conn = psycopg.connect(config.conninfo(), row_factory=dict_row, connect_timeout=5)
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Database is not available")

    try:
        yield conn
    finally:
        conn.close()


def check_connection():
    """Used by /api/health. Returns True if the database answers."""
    try:
        with psycopg.connect(config.conninfo(), connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False
