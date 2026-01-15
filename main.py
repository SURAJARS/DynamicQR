from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
import sqlite3
import qrcode
from io import BytesIO

app = FastAPI()

# =========================
# Database (Render-safe)
# =========================
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

init_db()

# =========================
# Utils
# =========================
def detect_language(request: Request):
    header = request.headers.get("accept-language", "").lower()
    if "ta" in header:
        return "ta"
    return "en"

# =========================
# Health
# =========================
@app.get("/")
def root():
    return {"status": "ok"}

# =========================
# CORE REDIRECT
# =========================
@app.get("/q/{code}")
def redirect_qr(code: str, request: Request):
    lang = detect_language(request)
    conn = get_db()

    row = conn.execute(
        "SELECT redirect_url FROM language_redirects WHERE code=? AND language=?",
        (code, lang)
    ).fetchone()

    if not row:
        row = conn.execute(
            "SELECT redirect_url FROM qr_codes WHERE code=? AND is_active=1",
            (code,)
        ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="QR not found")

    return RedirectResponse(row["redirect_url"], status_code=302)

# =========================
# QR IMAGE GENERATOR
# =========================
@app.get("/qr/{code}/image")
def qr_image(code: str):
    url = f"https://dynamicqr-s3mm.onrender.com/q/{code}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")

# =========================
# AUTO CREATE QR (ADMIN)
# =========================
@app.get("/admin/create-qr")
def create_qr(code: str, en_url: str, ta_url: str = "", token: str = ""):
    if token != "secret123":
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_db()

    conn.execute(
        "INSERT OR REPLACE INTO qr_codes (code, redirect_url) VALUES (?, ?)",
        (code, en_url)
    )

    if ta_url:
        conn.execute(
            "INSERT OR REPLACE INTO language_redirects (code, language, redirect_url) VALUES (?, ?, ?)",
            (code, "ta", ta_url)
        )

    conn.commit()
    conn.close()

    return qr_image(code)

# =========================
# ADMIN UI (CLEAN & SAFE)
# =========================
@app.get("/admin", response_class=HTMLResponse)
def admin_ui():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Dynamic QR</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            padding: 30px;
        }
        .container {
            max-width: 900px;
            margin: auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        .card {
            background: #ffffff;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.08);
        }
        h1, h2 {
            margin-top: 0;
        }
        input, button {
            width: 100%;
            padding: 10px;
            margin-top: 8px;
        }
        button {
            background: #000;
            color: #fff;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }
        ul {
            padding-left: 18px;
        }
        @media(max-width:800px){
            .container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>

<div class="container">

    <div class="card">
        <h1>Dynamic QR Generator</h1>
        <p>Create one QR that adapts automatically.</p>

        <form method="get" action="/admin/create-qr">
            <input type="hidden" name="token" value="secret123">

            <label>QR Code Name</label>
            <input name="code" required>

            <label>English Redirect URL</label>
            <input name="en_url" required>

            <label>Tamil Redirect URL (optional)</label>
            <input name="ta_url">

            <button type="submit">Create & Download QR</button>
        </form>
    </div>

    <div class="card">
        <h2>How it works</h2>
        <ul>
            <li>One QR is generated and printed</li>
            <li>QR always points to backend</li>
            <li>Language is detected automatically</li>
            <li>Tamil phones → Tamil page</li>
            <li>English phones → English page</li>
            <li>Links can change without reprinting QR</li>
        </ul>
        <p><b>The QR is static. The logic is dynamic.</b></p>
    </div>

</div>

</body>
</html>
"""
