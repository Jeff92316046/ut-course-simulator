import uuid
from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from schemas.teacher import CourseScheduleResponse
from services.teacher_service import TeacherService
from core.database import get_db
from api.dependencies import get_current_user
from schemas.course import (
    Teacher as TeacherResponse,
    Course as CourseResponse,
)
from model import User

logger = logging.getLogger(__name__)

service = TeacherService()
router = APIRouter(
    tags=["Teachers"],
)


@router.get("/search", response_model=List[TeacherResponse])
def search_teachers(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    name: str = Query(
        ..., min_length=1, description="Partial or full teacher name for fuzzy search"
    ),
):
    """Searches for teachers by name."""
    logger.info(f"Attempting to search teachers with name query: '{name}'.")
    try:
        teachers = service.search_teachers_by_name(db, name_query=name)
        response_data = [
            TeacherResponse.model_validate(teacher) for teacher in teachers
        ]
        logger.info(
            f"Successfully found {len(teachers)} teachers for name query: '{name}'."
        )
        return response_data
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while searching teachers for name '{name}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search teachers. Please try again later.",
        )


@router.get("/{teacher_id}/courses", response_model=List[CourseResponse])
def get_all_courses_taught_by_teacher(
    *,
    teacher_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    academic_year_semester: str | None = Query(
        None, description="學年學期, e.g., '113-1'"
    ),
):
    """Retrieves all courses taught by a specific teacher, with optional semester filter."""
    logger.info(
        f"Attempting to retrieve courses for teacher ID {teacher_id} (semester: {academic_year_semester or 'None'})."
    )
    try:
        courses = service.get_teacher_all_courses(
            db=db,
            teacher_id=teacher_id,
            academic_year_semester=academic_year_semester,
        )
        response_data = [CourseResponse.model_validate(course) for course in courses]
        logger.info(
            f"Successfully retrieved {len(courses)} courses for teacher ID {teacher_id}."
        )
        return response_data
    except HTTPException as e:
        logger.warning(
            f"Failed to retrieve courses for teacher ID {teacher_id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while retrieving courses for teacher ID {teacher_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teacher's courses. Please try again later.",
        )


@router.get("/{teacher_id}/schedule_slots", response_model=List[CourseScheduleResponse])
def get_teacher_all_schedule_slots(
    *,
    teacher_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    academic_year_semester: str | None = Query(
        None, description="學年學期, e.g., '113-1'"
    ),
):
    """Retrieves all schedule slots for a specific teacher, with optional semester filter."""
    logger.info(
        f"Attempting to retrieve schedule slots for teacher ID {teacher_id} (semester: {academic_year_semester or 'None'})."
    )
    try:
        schedule_slots = service.get_teacher_schedule_slots(
            db=db,
            teacher_id=teacher_id,
            academic_year_semester=academic_year_semester,
        )
        response_data = [
            CourseScheduleResponse.model_validate(slot) for slot in schedule_slots
        ]
        logger.info(
            f"Successfully retrieved {len(schedule_slots)} schedule slots for teacher ID {teacher_id}."
        )
        return response_data
    except HTTPException as e:
        logger.warning(
            f"Failed to retrieve schedule slots for teacher ID {teacher_id}: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while retrieving schedule slots for teacher ID {teacher_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teacher's schedule slots. Please try again later.",
        )
