"""API router: aggregate all route modules."""

from fastapi import APIRouter

from app.api import analytics, auth, chat, plan

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(plan.router, prefix="/plan", tags=["plan"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
