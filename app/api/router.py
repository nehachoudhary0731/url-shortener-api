from fastapi import APIRouter
from app.api.endpoints import auth, urls

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(urls.router)
