import string
import secrets
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import ShortURL, Click
from app.core.config import settings
from app.core.redis_client import redis_client

ALPHABET = string.ascii_letters + string.digits  # 62 chars -> 62^7 = 3.5 trillion combos


def generate_short_code(length: int = None) -> str:
    length = length or settings.SHORT_CODE_LENGTH
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def get_unique_short_code(db: Session) -> str:
    """Generate a short code, retrying on collision (extremely rare but handled)."""
    for _ in range(5):
        code = generate_short_code()
        exists = db.query(ShortURL).filter(ShortURL.short_code == code).first()
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="Could not generate unique short code. Try again.")


# ─── Cache helpers ────────────────────────────────────────────────────────────

CACHE_TTL = 3600  # 1 hour


def cache_url(short_code: str, original_url: str):
    redis_client.setex(f"url:{short_code}", CACHE_TTL, original_url)


def get_cached_url(short_code: str) -> Optional[str]:
    return redis_client.get(f"url:{short_code}")


def invalidate_cache(short_code: str):
    redis_client.delete(f"url:{short_code}")


# ─── CRUD operations ──────────────────────────────────────────────────────────

def create_short_url(db: Session, original_url: str, user_id: Optional[int],
                     custom_alias: Optional[str], expires_at: Optional[datetime]) -> ShortURL:
    # Check custom alias availability
    if custom_alias:
        existing = db.query(ShortURL).filter(ShortURL.custom_alias == custom_alias).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Alias '{custom_alias}' is already taken")

    short_code = custom_alias if custom_alias else get_unique_short_code(db)

    url = ShortURL(
        original_url=original_url,
        short_code=short_code,
        custom_alias=custom_alias,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(url)
    db.commit()
    db.refresh(url)
    cache_url(short_code, original_url)
    return url


def resolve_short_code(db: Session, short_code: str) -> str:
    """
    Resolve a short code to its original URL.
    Cache-hit: returns from Redis instantly.
    Cache-miss: queries DB, re-populates cache.
    """
    # Cache hit
    cached = get_cached_url(short_code)
    if cached:
        return cached

    # Cache miss — query DB
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    if not url.is_active:
        raise HTTPException(status_code=410, detail="This short URL has been deactivated")
    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This short URL has expired")

    cache_url(short_code, url.original_url)
    return url.original_url


def record_click(db: Session, short_code: str, ip: str, user_agent_str: str, referer: str):
    """Parse user-agent and store click analytics asynchronously."""
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url:
        return

    device_type = "unknown"
    browser = "unknown"
    os_name = "unknown"

    try:
        from user_agents import parse as ua_parse
        ua = ua_parse(user_agent_str or "")
        device_type = "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop")
        browser = ua.browser.family
        os_name = ua.os.family
    except Exception:
        pass

    click = Click(
        url_id=url.id,
        ip_address=ip,
        user_agent=user_agent_str,
        referer=referer,
        device_type=device_type,
        browser=browser,
        os=os_name,
    )
    db.add(click)
    db.commit()


def get_analytics(db: Session, short_code: str, user_id: int) -> dict:
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    if url.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't own this URL")

    clicks = db.query(Click).filter(Click.url_id == url.id).all()

    def count_by(field):
        counts = {}
        for c in clicks:
            val = getattr(c, field) or "unknown"
            counts[val] = counts.get(val, 0) + 1
        return counts

    unique_ips = len({c.ip_address for c in clicks if c.ip_address})
    recent = sorted(clicks, key=lambda c: c.clicked_at, reverse=True)[:10]

    return {
        "short_code": short_code,
        "original_url": url.original_url,
        "total_clicks": len(clicks),
        "unique_ips": unique_ips,
        "clicks_by_device": count_by("device_type"),
        "clicks_by_browser": count_by("browser"),
        "clicks_by_os": count_by("os"),
        "recent_clicks": recent,
    }
