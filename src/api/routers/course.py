import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session

from api.dependencies import get_current_user
from core.database import get_db
from schemas.course import (
    PaginatedCourseResponse,
    PaginationParams,
    Teacher as TeacherResponse,
    Course as CourseResponse,
)

from services.course_service import CourseService
from model import User

router = APIRouter(
    tags=["Courses"],
)
service = CourseService()


@router.get("/", response_model=PaginatedCourseResponse)
def get_all_courses(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    academic_year_semester: str | None = Query(
        None, description="學年學期, e.g., '113-1'"
    ),
    course_code: str | None = Query(None, description="課程代碼"),
    teacher_name: str | None = Query(None, description="教師姓名 (可模糊查詢)"),
    day_of_week: int | None = Query(None, ge=1, le=7, description="星期幾 (1-7)"),
    start_period: int | None = Query(None, ge=1, le=14, description="開始節次 (1-14)"),
):
    courses, total = service.get_courses(
        db=db,
        academic_year_semester=academic_year_semester,
        course_code=course_code,
        teacher_name=teacher_name,
        day_of_week=day_of_week,
        start_period=start_period,
        limit=pagination.limit,
        offset=pagination.offset,
    )

    response_data = [CourseResponse.model_validate(course) for course in courses]

    return PaginatedCourseResponse(
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        data=response_data,
    )


@router.get("/{course_id}/teachers", response_model=list[TeacherResponse])
def get_course_teachers(
    *,
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = service.get_teachers_for_course(db=db, course_id=course_id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    teachers = [TeacherResponse.model_validate(teacher) for teacher in course.teachers]
    return teachers
