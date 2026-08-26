import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

ADMIN_KEY = os.getenv("ADMIN_KEY", "100525")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "class_news.db"))
UPLOAD_ROOT = Path(DATABASE_PATH).parent if Path(DATABASE_PATH).is_absolute() else BASE_DIR
UPLOAD_DIR = UPLOAD_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="우리반 뉴스")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image TEXT,
            likes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS likes (
            news_id INTEGER NOT NULL,
            visitor_id TEXT NOT NULL,
            PRIMARY KEY (news_id, visitor_id),
            FOREIGN KEY(news_id) REFERENCES news(id) ON DELETE CASCADE
        );
        """
    )
    conn.close()


init_db()


def admin_ok(request: Request) -> bool:
    return request.cookies.get("admin_session") == request.app.state.admin_session


@app.on_event("startup")
def startup():
    app.state.admin_session = secrets.token_urlsafe(32)


def ensure_visitor(request: Request, response):
    visitor_id = request.cookies.get("visitor_id")
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        response.set_cookie("visitor_id", visitor_id, max_age=60 * 60 * 24 * 365, samesite="lax")
    return visitor_id


def news_dict(row, visitor_id=None):
    liked = False
    if visitor_id:
        conn = db()
        liked = conn.execute(
            "SELECT 1 FROM likes WHERE news_id=? AND visitor_id=?",
            (row["id"], visitor_id),
        ).fetchone() is not None
        conn.close()
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "image": row["image"],
        "likes": row["likes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "liked": liked,
    }


@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/api/news")
def get_news(request: Request):
    visitor_id = request.cookies.get("visitor_id")
    conn = db()
    rows = conn.execute("SELECT * FROM news ORDER BY created_at DESC, id DESC").fetchall()
    conn.close()
    return [news_dict(row, visitor_id) for row in rows]


@app.get("/api/news/{news_id}")
def get_one_news(news_id: int, request: Request):
    visitor_id = request.cookies.get("visitor_id")
    conn = db()
    row = conn.execute("SELECT * FROM news WHERE id=?", (news_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "뉴스를 찾을 수 없습니다.")
    return news_dict(row, visitor_id)


@app.post("/api/admin/login")
def admin_login(payload: dict):
    if str(payload.get("key", "")) != ADMIN_KEY:
        raise HTTPException(401, "관리자 키가 올바르지 않습니다.")
    response = JSONResponse({"ok": True})
    response.set_cookie("admin_session", app.state.admin_session, httponly=True, samesite="lax", max_age=60 * 60 * 12)
    return response


@app.post("/api/admin/logout")
def admin_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("admin_session")
    return response


@app.get("/api/admin/me")
def admin_me(request: Request):
    return {"admin": admin_ok(request)}


@app.post("/api/admin/news")
async def create_news(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile | None = File(None),
):
    if not admin_ok(request):
        raise HTTPException(401, "관리자 인증이 필요합니다.")
    title = title.strip()
    content = content.strip()
    if not title or not content:
        raise HTTPException(400, "제목과 내용을 입력해주세요.")

    image_url = None
    if image and image.filename:
        ext = Path(image.filename).suffix.lower()
        allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        if ext not in allowed:
            raise HTTPException(400, "JPG, PNG, GIF, WEBP 이미지만 업로드할 수 있습니다.")
        data = await image.read()
        if len(data) > 8 * 1024 * 1024:
            raise HTTPException(400, "이미지는 8MB 이하로 업로드해주세요.")
        filename = f"{uuid.uuid4().hex}{ext}"
        (UPLOAD_DIR / filename).write_bytes(data)
        image_url = f"/uploads/{filename}"

    now = datetime.now(timezone.utc).isoformat()
    conn = db()
    cur = conn.execute(
        "INSERT INTO news(title, content, image, created_at, updated_at) VALUES(?,?,?,?,?)",
        (title, content, image_url, now, now),
    )
    conn.commit()
    news_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": news_id}


@app.put("/api/admin/news/{news_id}")
async def update_news(
    news_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    remove_image: bool = Form(False),
    image: UploadFile | None = File(None),
):
    if not admin_ok(request):
        raise HTTPException(401, "관리자 인증이 필요합니다.")
    conn = db()
    row = conn.execute("SELECT * FROM news WHERE id=?", (news_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "뉴스를 찾을 수 없습니다.")

    image_url = row["image"]
    if remove_image:
        image_url = None
    if image and image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            conn.close()
            raise HTTPException(400, "JPG, PNG, GIF, WEBP 이미지만 업로드할 수 있습니다.")
        data = await image.read()
        if len(data) > 8 * 1024 * 1024:
            conn.close()
            raise HTTPException(400, "이미지는 8MB 이하로 업로드해주세요.")
        filename = f"{uuid.uuid4().hex}{ext}"
        (UPLOAD_DIR / filename).write_bytes(data)
        image_url = f"/uploads/{filename}"

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE news SET title=?, content=?, image=?, updated_at=? WHERE id=?",
        (title.strip(), content.strip(), image_url, now, news_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/admin/news/{news_id}")
def delete_news(news_id: int, request: Request):
    if not admin_ok(request):
        raise HTTPException(401, "관리자 인증이 필요합니다.")
    conn = db()
    row = conn.execute("SELECT image FROM news WHERE id=?", (news_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "뉴스를 찾을 수 없습니다.")
    conn.execute("DELETE FROM likes WHERE news_id=?", (news_id,))
    conn.execute("DELETE FROM news WHERE id=?", (news_id,))
    conn.commit()
    conn.close()
    if row["image"] and row["image"].startswith("/uploads/"):
        p = UPLOAD_DIR / row["image"].split("/uploads/", 1)[1]
        if p.exists():
            p.unlink()
    return {"ok": True}


@app.post("/api/news/{news_id}/like")
def like_news(news_id: int, request: Request):
    conn = db()
    row = conn.execute("SELECT id, likes FROM news WHERE id=?", (news_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "뉴스를 찾을 수 없습니다.")

    visitor_id = request.cookies.get("visitor_id")
    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    already = conn.execute(
        "SELECT 1 FROM likes WHERE news_id=? AND visitor_id=?",
        (news_id, visitor_id),
    ).fetchone()
    response = JSONResponse({"ok": True, "liked": bool(already), "likes": row["likes"]})

    if not already:
        conn.execute("INSERT INTO likes(news_id, visitor_id) VALUES(?,?)", (news_id, visitor_id))
        conn.execute("UPDATE news SET likes=likes+1 WHERE id=?", (news_id,))
        conn.commit()
        new_count = row["likes"] + 1
        response = JSONResponse({"ok": True, "liked": True, "likes": new_count})

    conn.close()
    response.set_cookie("visitor_id", visitor_id, max_age=60 * 60 * 24 * 365, samesite="lax")
    return response
