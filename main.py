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
