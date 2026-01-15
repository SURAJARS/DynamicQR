import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse

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
@app.get("/admin/create-qr")
def create_qr(
    code: str,
    en_url: str,
    ta_url: str = "",
    token: str = ""
):
    # simple protection
    if token != "secret123":
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_db()

    # Insert default (English)
    conn.execute(
        "INSERT OR REPLACE INTO qr_codes (code, redirect_url) VALUES (?, ?)",
        (code, en_url)
    )

    # Insert Tamil override if provided
    if ta_url:
        conn.execute(
            "INSERT OR REPLACE INTO language_redirects (code, language, redirect_url) VALUES (?, ?, ?)",
            (code, "ta", ta_url)
        )

    conn.commit()
    conn.close()

    # Generate QR image (same logic as before)
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



@app.get("/admin", response_class=HTMLResponse)
def admin_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dynamic QR – Admin</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                background: linear-gradient(135deg, #f5f7fa, #e4e8ee);
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
                background: #fff;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            }
            h1 {
                margin-top: 0;
                font-size: 26px;
            }
            h2 {
                margin-top: 0;
                font-size: 20px;
            }
            p {
                color: #555;
                line-height: 1.5;
            }
            label {
                font-size: 14px;
                margin-top: 12px;
                display: block;
            }
            input {
                width: 100%;
                padding: 10px;
                margin-top: 6px;
                border-radius: 6px;
                border: 1px solid #ccc;
                font-size: 14px;
            }
            button {
                margin-top: 20px;
                width: 100%;
                padding: 12px;
                font-size: 15px;
                background: #111;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }
            button:hover {
                background: #000;
            }
            .tag {
                display: inline-block;
                background: #eef2ff;
                color: #333;
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 12px;
                margin-bottom: 10px;
            }
            ul {
                padding-left: 18px;
            }
            li {
                margin-bottom: 8px;
            }
            .footer-note {
                font-size: 12px;
                color: #777;
                margin-top: 15px;
            }
            @media (max-width: 800px) {
                .container {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>

        <div class="container">

            <!-- LEFT: CREATE QR -->
            <div class="card">
                <span class="tag">Admin Panel</span>
                <h1>Dynamic QR Generator</h1>
                <p>
                    Create a single QR code that redirects users
                    based on their language — without reprinting.
                </p>

                <form method="get" action="/admin/create-qr">
                    <input type="hidden" name="token" value="secret123">

                    <label>QR Code Name</label>
                    <input name="code" placeholder="e.g. shop-front" required>

                    <label>English Redirect URL</label>
                    <input name="en_url" placeholder="https://example.com/en" required>

                    <label>Tamil Redirect URL (optional)</label>
                    <input name="ta_url" placeholder="https://example.com/ta">

                    <button type="submit">Create & Download QR</button>
                </form>

                <div class="footer-note">
                    After clicking, the QR image will open in a new page.
                </div>
            </div>

            <!-- RIGHT: HOW IT WORKS -->
            <div class="card">
                <span class="tag">How it works</span>
                <h2>One QR. Multiple Destinations.</h2>

                <p>
                    This system separates the <b>QR image</b> from the
                    <b>decision logic</b>.
                </p>

                <ul>
                    <li>
                        You generate <b>one QR code</b> and print it anywhere.
                    </li>
                    <li>
                        The QR always points to our backend URL.
                    </li>
                    <li>
                        When someone scans it:
                        <ul>
                            <li>📱 Tamil phone → Tamil page</li>
                            <li>🌍 English phone → English page</li>
                        </ul>
                    </li>
                    <li>
                        You can change links anytime without changing the QR.
                    </li>
                </ul>

                <p>
                    No mobile app.  
                    No frontend dependency.  
                    Just reliable backend logic.
                </p>

                <p class="footer-note">
                    Ideal for shops, events, menus, posters, and campaigns.
                </p>
            </div>

        </div>

    </body>
    </html>
    """

    </html>
    """


