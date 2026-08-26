from pathlib import Path
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LOCAL_UPLOAD_DIR = BASE_DIR / "uploads"

# Render Persistent Disk: set DATA_DIR=/var/data
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "class_news.db"

ADMIN_KEY = os.getenv("ADMIN_KEY", "100525")
KST = timezone(timedelta(hours=9))

app = FastAPI(title="우리반 뉴스")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IMPORTANT: paths are based on main.py, so Render Root Directory can be blank.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            likes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def now_text() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def check_admin(key: str):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


def safe_name(name: str) -> str:
    base = Path(name).name
    stamp = datetime.now(KST).strftime("%Y%m%d%H%M%S%f")
    return f"{stamp}_{base.replace(' ', '_')}"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/api/news")
def list_news():
    conn = db()
    rows = conn.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/news/{news_id}")
def get_news(news_id: int):
    conn = db()
    row = conn.execute("SELECT * FROM news WHERE id=?", (news_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다.")
    return dict(row)


@app.post("/api/admin/login")
def admin_login(key: str = Form(...)):
    check_admin(key)
    return {"ok": True}


@app.post("/api/news")
async def create_news(
    key: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
):
    check_admin(key)
    title = title.strip()
    content = content.strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="제목과 내용을 입력해주세요.")

    image_url = None
    if image and image.filename:
        allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        ext = Path(image.filename).suffix.lower()
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="JPG, PNG, GIF, WEBP 이미지만 업로드할 수 있습니다.")
        filename = safe_name(image.filename)
        target = UPLOAD_DIR / filename
        data = await image.read()
        if len(data) > 8 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="이미지는 8MB 이하만 업로드할 수 있습니다.")
        target.write_bytes(data)
        image_url = f"/uploads/{filename}"

    timestamp = now_text()
    conn = db()
    cur = conn.execute(
        "INSERT INTO news (title, content, image_url, likes, created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)",
        (title, content, image_url, timestamp, timestamp),
    )
    conn.commit()
    news_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": news_id}


@app.put("/api/news/{news_id}")
async def update_news(
    news_id: int,
    key: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    remove_image: bool = Form(False),
):
    check_admin(key)
    title = title.strip()
    content = content.strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="제목과 내용을 입력해주세요.")

    conn = db()
    old = conn.execute("SELECT image_url FROM news WHERE id=?", (news_id,)).fetchone()
    if not old:
        conn.close()
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다.")

    image_url = old["image_url"]
    if remove_image:
        image_url = None
    if image and image.filename:
        allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        ext = Path(image.filename).suffix.lower()
        if ext not in allowed:
            conn.close()
            raise HTTPException(status_code=400, detail="JPG, PNG, GIF, WEBP 이미지만 업로드할 수 있습니다.")
        data = await image.read()
        if len(data) > 8 * 1024 * 1024:
            conn.close()
            raise HTTPException(status_code=400, detail="이미지는 8MB 이하만 업로드할 수 있습니다.")
        filename = safe_name(image.filename)
        (UPLOAD_DIR / filename).write_bytes(data)
        image_url = f"/uploads/{filename}"

    conn.execute(
        "UPDATE news SET title=?, content=?, image_url=?, updated_at=? WHERE id=?",
        (title, content, image_url, now_text(), news_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/news/{news_id}")
def delete_news(news_id: int, key: str):
    check_admin(key)
    conn = db()
    row = conn.execute("SELECT image_url FROM news WHERE id=?", (news_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다.")
    conn.execute("DELETE FROM news WHERE id=?", (news_id,))
    conn.commit()
    conn.close()
    if row["image_url"]:
        file_path = UPLOAD_DIR / Path(row["image_url"]).name
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
    return {"ok": True}


@app.post("/api/news/{news_id}/like")
def like_news(news_id: int):
    conn = db()
    cur = conn.execute("UPDATE news SET likes = likes + 1 WHERE id=?", (news_id,))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다.")
    row = conn.execute("SELECT likes FROM news WHERE id=?", (news_id,)).fetchone()
    conn.close()
    return {"ok": True, "likes": row["likes"]}
