from db import get_db

conn = get_db()
conn.execute("""
CREATE TABLE IF NOT EXISTS qr_codes (
    code TEXT PRIMARY KEY,
    redirect_url TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
)
""")
conn.commit()
conn.close()

print("DB initialized")
