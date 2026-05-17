from pydantic import BaseModel, HttpUrl, field_validator, EmailStr
from typing import Optional
from datetime import datetime



# For Users
class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"



# For URLs
class URLCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 chars)")
        return v

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, v):
        if v is None:
            return v
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Alias can only contain letters, numbers, hyphens, and underscores")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Alias must be between 3 and 50 characters")
        return v


class URLOut(BaseModel):
    id: int
    original_url: str
    short_code: str
    short_url: str
    custom_alias: Optional[str] = None
    is_active: bool
    expires_at: Optional[datetime] = None
    total_clicks: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class URLUpdate(BaseModel):
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ClickOut(BaseModel):
    id: int
    ip_address: Optional[str] = None
    referer: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    country: Optional[str] = None
    clicked_at: datetime

    class Config:
        from_attributes = True


class AnalyticsOut(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    unique_ips: int
    clicks_by_device: dict
    clicks_by_browser: dict
    clicks_by_os: dict
    recent_clicks: list[ClickOut]
