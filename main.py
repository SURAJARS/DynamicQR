import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
import sqlite3

app = FastAPI()

# =========================
# Database config (Render-safe)
# =========================
DB_PATH = "/tmp/qr.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)

    # Main QR table (default redirect)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS qr_codes (
        code TEXT PRIMARY KEY,
        redirect_url TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    # Language-specific redirects
    conn.execute("""
    CREATE TABLE IF NOT EXISTS language_redirects (
        code TEXT,
        language TEXT,
        redirect_url TEXT,
        PRIMARY KEY (code, language)
    )
    """)

    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# =========================
# Utility: detect language
# =========================
def get_language(request: Request):
    lang_header = request.headers.get("accept-language", "").lower()
    if "ta" in lang_header:
        return "ta"
    return "en"

# =========================
# Health check
# =========================
@app.get("/")
def root():
    return {"status": "ok"}

# =========================
# TEMP ADMIN: add test QR
# =========================
@app.get("/admin/add-test")
def add_test(token: str = ""):
    if token != "secret123":
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO qr_codes (code, redirect_url) VALUES (?, ?)",
        ("demo", "https://www.google.com")
    )
    conn.commit()
    conn.close()

    return {"status": "added"}

# =========================
# TEMP ADMIN: add language test
# =========================
@app.get("/admin/add-lang-test")
def add_lang_test(token: str = ""):
    if token != "secret123":
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_db()

    # Default English redirect
    conn.execute(
        "INSERT OR REPLACE INTO qr_codes (code, redirect_url) VALUES (?, ?)",
        ("langdemo", "https://example.com/en")
    )

    # Tamil redirect override
    conn.execute(
        "INSERT OR REPLACE INTO language_redirects (code, language, redirect_url) VALUES (?, ?, ?)",
        ("langdemo", "ta", "https://example.com/ta")
    )

    conn.commit()
    conn.close()

    return {"status": "language rules added"}

# =========================
# CORE: QR redirect endpoint
# =========================
@app.get("/q/{code}")
def redirect_qr(code: str, request: Request):
    lang = get_language(request)
    conn = get_db()

    # 1️⃣ Try language-specific redirect
    row = conn.execute(
        "SELECT redirect_url FROM language_redirects WHERE code=? AND language=?",
        (code, lang)
    ).fetchone()

    # 2️⃣ Fallback to default redirect
    if not row:
        row = conn.execute(
            "SELECT redirect_url FROM qr_codes WHERE code=? AND is_active=1",
            (code,)
        ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="QR not found")

    return RedirectResponse(url=row["redirect_url"], status_code=302)

@app.get("/qr/{code}/image")
def generate_qr(code: str):
    qr_url = f"https://dynamicqr-s3mm.onrender.com/q/{code}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename={code}.png"
        }
    )
