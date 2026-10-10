from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.reviews import router as reviews_router

api_v1_router = APIRouter()
api_v1_router.include_router(projects_router)
api_v1_router.include_router(reviews_router)
