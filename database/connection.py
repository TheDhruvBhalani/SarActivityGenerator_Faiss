"""
Database connection utilities
"""
import sqlite3
from config.settings import Config


def get_connection(db_path: str = None):
    """Get connection to main database"""
    path = db_path or Config.DB_PATH
    return sqlite3.connect(path)


def get_track_c_connection(db_path: str = None):
    """Get connection to Track C (continual learning) database"""
    path = db_path or Config.TRACK_C_DB_PATH
    return sqlite3.connect(path)
