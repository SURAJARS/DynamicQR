from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
import sqlite3
import os

app = FastAPI()

DB_PATH = "/tmp/qr.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS qr_codes (
        code TEXT PRIMARY KEY,
        redirect_url TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/admin/add-test")
def add_test():
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO qr_codes (code, redirect_url) VALUES (?, ?)",
        ("demo", "https://www.google.com")
    )
    conn.commit()
    conn.close()
    return {"status": "added"}

@app.get("/q/{code}")
def redirect_qr(code: str):
    conn = get_db()
    row = conn.execute(
        "SELECT redirect_url FROM qr_codes WHERE code=? AND is_active=1",
        (code,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="QR not found")

    return RedirectResponse(url=row["redirect_url"], status_code=302)
