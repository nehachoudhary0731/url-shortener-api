from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.db.connection import engine, Base
from app.services.url_service import (
    resolve_short_code,
    record_click
)
from sqlalchemy.orm import Session
from app.db.connection import get_db



Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener API",
    description="""
A production-ready URL shortener with:
- **JWT authentication** — register/login to manage your links
- **Custom aliases** — `yourdomain.com/my-brand` instead of random codes
- **Click analytics** — device type, browser, OS, referrer per click
- **Redis caching** — redirects served from cache (cache-hit: ~1ms)
- **Rate limiting** — per-IP sliding window via Redis
- **Link expiry** — set an expiration datetime per URL
- **Collision handling** — guaranteed unique short codes
    """,
    version="1.0.0",
)

@app.get("/")
def root():
    return {"message": "URL Shortener API is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/{short_code}", include_in_schema=False)
def redirect(short_code: str, request: Request, db: Session = Depends(get_db)):
    original_url = resolve_short_code(db, short_code)

    try:
        record_click(
            db=db,
            short_code=short_code,
            ip=request.client.host,
            user_agent_str=request.headers.get("user-agent", ""),
            referer=request.headers.get("referer", ""),
        )
    except Exception:
        pass

    return RedirectResponse(url=original_url, status_code=302)
