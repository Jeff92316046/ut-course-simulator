from fastapi import APIRouter

from api.routers import (
    auth,
    swagger_oauth,
    course,
    teacher,
    course_selection,
    course_table,
)

from core.config import settings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(course.router, prefix="/courses")
api_router.include_router(teacher.router, prefix="/teachers")
api_router.include_router(course_selection.router, prefix="/course-selections")
api_router.include_router(course_table.router, prefix="/course-tables")

if settings.APP_MODE == "dev":
    api_router.include_router(swagger_oauth.oauth_router, prefix="/auth")
