from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.connection import get_db
from app.db.models import ShortURL, User
from app.db.schemas import URLCreate, URLOut, URLUpdate, AnalyticsOut
from app.core.security import get_current_user, get_optional_user
from app.core.rate_limiter import rate_limit
from app.core.config import settings
from app.services.url_service import (
    create_short_url,
    get_analytics, invalidate_cache
)

router = APIRouter(tags=["URLs"])


def enrich(url: ShortURL) -> dict:
    """Add computed short_url and total_clicks fields."""
    data = {
        "id": url.id,
        "original_url": url.original_url,
        "short_code": url.short_code,
        "short_url": f"{settings.BASE_URL}/{url.short_code}",
        "custom_alias": url.custom_alias,
        "is_active": url.is_active,
        "expires_at": url.expires_at,
        "total_clicks": len(url.clicks) if url.clicks else 0,
        "created_at": url.created_at,
    }
    return data


#Shorten a URL
@router.post("/shorten", response_model=URLOut, status_code=201)
def shorten_url(
    payload: URLCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    _: None = Depends(rate_limit),
):
    url = create_short_url(
        db=db,
        original_url=payload.original_url,
        user_id=current_user.id if current_user else None,
        custom_alias=payload.custom_alias,
        expires_at=payload.expires_at,
    )
    return enrich(url)


#User's URL list
@router.get("/urls", response_model=List[URLOut])
def list_my_urls(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    urls = db.query(ShortURL).filter(ShortURL.user_id == current_user.id)\
        .order_by(ShortURL.created_at.desc()).offset(skip).limit(limit).all()
    return [enrich(u) for u in urls]


#Update a URL
@router.patch("/urls/{short_code}", response_model=URLOut)
def update_url(
    short_code: str,
    payload: URLUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    if url.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't own this URL")

    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(url, key, val)

    db.commit()
    db.refresh(url)
    invalidate_cache(short_code) 
    return enrich(url)


# Delete a URL
@router.delete("/urls/{short_code}", status_code=204)
def delete_url(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    url = db.query(ShortURL).filter(ShortURL.short_code == short_code).first()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    if url.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't own this URL")

    db.delete(url)
    db.commit()
    invalidate_cache(short_code)


#Analytics
@router.get("/urls/{short_code}/analytics", response_model=AnalyticsOut)
def analytics(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_analytics(db, short_code, current_user.id)

#Health
@router.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
