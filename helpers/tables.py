import sqlite3
import logging

logger = logging.getLogger(__name__)


def make_tables(cursor: sqlite3.Cursor) -> None:
    """
        A function that initilizes the tables for the database.

        Args:
            cursor (sqlite3.Cursor):
                The cursor of the database.
    """

    logger.info("Creating the SQLite Database tables...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            total_number_of_messages INTEGER,
            last_message_id INTEGER NOT NULL DEFAULT 1,
            message_counter INTEGER NOT NULL DEFAULT 0,
            archiving_time FLOAT NOT NULL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER,
            message_id INTEGER ,
            author_name TEXT,
            views INTEGER,
            sender_id INTEGER,
            forward_from_username INTEGER,
            forward_from_user_id INTEGER,
            replied_to_id TEXT,
            text TEXT,
            date DATETIME,
            edit_date DATETIME,
            file_path TEXT,
            file_id TEXT,
            file_size FLOAT NOT NULL DEFAULT 0.0,
            downloaded_file BOOL NOT NULL DEFAULT FALSE,
            UNIQUE (dialog_id, message_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER,
            message_id INTEGER,
            reactors_id INTEGER,
            reacting_date DATETIME,
            reaction TEXT,
            count INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            dialog_id INTEGER,
            UNIQUE (user_id, dialog_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialog_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id TEXT UNIQUE,
            full_request TEXT,
            date_of_request DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialog_metadata_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER,
            full_request TEXT UNIQUE,
            date_of_request DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialog_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialog_id INTEGER,
            photo_id INTEGER UNIQUE,
            photo_path TEXT,
            photo_date DATETIME
        )
    """)
