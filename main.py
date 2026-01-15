from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI()

# test endpoint
@app.get("/")
def root():
    return {"status": "ok"}

# QR redirect endpoint
@app.get("/q/{code}")
def redirect_qr(code: str):
    # TEMP: hardcoded redirect (we will use DB later)
    return RedirectResponse(
        url="https://www.google.com",
        status_code=302
    )
