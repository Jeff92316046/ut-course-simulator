from fastapi import APIRouter

from api.routers import auth, swagger_oauth, course, teacher

from core.config import settings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(course.router, prefix="/course")
api_router.include_router(teacher.router, prefix="/teacher")
if settings.APP_MODE == "dev":
    api_router.include_router(swagger_oauth.oauth_router, prefix="/auth")
