"""SQLite persistence with parameterized queries and hourly energy units."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS buildings(building_id TEXT PRIMARY KEY,name TEXT NOT NULL,site_id TEXT NOT NULL,is_demo INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS readings(building_id TEXT NOT NULL REFERENCES buildings(building_id),timestamp TEXT NOT NULL,kwh REAL NOT NULL CHECK(kwh>=0),temperature_c REAL,PRIMARY KEY(building_id,timestamp));
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
CREATE TABLE IF NOT EXISTS documents(document_id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chunks(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,document_id INTEGER NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,chunk_index INTEGER NOT NULL,page_number INTEGER,content TEXT NOT NULL);
"""
@contextmanager
def connection(path=None):
    file=Path(path) if path is not None else db_path()
    file.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(file),timeout=15)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally: con.close()

def initialize(path=None):
    with connection(path) as con: con.executescript(SCHEMA)

def list_buildings(path=None):
    with connection(path) as con:
        return [dict(r) for r in con.execute("SELECT building_id,name,site_id,is_demo FROM buildings ORDER BY building_id")]

def readings(building_id,limit=336,path=None):
    with connection(path) as con:
        return [dict(r) for r in con.execute("SELECT timestamp,kwh,temperature_c FROM readings WHERE building_id=? ORDER BY timestamp DESC LIMIT ?",(building_id,limit))][::-1]

def add_document(title,source,page_texts,path=None):
    from .retrieval import split_text
    with connection(path) as con:
        doc_id=con.execute("INSERT INTO documents(title,source) VALUES (?,?)",(title,source)).lastrowid
        index=0
        for page,text in page_texts:
            for chunk in split_text(text):
                con.execute("INSERT INTO chunks(document_id,chunk_index,page_number,content) VALUES(?,?,?,?)",(doc_id,index,page,chunk))
                index+=1
        if not index: raise ValueError("Document contains no searchable text")
    return doc_id

def list_documents(path=None):
    with connection(path) as con:
        return [dict(r) for r in con.execute("SELECT d.document_id,d.title,d.source,COUNT(c.chunk_id) AS chunks FROM documents d LEFT JOIN chunks c ON c.document_id=d.document_id GROUP BY d.document_id ORDER BY d.document_id")]
