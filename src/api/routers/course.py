import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session
import logging  # Import the logging module

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

logger = logging.getLogger(__name__)

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
    """Retrieves a paginated list of courses with optional filters."""
    logger.info(
        f"Attempting to retrieve courses with filters: "
        f"semester='{academic_year_semester}', code='{course_code}', teacher='{teacher_name}', "
        f"day='{day_of_week}', period='{start_period}', "
        f"limit={pagination.limit}, offset={pagination.offset}."
    )
    try:
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

        logger.info(
            f"Successfully retrieved {len(courses)} courses (total: {total}) matching the filters."
        )
        return PaginatedCourseResponse(
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            data=response_data,
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while retrieving courses with filters: "
            f"semester='{academic_year_semester}', code='{course_code}', teacher='{teacher_name}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve courses. Please try again later.",
        )


@router.get("/{course_id}/teachers", response_model=list[TeacherResponse])
def get_course_teachers(
    *,
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all teachers associated with a specific course ID."""
    logger.info(f"Attempting to retrieve teachers for course ID: {course_id}.")
    try:
        course = service.get_teachers_for_course(db=db, course_id=course_id)

        if not course:
            logger.warning(
                f"Course ID {course_id} not found when attempting to retrieve teachers."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        teachers = [
            TeacherResponse.model_validate(teacher) for teacher in course.teachers
        ]
        logger.info(
            f"Successfully retrieved {len(teachers)} teachers for course ID: {course_id}."
        )
        return teachers
    except HTTPException as e:
        logger.warning(
            f"Failed to retrieve teachers for course ID {course_id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while retrieving teachers for course ID {course_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve course teachers. Please try again later.",
        )
