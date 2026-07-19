import sqlite3, logging

logger = logging.getLogger(__name__)


def makeTables(cursor: sqlite3.Cursor):
    logger.info("Creating the SQLite Database tables")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId INTEGER UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            totalNumberOfMessages INTEGER,
            lastMessageId INTEGER NOT NULL DEFAULT 0,
            messageCounter INTEGER NOT NULL DEFAULT 0,
            archivingTime FLOAT NOT NULL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId INTEGER,
            messageId INTEGER ,
            authorName TEXT,
            views INTEGER,
            senderId INTEGER,
            forwardFromUsername INTEGER,
            forwardFromUserId INTEGER,
            repliedToId INTEGER,
            text TEXT,
            date DATETIME,
            editDate DATETIME,
            filePath TEXT,
            fileId TEXT,
            fileSize FLOAT NOT NULL DEFAULT 0.0,
            downloadedMedia BOOL NOT NULL DEFAULT FALSE,
            UNIQUE (dialogId, messageId)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId INTEGER,
            messageId INTEGER,
            reactorsId INTEGER,
            dateOfReacting DATETIME,
            reaction TEXT,
            count INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            dialogId INTEGER,
            UNIQUE (userId, dialogId)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogInfo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId TEXT UNIQUE,
            fullRequest TEXT,
            dateOfRequest DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogInfoArchive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId INTEGER,
            fullRequest TEXT UNIQUE,
            dateOfRequest DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogPhotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dialogId INTEGER,
            photoId INTEGER UNIQUE,
            photoPath TEXT,
            photoDate DATETIME
        )
    """)
