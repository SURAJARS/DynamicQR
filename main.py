from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from db import get_db

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

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

@app.post("/admin/add-test")
def add_test():
    from db import get_db

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO qr_codes (code, redirect_url) VALUES (?, ?)",
        ("demo", "https://www.google.com")
    )
    conn.commit()
    conn.close()

    return {"status": "added"}


